"""
`click_repl.parser`

Parsing functionalities for the click_repl module.
"""

from __future__ import annotations

import re
import typing as t
from functools import lru_cache
from gettext import gettext as _
from shlex import shlex
from typing import Any, Dict, Optional, Sequence, Tuple

import click
from click import Argument as CoreArgument
from click import Command, Context, MultiCommand, Parameter
from click.exceptions import BadOptionUsage, NoSuchOption
from click.parser import Argument as _Argument
from click.parser import Option, OptionParser, ParsingState, normalize_opt
from typing_extensions import TypeAlias

from . import utils
from ._globals import HAS_CLICK_GE_8
from .exceptions import ArgumentPositionError

InfoDict: TypeAlias = Dict[str, Any]

_KEY: TypeAlias = Tuple[
    Optional[InfoDict],
    Optional[InfoDict],
    Optional[InfoDict],
    Tuple[InfoDict, ...],
]

_flag_needs_value = object()
_quotes_to_empty_str_dict = str.maketrans(dict.fromkeys("'\"", ""))

# Just gonna assume that people use only '-' and '--' as prefix for option flags
# _EQUALS_SIGN_AFTER_OPT_FLAG = re.compile(r"^(--?[a-z][\w-]*)=(.*)$", re.I)
_EQUALS_SIGN_AFTER_OPT_FLAG = re.compile(
    r"^(([^a-z\d\s])\2?[a-z]+(?:-[a-z\d]+)?)=(.*)$", re.I
)


def split_arg_string(string: str, posix: bool = True) -> list[str]:
    """
    Split a command line string into a list of tokens.
    Using the same implementation as in `click.parser.split_arg_string`

    This function behaves similarly to `shlex.split`, but it does not fail
    if the string is incomplete. It handles missing closing quotes or incomplete
    escape sequences by treating the partial token as-is.

    Parameters
    ----------
    string : str
        The string to be split into tokens.

    posix : bool
        Determines whether to split the string in POSIX style.

    Returns
    -------
    A list of string tokens parsed from the input string.
    """

    lex = shlex(string, posix=posix, punctuation_chars=True)
    lex.whitespace_split = True
    lex.escape = ""
    out: list[str] = []

    try:
        out.extend(lex)
    except ValueError:
        out.append(lex.token)

    return out


class Incomplete:
    __slots__ = ("raw_str", "parsed_str")

    def __init__(self, raw_str: str, parsed_str: str) -> None:
        self.raw_str = raw_str.strip()
        self.parsed_str = parsed_str

    def __str__(self) -> str:
        return self.parsed_str

    def __repr__(self) -> str:
        return repr(self.parsed_str)

    def __bool__(self) -> bool:
        return bool(self.raw_str)

    def __len__(self) -> int:
        return len(self.parsed_str)

    def expand_envvars(self) -> str:
        self.parsed_str = utils._expand_envvars(self.parsed_str).strip()
        return self.parsed_str

    def reverse_prefix_envvars(self, value: str) -> str:
        expanded_incomplete = self.expand_envvars()

        if value.startswith(expanded_incomplete):
            value = self.parsed_str + value[len(expanded_incomplete) :]

        return value


@lru_cache(maxsize=3)
def _resolve_incomplete(document_text: str) -> tuple[tuple[str, ...], Incomplete]:
    args = split_arg_string(document_text)
    cursor_within_command = not document_text[-1:].isspace()

    if args and cursor_within_command:
        incomplete = args.pop()
    else:
        incomplete = ""

    equal_sign_match = _EQUALS_SIGN_AFTER_OPT_FLAG.match(incomplete)

    if equal_sign_match:
        opt, _, incomplete = equal_sign_match.groups()
        args.append(opt)

    _args = tuple(args)

    if not incomplete:
        return _args, Incomplete("", "")

    raw_incomplete_with_quotes = ""
    secondary_check = False

    space_splitted_args = document_text.split(" ")

    if equal_sign_match:
        opt_len = len(opt)
        space_splitted_args[-1:] = [
            space_splitted_args[-1][:opt_len],
            space_splitted_args[-1][opt_len + 1 :],
        ]

    for token in reversed(space_splitted_args):
        _tmp = f"{token} {raw_incomplete_with_quotes}".rstrip()

        if _tmp.translate(_quotes_to_empty_str_dict).strip() == incomplete:
            secondary_check = True

        elif secondary_check:
            break

        raw_incomplete_with_quotes = _tmp

    return _args, Incomplete(raw_incomplete_with_quotes, incomplete)


class ReplParsingState:
    __slots__ = (
        "cli",
        "current_ctx",
        "cli_ctx",
        "args",
        "current_group",
        "current_command",
        "current_param",
        "remaining_params",
        "double_dash_found",
    )

    def __init__(
        self,
        cli_ctx: Context,
        current_ctx: Context,
        args: tuple[str, ...],
    ) -> None:
        self.cli_ctx = cli_ctx
        self.cli = t.cast(MultiCommand, self.cli_ctx.command)

        self.current_ctx = current_ctx
        self.args = args

        self.remaining_params: list[Parameter] = []
        self.double_dash_found = getattr(current_ctx, "_double_dash_found", False)

        self.current_group, self.current_command, self.current_param = self.parse()

    def __str__(self) -> str:
        res = [str(self.current_group.name)]

        cmd = getattr(self.current_command, "name", None)
        if cmd is not None:
            res.append(cmd)

        param = getattr(self.current_param, "name", None)
        if param is not None:
            if len(res) == 1:
                res.append("None")
            res.append(param)

        return " > ".join(res)

    def __repr__(self) -> str:
        return f'"{str(self)}"'

    def __key(self) -> _KEY:
        keys: list[InfoDict | None] = []

        for i in (
            self.current_group,
            self.current_command,
            self.current_param,
            self.current_ctx,
        ):
            keys.append(None if i is None else utils.get_info_dict(i))

        return (  # type: ignore[return-value]
            *keys,
            tuple(utils.get_info_dict(param) for param in self.remaining_params),
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ReplParsingState):
            return NotImplemented  # type:ignore[no-any-return]
        return self.__key() == other.__key()

    def parse(self) -> tuple[MultiCommand, Command | None, Parameter | None]:
        current_group, current_command = self.get_current_group_and_command()
        current_param = None

        if current_command is not None:
            current_param = self.get_current_param(current_command)

        return current_group, current_command, current_param

    def get_current_group_and_command(self) -> tuple[MultiCommand, Command | None]:
        current_ctx_command = self.current_ctx.command

        current_group = current_ctx_command
        current_command = None

        if current_ctx_command == self.cli:
            return current_group, current_command  # type:ignore[return-value]

        # If parent ctx exist, we change current_group to the parent ctx's command.
        if self.current_ctx.parent is not None:
            current_group = self.current_ctx.parent.command

        current_group = t.cast(MultiCommand, current_group)

        cmd_arguments_list = [
            param
            for param in current_ctx_command.params
            if isinstance(param, click.Argument)
        ]

        all_arguments_got_values = all(
            not utils.is_param_value_incomplete(self.current_ctx, param.name)
            for param in cmd_arguments_list
        )

        has_incomplete_args = not (cmd_arguments_list and all_arguments_got_values)

        if (
            isinstance(current_ctx_command, click.MultiCommand)
            and all_arguments_got_values
        ):
            # Promote the current command as current group, only if it
            # has got values to all of its click.Argument type args.
            current_group = current_ctx_command

        elif not current_group.chain or (
            current_ctx_command.params and has_incomplete_args
        ):
            current_command = current_ctx_command

        return current_group, current_command

    def get_current_param(self, current_command: Command) -> Parameter | None:
        self.remaining_params = [
            param
            for param in current_command.params
            if utils.is_param_value_incomplete(self.current_ctx, param.name)
        ]

        return self.parse_param_opt(current_command) or self.parse_param_arg(
            current_command
        )

    def parse_param_opt(self, current_command: Command) -> click.Option | None:
        if "--" in self.args:
            # click parses all input strings after "--" as values for click.Argument
            # type parameters. So, we don't check for click.Optional parameters.
            return None

        for param in current_command.params:
            if not isinstance(param, click.Option):
                continue

            if param.is_flag or param.count:
                continue

            opts = param.opts + param.secondary_opts
            current_args_for_param = self.args[param.nargs * -1 :]

            if any(opt in current_args_for_param for opt in opts):
                # We want to make sure if this parameter was called
                # If we are inside a parameter that was called, we want
                # to show only relevant choices
                return param

        return None

    def parse_param_arg(self, current_command: Command) -> click.Argument | None:
        nargs_minus_one_param = None

        for idx, param in enumerate(current_command.params):
            if not isinstance(param, click.Argument):
                continue

            if nargs_minus_one_param is not None:
                raise ArgumentPositionError(current_command, param, idx)

            if param.nargs == -1:
                nargs_minus_one_param = param

            elif utils.is_param_value_incomplete(self.current_ctx, param.name):
                return param

        return nargs_minus_one_param


@lru_cache(maxsize=3)
def _resolve_repl_parsing_state(
    cli_ctx: Context,
    current_ctx: Context,
    args: tuple[str, ...],
) -> ReplParsingState:
    return ReplParsingState(cli_ctx, current_ctx, args)


class ArgumentParamParser(_Argument):
    def process(
        self,
        value: str | Sequence[str | None] | None,
        state: ParsingState,
    ) -> None:
        if self.nargs > 1 and value is not None:
            holes = value.count(None)
            if holes == len(value):
                value = None  # responsible for adding None value if arg is empty

        state.opts[self.dest] = value  # type: ignore[index]
        state.order.append(self.obj)


class ReplOptionParser(OptionParser):
    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)

        for opt in ctx.command.params:
            opt.add_to_parser(self, ctx)

    def add_argument(self, obj: CoreArgument, dest: str | None, nargs: int = 1) -> None:
        self._args.append(ArgumentParamParser(obj=obj, dest=dest, nargs=nargs))

    def _process_args_for_options(self, state: ParsingState) -> None:
        while state.rargs:
            arg = state.rargs.pop(0)
            arglen = len(arg)

            # Double dashes always handled explicitly regardless of what
            # prefixes are valid.

            if arg == "--":
                # Dynamic attribute in click.Context object that helps to
                # denote to the completer class to stop generating
                # completions for option flags.
                self.ctx._double_dash_found = True  # type: ignore[union-attr]
                return

            elif arg[:1] in self._opt_prefixes and arglen > 1:
                self._process_opts(arg, state)

            elif self.allow_interspersed_args:
                state.largs.append(arg)

            else:
                state.rargs.insert(0, arg)
                return

    def _match_long_opt(
        self, opt: str, explicit_value: str | None, state: ParsingState
    ) -> None:
        if opt not in self._long_opt:
            from difflib import get_close_matches

            possibilities = get_close_matches(opt, self._long_opt)
            raise NoSuchOption(opt, possibilities=possibilities, ctx=self.ctx)

        option = self._long_opt[opt]
        if option.takes_value:
            if explicit_value is not None:
                state.rargs.insert(0, explicit_value)

            value = self._get_value_from_state(opt, option, state)

        elif explicit_value is not None:
            raise BadOptionUsage(opt, _(f"Option {opt!r} does not take a value."))

        else:
            value = None

        option.process(value, state)

    def _match_short_opt(self, arg: str, state: ParsingState) -> None:
        stop = False
        i = 1
        prefix = arg[0]
        unknown_options = []

        for ch in arg[1:]:
            opt = normalize_opt(f"{prefix}{ch}", self.ctx)
            option = self._short_opt.get(opt)
            i += 1

            if not option:
                if self.ignore_unknown_options:
                    unknown_options.append(ch)
                    continue

                raise NoSuchOption(opt, ctx=self.ctx)

            if option.takes_value:
                # Any characters left in arg?  Pretend they're the
                # next arg, and stop consuming characters of arg.
                if i < len(arg):
                    state.rargs.insert(0, arg[i:])
                    stop = True

                value = self._get_value_from_state(opt, option, state)

            else:
                value = None

            option.process(value, state)

            if stop:
                break

        if self.ignore_unknown_options and unknown_options:
            state.largs.append(f"{prefix}{''.join(unknown_options)}")

    def _get_value_from_state(
        self, option_name: str, option: Option, state: ParsingState
    ) -> Any:
        nargs = option.nargs
        rargs_len = len(state.rargs)

        if rargs_len < nargs:
            if HAS_CLICK_GE_8 and option.obj._flag_needs_value:
                # Option allows omitting the value.
                value = _flag_needs_value
            else:
                # Fills up missing values with None.
                if nargs == 1:
                    value = None
                else:
                    value = tuple(state.rargs + [None] * (nargs - rargs_len))
                state.rargs = []

        elif nargs == 1:
            next_rarg = state.rargs[0]

            if (
                HAS_CLICK_GE_8
                and option.obj._flag_needs_value
                and isinstance(next_rarg, str)
                and next_rarg[:1] in self._opt_prefixes
                and len(next_rarg) > 1
            ):
                value = _flag_needs_value
            else:
                value = state.rargs.pop(0)
        else:
            value = tuple(state.rargs[:nargs])
            del state.rargs[:nargs]

        return value
