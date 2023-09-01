"""
`click_repl.parser`

Parsing functionalities for the click_repl module.
"""
import re
import typing as t
from functools import lru_cache
from gettext import gettext as _
from shlex import shlex

import click
from click.exceptions import BadOptionUsage
from click.exceptions import NoSuchOption
from click.parser import Argument as _Argument
from click.parser import normalize_opt
from click.parser import OptionParser
from click.parser import ParsingState

from . import utils
from ._globals import HAS_CLICK8
from .exceptions import ArgumentPositionError

if t.TYPE_CHECKING:
    from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

    from click import Argument as CoreArgument
    from click import Command, Context, MultiCommand, Parameter, Group
    from click.parser import Option

    _KEY: t.TypeAlias = Tuple[
        Optional[Dict[str, Any]],
        Optional[Dict[str, Any]],
        Optional[Dict[str, Any]],
        Tuple[Dict[str, Any], ...],
    ]


_flag_needs_value = object()
_quotes_to_empty_str_dict = str.maketrans(dict.fromkeys("'\"", ""))
_EQUALS_SIGN_AFTER_OPT_FLAG = re.compile(r"^([^a-z\d\s]+[^=\s]+)=(.+)$", re.I)


def split_arg_string(string: str, posix: bool = True) -> "List[str]":
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

    posix : bool, default: True
        Determines whether to split the string in POSIX style.

    Returns
    -------
    A list of string tokens parsed from the input string.
    """

    lex = shlex(string, posix=posix, punctuation_chars=True)
    lex.whitespace_split = True
    lex.commenters = ""
    lex.escape = ""
    out: "List[str]" = []

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

    def _expand_envvars(self) -> str:
        self.parsed_str = utils._expand_envvars(self.parsed_str)
        return self.parsed_str


@lru_cache(maxsize=3)
def get_args_and_incomplete_from_args(
    document_text: str,
) -> "Tuple[Tuple[str, ...], Incomplete]":
    args = split_arg_string(document_text)
    cursor_within_command = not document_text[-1:].isspace()

    if args and cursor_within_command:
        incomplete = args.pop()
    else:
        incomplete = ""

    match = _EQUALS_SIGN_AFTER_OPT_FLAG.match(incomplete)

    if match:
        _, opt, incomplete = match.groups()
        args.append(opt)

    _args = tuple(args)

    if not incomplete:
        return _args, Incomplete("", "")

    raw_incomplete = ""
    secondary_check = False

    for token in reversed(document_text.split(" ")):
        _tmp = f"{token} {raw_incomplete}".rstrip()

        if _tmp.translate(_quotes_to_empty_str_dict).strip() == incomplete:
            secondary_check = True

        elif secondary_check:
            break

        raw_incomplete = _tmp

    return _args, Incomplete(raw_incomplete, incomplete)


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
        cli_ctx: "Context",
        current_ctx: "Context",
        args: "Tuple[str, ...]",
    ) -> None:
        self.cli_ctx = cli_ctx
        self.cli: "MultiCommand" = self.cli_ctx.command  # type: ignore[assignment]

        self.current_ctx = current_ctx
        self.args = args

        self.remaining_params: "List[Parameter]" = []
        self.double_dash_found = getattr(current_ctx, "__double_dash_found", False)

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

    def __key(self) -> "_KEY":
        keys: "List[Optional[Dict[str, Any]]]" = []

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
            return NotImplemented
        return self.__key() == other.__key()

    def parse(self) -> "Tuple[Group, Optional[Command], Optional[Parameter]]":
        current_group, current_command = self.get_current_group_and_command()

        if current_command is not None:
            current_param = self.get_current_param(current_command)
        else:
            current_param = None

        return current_group, current_command, current_param

    def get_current_group_and_command(self) -> "Tuple[Group, Optional[Command]]":
        current_ctx_command = self.current_ctx.command
        parent_group = current_ctx_command

        # If parent ctx exist, we change parent_group to the parent ctx's command.
        if self.current_ctx.parent is not None:
            parent_group = self.current_ctx.parent.command

        current_group: "Group" = parent_group  # type: ignore[assignment]
        is_parent_group_chained = parent_group.chain  # type: ignore[attr-defined]
        current_command = None

        # Check if not all the required arguments have been assigned a value.
        # Here, we are checking if any of the click.Argument type parameters
        # have an incomplete value. Only click.Argument type parameters require
        # values (they have required=True by default), so they consume any
        # incoming string value they receive. If any incomplete argument value
        # is found, not_all_args_got_values is set to False. This condition check
        # is only performed when the parent group is a non-chained multi-command.

        args_list = [
            param
            for param in current_ctx_command.params
            if isinstance(param, click.Argument)
        ]

        not_all_args_got_values = all(
            not utils._is_param_value_incomplete(self.current_ctx, param.name)
            for param in args_list
        )

        incomplete_args_exist = not args_list or not_all_args_got_values
        no_incomplete_args = args_list and not_all_args_got_values

        if current_ctx_command == self.cli:
            return current_group, current_command

        elif (
            isinstance(current_ctx_command, click.MultiCommand) and incomplete_args_exist
        ):
            # If all the arguments are passed to the ctx multicommand,
            # promote it as current group.
            current_group = current_ctx_command  # type: ignore[assignment]

        elif not (
            is_parent_group_chained
            and (not current_ctx_command.params or no_incomplete_args)
        ):
            # The current command should point to its parent, once it
            # got all of its values, only if the parent has chain=True
            # let current_command be None. Or else, let current_command
            # be the current_ctx_command.
            current_command = current_ctx_command

        return current_group, current_command

    def get_current_param(self, current_command: "Command") -> "Optional[Parameter]":
        self.remaining_params = [
            param
            for param in current_command.params
            if utils._is_param_value_incomplete(self.current_ctx, param.name)
        ]

        param: "Optional[Parameter]" = self.parse_param_opt(current_command)
        if param is None:
            param = self.parse_param_arg(current_command)

        return param

    def parse_param_opt(self, current_command: "Command") -> "Optional[click.Option]":
        if "--" in self.args:
            # click parses all input strings after "--" as values for click.Argument
            # type parameters. So, we don't check for click.Optional parameters.
            return None

        for param in current_command.params:
            if isinstance(param, click.Argument) or (
                param.is_flag or param.count  # type: ignore[attr-defined]
            ):
                # We skip the current parameter check if its a click.Argument type
                # parameter, or its a flag or a counting type option.
                continue

            opts = param.opts + param.secondary_opts

            if any(i in self.args[param.nargs * -1 :] for i in opts):
                # We want to make sure if this parameter was called
                # If we are inside a parameter that was called, we want to show only
                # relevant choices
                return param  # type: ignore[return-value]

        return None

    def parse_param_arg(self, current_command: "Command") -> "Optional[click.Argument]":
        minus_one_param = None

        command_argument_params = (
            param
            for param in current_command.params  # type: ignore[union-attr]
            if isinstance(param, click.Argument)
        )

        for idx, param in enumerate(command_argument_params):
            if minus_one_param:
                raise ArgumentPositionError(current_command, param, idx)

            if param.nargs == -1:
                minus_one_param = param
                continue

            elif utils._is_param_value_incomplete(self.current_ctx, param.name):
                return param

        return minus_one_param


@lru_cache(maxsize=3)
def get_current_repl_parsing_state(
    cli_ctx: "Context",
    current_ctx: "Context",
    args: "Tuple[str, ...]",
) -> "ReplParsingState":
    return ReplParsingState(cli_ctx, current_ctx, args)


class Argument(_Argument):
    def process(
        self,
        value: "Union[Optional[str], Sequence[Optional[str]]]",
        state: "ParsingState",
    ) -> None:
        if self.nargs > 1 and value is not None:
            holes = sum(1 for x in value if x is None)
            if holes == len(value):
                value = None  # responsible for adding None value if arg is empty

        state.opts[self.dest] = value  # type: ignore[index]
        state.order.append(self.obj)


class ReplOptionParser(OptionParser):
    def __init__(self, ctx: "Context") -> None:
        super().__init__(ctx)

        for opt in ctx.command.params:
            opt.add_to_parser(self, ctx)

    def add_argument(
        self, obj: "CoreArgument", dest: "Optional[str]", nargs: int = 1
    ) -> None:
        self._args.append(Argument(obj=obj, dest=dest, nargs=nargs))

    def _process_args_for_options(self, state: "ParsingState") -> None:
        while state.rargs:
            arg = state.rargs.pop(0)
            arglen = len(arg)
            # Double dashes always handled explicitly regardless of what
            # prefixes are valid.
            if arg == "--":
                # Helps to denote to the completer class to stop generating
                # completions for option flags.
                self.ctx.__double_dash_found = True  # type: ignore[union-attr]
                return
            elif arg[:1] in self._opt_prefixes and arglen > 1:
                self._process_opts(arg, state)
            elif self.allow_interspersed_args:
                state.largs.append(arg)
            else:
                state.rargs.insert(0, arg)
                return

    def _match_long_opt(
        self, opt: str, explicit_value: "Optional[str]", state: "ParsingState"
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

    def _match_short_opt(self, arg: str, state: "ParsingState") -> None:
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
        self, option_name: str, option: "Option", state: "ParsingState"
    ) -> "Any":
        nargs = option.nargs
        rargs_len = len(state.rargs)

        if rargs_len < nargs:
            if HAS_CLICK8 and option.obj._flag_needs_value:
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
                HAS_CLICK8
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
