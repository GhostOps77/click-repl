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
    from typing import Any, Dict, List, Optional, Tuple

    from click import Argument as CoreArgument
    from click import Command, Context, MultiCommand, Parameter
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
        Split the string in POSIX style.

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
        self.raw_str = raw_str
        self.parsed_str = parsed_str

    def __str__(self) -> str:
        return self.parsed_str

    def __repr__(self) -> str:
        return repr(self.parsed_str)

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


class ArgsParsingState:
    """
    Maintains the parsing state of the arguments in the REPL prompt.

    This class parses a list of string arguments from the REPL prompt
    and keeps track of the current group/CLI, current command, and current
    parameter based on the given list of string arguments.
    """

    __slots__ = (
        "cli",
        "current_ctx",
        "cli_ctx",
        "args",
        "current_group",
        "current_command",
        "current_param",
        "remaining_params",
    )

    def __init__(
        self, cli_ctx: "Context", current_ctx: "Context", args: "Tuple[str]"
    ) -> None:
        """
        Initializes the parsing state using the CLI context, current context,
        and the sequence of string arguments.

        Parameters
        ----------
        cli_ctx : click.Context
            The CLI context representing the top-level command or group.

        current_ctx : click.Context
            The current context representing the current command or group being parsed.

        args : A sequence of strings
            The sequence of parsed string arguments from the REPL prompt.
        """

        self.cli_ctx = cli_ctx
        self.cli: "MultiCommand" = self.cli_ctx.command  # type: ignore[assignment]

        self.current_ctx = current_ctx
        self.args = args

        self.current_group: "MultiCommand" = self.cli
        self.current_command: "Optional[Command]" = None
        self.current_param: "Optional[Parameter]" = None

        self.remaining_params: "List[Parameter]" = []

        self.parse()

    def __str__(self) -> str:
        res = [str(self.current_group.name)]

        cmd = getattr(self.current_command, "name", None)
        if cmd is not None:
            res.append(cmd)

        param = getattr(self.current_param, "name", None)
        if param is not None:
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
            if i is None:
                keys.append(None)

            else:
                keys.append(utils.get_info_dict(i))

        return (  # type: ignore[return-value]
            *keys,
            tuple(utils.get_info_dict(param) for param in self.remaining_params),
        )

    def __eq__(  # type: ignore[override]
        self, other: "Optional[ArgsParsingState]"
    ) -> bool:
        if not isinstance(other, ArgsParsingState):
            return NotImplemented
        return self.__key() == other.__key()

    def parse(self) -> None:
        """
        Main method that parses the list of strings of args, and updates
        the state object.
        """

        self.current_group, self.current_command = self.get_current_group_and_command()
        if self.current_command is not None:
            self.current_param = self.get_current_params()

    def get_current_group_and_command(self) -> "Tuple[MultiCommand, Optional[Command]]":
        """
        Returns the current group and command based on the list of arguments.

        Returns
        -------
        A tupe containing:
          - MultiCommand
            The current group/CLI object.

          - Command or None
            The current command object if available, else None
        """

        current_ctx_command = self.current_ctx.command
        parent_group = current_ctx_command

        # If parent ctx exist, we change parent_group to the parent ctx's command
        if self.current_ctx.parent is not None:
            parent_group = self.current_ctx.parent.command

        current_group: "MultiCommand" = parent_group  # type: ignore[assignment]
        is_parent_group_chained = getattr(parent_group, "chain", False)
        current_command = None

        # Check whether if current ctx's command is same as the CLI.
        # is_cli = current_ctx_command == self.cli

        # Check if not all the required arguments have been assigned a value.
        # Here, we are checking if any of the click.Argument type parameters
        # have an incomplete value. Only click.Argument type parameters require
        # values (they have required=True by default), so they consume any
        # incoming string value they receive. If any incomplete argument value
        # is found, is_all_args_available is set to False. This condition check
        # is only performed when the parent group is a non-chained multi-command.

        is_all_args_not_available = True

        for param in current_ctx_command.params:
            if (
                not is_parent_group_chained or isinstance(param, click.Argument)
            ) and utils._is_param_value_incomplete(self.current_ctx, param.name):
                is_all_args_not_available = False

        if (
            isinstance(current_ctx_command, click.MultiCommand)
            and is_all_args_not_available
        ):
            # Every CLI command is a MultiCommand
            # If all the arguments are passed to the ctx command,
            # promote it as current group
            current_group = current_ctx_command

        elif not (is_parent_group_chained and is_all_args_not_available):
            # The current command should point to its parent, once it
            # got all of its values, only if the parent has chain=True
            # let current_cmd be None. Or else, let current_command
            # be the current_ctx_command.
            current_command = current_ctx_command

        # print(current_group, current_command)
        return current_group, current_command

    def get_current_params(self) -> "Optional[Parameter]":
        self.remaining_params = [
            param
            for param in self.current_command.params  # type: ignore[union-attr]
            if utils._is_param_value_incomplete(self.current_ctx, param.name)
        ]

        param: "Optional[Parameter]" = self.parse_param_opt()
        if param is None:
            param = self.parse_params_arg()

        return param

    def parse_param_opt(self) -> "Optional[click.Option]":
        if "--" in self.args:
            # click parses all input strings after "--" as values for click.Argument
            # type parameters. So, we don't check for click.Optional parameters.
            return None

        for param in self.current_command.params:  # type: ignore[union-attr]
            if isinstance(param, click.Argument) or (
                param.is_bool_flag or param.count  # type: ignore[union-attr]
            ):
                # We skip the current parameter check if its a click.Argument type
                # parameter, or its a boolean flag or a counting type option.
                continue

            opts = param.opts + param.secondary_opts

            if any(i in self.args[param.nargs * -1 :] for i in opts):
                # We want to make sure if this parameter was called
                # If we are inside a parameter that was called, we want to show only
                # relevant choices
                return param  # type: ignore[return-value]

        return None

    def parse_params_arg(self) -> "Optional[click.Argument]":
        minus_one_param = None

        command_argument_params = (
            i
            for i in self.current_command.params  # type: ignore[union-attr]
            if isinstance(i, click.Argument)
        )

        for param in command_argument_params:
            if minus_one_param:
                raise ArgumentPositionError(self.current_command, param)

            if param.nargs == -1:
                minus_one_param = param
                continue

            elif utils._is_param_value_incomplete(self.current_ctx, param.name):
                return param

        return minus_one_param


@lru_cache(maxsize=3)
def currently_introspecting_args(
    cli_ctx: "Context",
    cmd_ctx: "Context",
    args: "Tuple[str]",
) -> ArgsParsingState:
    return ArgsParsingState(cli_ctx, cmd_ctx, args)


class Argument(_Argument):
    def process(
        self,
        value: "t.Union[t.Optional[str], t.Sequence[t.Optional[str]]]",
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
        ctx.resilient_parsing = False

        super().__init__(ctx)

        for opt in ctx.command.params:
            opt.add_to_parser(self, ctx)

    def add_argument(
        self, obj: "CoreArgument", dest: "t.Optional[str]", nargs: int = 1
    ) -> None:
        self._args.append(Argument(obj=obj, dest=dest, nargs=nargs))

    def _match_long_opt(
        self, opt: str, explicit_value: "t.Optional[str]", state: "ParsingState"
    ) -> None:
        if opt not in self._long_opt:
            from difflib import get_close_matches

            possibilities = get_close_matches(opt, self._long_opt)
            raise NoSuchOption(opt, possibilities=possibilities, ctx=self.ctx)

        option = self._long_opt[opt]
        if option.takes_value:
            # At this point it's safe to modify rargs by injecting the
            # explicit value, because no exception is raised in this
            # branch.  This means that the inserted value will be fully
            # consumed.
            if explicit_value is not None:
                state.rargs.insert(0, explicit_value)

            value = self._get_value_from_state(opt, option, state)

        elif explicit_value is not None:
            raise BadOptionUsage(
                opt, _("Option {name!r} does not take a value.").format(name=opt)
            )

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

        # If we got any unknown options we re-combinate the string of the
        # remaining options and re-attach the prefix, then report that
        # to the state as new larg.  This way there is basic combinatorics
        # that can be achieved while still ignoring unknown arguments.
        if self.ignore_unknown_options and unknown_options:
            state.largs.append(f"{prefix}{''.join(unknown_options)}")

    def _get_value_from_state(
        self, option_name: str, option: "Option", state: "ParsingState"
    ) -> t.Any:
        nargs = option.nargs
        rargs_len = len(state.rargs)

        if rargs_len < nargs:
            if HAS_CLICK8 and option.obj._flag_needs_value:
                # Option allows omitting the value.
                value = _flag_needs_value
            else:
                # Fills up missing values with None.
                if nargs == 1 or rargs_len == 0:
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
                # The next arg looks like the start of an option, don't
                # use it as the value if omitting the value is allowed.
                value = _flag_needs_value
            else:
                value = state.rargs.pop(0)
        else:
            value = tuple(state.rargs[:nargs])
            del state.rargs[:nargs]

        return value
