import os
import typing as t
from collections import deque
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

if t.TYPE_CHECKING:
    from typing import Any, Dict, List, Optional, Sequence, Tuple, Type
    from click import Argument as CoreArgument
    from click import Command, Context, MultiCommand, Parameter
    from click.parser import Option

    V = t.TypeVar("V")
    _KEY: t.TypeAlias = Tuple[
        Optional[Dict[str, Any]],
        Optional[Dict[str, Any]],
        Optional[Dict[str, Any]],
        Tuple[Dict[str, Any], ...],
    ]

# try:
#     from click.parser import _flag_needs_value
# except ImportError:
_flag_needs_value = object()
# EQUAL_SIGNED_OPTION = re.compile(r"^(\W{1,2}[a-z][a-z-]*)=", re.I)


def _fetch(c: "t.Deque[V]", spos: "t.Optional[int]" = None) -> "t.Optional[V]":
    """To fetch the click.Arguments in the required order to parse them"""
    try:
        if spos is None:
            return c.popleft()
        else:
            return c.pop()
    except IndexError:
        return None


def split_arg_string(string: str, posix: bool = True) -> "List[str]":
    """Split an argument string as with `shlex.split`, but don't
    fail if the string is incomplete. Ignores a missing closing quote or
    incomplete escape sequence and uses the partial token as-is.
    .. code-block:: python
        shlex_split("example 'my file")
        ["example", "my file"]
        shlex_split("example my\\")
        ["example", "my"]

    :param `string`: String to split.
    :param `posix`: Split string in posix style (default: True)

    Return: A list that contains the splitted string
    """

    lex = shlex(string, posix=posix, punctuation_chars=True)
    lex.whitespace_split = True
    lex.commenters = ""
    lex.escape = ""
    out: "List[str]" = []
    # remaining_token: str = ""

    try:
        out.extend(lex)
    except ValueError:
        # Raised when end-of-string is reached in an invalid state. Use
        # the partial token as-is. The quote or escape character is in
        # lex.state, not lex.token.
        # remaining_token = lex.token
        out.append(lex.token)

    # To get the actual text passed in through REPL cmd line
    # irrespective of quotes
    # last_val = ""
    # if out and remaining_token == "" and not string[-1].isspace():
    #     remaining_token = out[-1]

    #     tmp = ""
    #     for i in reversed(string.split()):
    #         last_val = f"{i} {tmp}".strip()
    #         if last_val.replace("'", "").replace('"', "") == remaining_token:
    #             break
    #         else:
    #             tmp = last_val

    #     if out and last_val == out[-1]:
    #         last_val = ""

    return out  # , last_val


@lru_cache(maxsize=3)
def get_args_and_incomplete_from_args(
    document_text: str,
) -> "Tuple[Tuple[str, ...], str]":
    args = split_arg_string(document_text)
    cursor_within_command = not document_text[-1:].isspace()
    # cursor_within_command = (
    #     document_text.rstrip() == document_text
    # )

    if args and cursor_within_command:  # and not remaining_token:
        # We've entered some text and no space, give completions for the
        # current word.
        incomplete = args.pop()
    else:
        # We've not entered anything, either at all or for the current
        # command, so give all relevant completions for this context.
        incomplete = ""  # remaining_token

    # match = EQUAL_SIGNED_OPTION.split(incomplete, 1)
    # if len(match) > 1:
    #     opt, incomplete = match[1], match[2]
    #     args.append(opt)

    if "=" in incomplete:
        opt, incomplete = incomplete.split("=", 1)
        args.append(opt)

    incomplete = os.path.expandvars(os.path.expanduser(incomplete))

    return tuple(args), incomplete


class ArgsParsingState:
    """Parses the list of args of string thats currently in the REPL prompt."""

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
        self, cli_ctx: "Context", current_ctx: "Context", args: "Sequence[str]"
    ) -> None:
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
        res = ""

        group = getattr(self.current_group, "name", None)
        if group is not None:
            res += f"{group}"

        cmd = getattr(self.current_command, "name", None)
        if cmd is not None:
            res += f" > {cmd}"

        param = getattr(self.current_param, "name", None)
        if param is not None:
            res += f" > {param}"

        return res

    def __repr__(self) -> str:
        return f'"{str(self)}"'

    def __key(self) -> "_KEY":
        keys: "List[Optional[Dict[str, Any]]]" = []

        for i in (self.current_group, self.current_command, self.current_param):
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
        if isinstance(other, ArgsParsingState):
            return self.__key() == other.__key()
        return False

    def parse(self) -> None:
        self.current_group, self.current_command = self.get_current_command()
        if self.current_command is not None:
            self.current_param = self.get_current_params()

    def get_current_command(self) -> "Tuple[MultiCommand, Optional[Command]]":
        current_ctx_command = self.current_ctx.command
        # parent_group = ctx_command

        # If parent ctx exist, we change parent_group to the parent ctx's command
        parent_group: "MultiCommand" = getattr(
            self.current_ctx.parent,
            "command",
            current_ctx_command,  # type: ignore[arg-type]
        )

        # if self.cmd_ctx.parent is not None:
        #     parent_group = self.cmd_ctx.parent.command

        current_group: "MultiCommand" = parent_group  # type: ignore[assignment]
        current_command = None

        # Check whether if current ctx's command is same as the CLI.
        is_cli = current_ctx_command == self.cli

        # All the required arguments should be assigned with some values
        current_ctx_params = self.current_ctx.params

        is_all_args_available = True

        if current_ctx_params:
            for param in current_ctx_command.params:
                if utils.is_param_value_incomplete(self.current_ctx, param.name):
                    if getattr(parent_group, "chain", False) and isinstance(
                        param, click.Option
                    ):
                        continue

                    is_all_args_available = False
                    break

        if isinstance(current_ctx_command, click.MultiCommand) and (
            is_cli or is_all_args_available
        ):
            # Every CLI command is a MultiCommand
            # If all the arguments are passed to the ctx command,
            # promote it as current group
            current_group = current_ctx_command

        elif getattr(parent_group, "chain", False) and is_all_args_available:
            # The current command should point to its parent, once it
            # got all of its values, only if the parent has chain=True
            # Let current_cmd be None and never let it change in the else clause
            pass

        else:
            # This else clause helps in some unknown edge cases, to fill up the
            # current command value
            current_command = current_ctx_command

        return current_group, current_command

    def get_current_params(self) -> "Optional[Parameter]":
        self.remaining_params = [
            param
            for param in self.current_command.params  # type: ignore[union-attr]
            if utils.is_param_value_incomplete(self.current_ctx, param.name)
        ]

        param = self.parse_param_opt()
        if param is None:
            param = self.parse_params_arg()

        return param

    def parse_param_opt(self) -> "Optional[Parameter]":
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
                return param

        return None

    def parse_params_arg(self) -> "Optional[Parameter]":
        minus_one_param = None

        command_params = deque(
            i
            for i in self.current_command.params  # type: ignore[union-attr]
            if isinstance(i, click.Argument)
        )

        while command_params:
            param = _fetch(command_params, minus_one_param)

            if param is None:
                break

            if param.nargs == -1:
                minus_one_param = param
                continue

            elif utils.is_param_value_incomplete(self.current_ctx, param.name):
                return param

        return minus_one_param


@lru_cache(maxsize=3)
def currently_introspecting_args(
    cli_ctx: "Context",
    cmd_ctx: "Context",
    args: "Sequence[str]",
    state_cls: "Optional[Type[ArgsParsingState]]" = None,
) -> ArgsParsingState:
    if state_cls is None:
        state_cls = ArgsParsingState

    return state_cls(cli_ctx, cmd_ctx, args)


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


class CustomOptionsParser(OptionParser):
    __slots__ = (
        "ctx",
        "allow_interspersed_args",
        "ignore_unknown_options",
        "_short_opt",
        "_long_opt",
        "_opt_prefixes",
        "_args",
    )

    def __init__(self, ctx: "Context") -> None:
        # ctx.resilient_parsing = False
        # ctx.allow_extra_args = True
        # ctx.allow_interspersed_args = True
        # ctx.ignore_unknown_options = True

        super().__init__(ctx)

        for opt in ctx.command.params:
            opt.add_to_parser(self, ctx)

    def add_argument(
        self, obj: "CoreArgument", dest: "t.Optional[str]", nargs: int = 1
    ) -> None:
        """Adds a positional argument named `dest` to the parser.

        The `obj` can be used to identify the option in the order list
        that is returned from the parser.
        """
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
                # Fills up missing values with None
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
