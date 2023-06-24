import os
import re
import typing as t
from collections import deque
from functools import lru_cache
from gettext import gettext as _
from pathlib import Path
from shlex import shlex

import click
from click.exceptions import BadOptionUsage
from click.exceptions import NoSuchOption
from click.parser import Argument as _Argument
from click.parser import normalize_opt
from click.parser import OptionParser
from prompt_toolkit.completion import Completion

from ._globals import _RANGE_TYPES

if t.TYPE_CHECKING:
    from typing import Dict, Generator, Iterable, List, Optional, Tuple, Union

    from click import Argument as CoreArgument  # noqa: F401
    from click import Command, Context, MultiCommand, Parameter
    from click.parser import Option, ParsingState

    V = t.TypeVar("V")

# try:
#     from click.parser import _flag_needs_value
# except ImportError:
_flag_needs_value = object()
EQUAL_SIGNED_OPTION = re.compile(r"^(\W{1,2}[a-z][a-z-]*)=", re.I)
IS_WINDOWS = os.name == "nt"


# Handle backwards compatibility for click<=8
try:
    import click.shell_completion  # noqa: F401

    HAS_CLICK_V8 = True
    AUTO_COMPLETION_PARAM = "shell_complete"
except ImportError:
    import click._bashcomplete  # type: ignore[import]

    HAS_CLICK_V8 = False
    AUTO_COMPLETION_PARAM = "autocompletion"


def quotes(text: str) -> str:
    if " " in text and text[0] != '"' and text[-1] != '"':
        text = text.strip('"')
        return f'"{text}"'
    return text


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
    """Split an argument string as with :func:`shlex.split`, but don't
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
    """Custom class to parse the list of args"""

    __slots__ = (
        "cli",
        "ctx",
        "args",
        "current_group",
        "current_command",
        "current_param",
        "remaining_params",
    )

    def __init__(self, cli: "MultiCommand", ctx: "Context", args: "List[str]") -> None:
        self.cli = cli
        self.ctx = ctx
        self.args = args

        self.current_group: "MultiCommand" = cli
        self.current_command: "Optional[Command]" = None
        self.current_param: "Optional[Parameter]" = None

        self.remaining_params: "List[Parameter]" = []

        self.current_group, self.current_command = self.get_current_command()
        if self.current_command is not None:
            self.current_param = self.parse_params()

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

    def get_current_command(self) -> "Tuple[MultiCommand, Optional[Command]]":
        ctx_command = self.ctx.command
        parent_group = ctx_command

        # If there's a parent ctx exist
        if self.ctx.parent is not None:
            parent_group = self.ctx.parent.command

        current_group: "MultiCommand" = parent_group  # type: ignore[assignment]
        current_command = None
        is_cli = ctx_command == self.cli  # if current ctx's command is same as the CLI

        # All the required arguments should be assigned with some values
        all_args_val = all(
            self.ctx.params[i.name] is not None  # type: ignore[index]
            for i in ctx_command.params
            if isinstance(i, click.Argument)
        )

        # Every CLI command is a MultiCommand
        if isinstance(ctx_command, click.MultiCommand) and (is_cli or all_args_val):
            current_group = ctx_command

        elif getattr(parent_group, "chain", False) and all_args_val:
            # The current command should point to its parent, once it
            # got all of its values, only if the parent has chain=True
            # Let current_cmd be None and never let it change in the else clause
            pass

        else:
            # This else clause helps in some unknown edge cases, to fill up the
            # current command value
            current_command = ctx_command  # type: ignore[unreachable]

        return current_group, current_command

    def parse_params(self) -> "Optional[Parameter]":
        # print(f"\n{vars(ctx) = }")

        self.remaining_params = [
            param
            for param in self.current_command.params  # type: ignore[union-attr]
            if self.ctx.params.get(param.name, None)  # type: ignore[arg-type]
            in (None, ())
            # or not is_bool_flag_or_count_parsed(param, self.ctx)
        ]

        param = self.parse_param_opt()
        if param is None:
            param = self.parse_params_arg()

        return param

    def parse_param_opt(self) -> "Optional[Parameter]":
        for param in self.current_command.params:  # type: ignore[union-attr]
            if (
                isinstance(param, click.Option)
                # and not ctx.args
                and "--" not in self.args
            ):
                opts = param.opts + param.secondary_opts

                # if (
                #     param.is_bool_flag and ctx.params[param.name] == param.flag_value
                # ) or (param.count and ctx.params[param.name] != 0):
                #     continue

                if param.is_bool_flag or param.count:
                    continue

                # elif (
                #     isinstance(self.current_cmd, click.MultiCommand)
                #     and param.name in ctx.params
                # ) or
                elif any(i in self.args[param.nargs * -1 :] for i in opts):  # noqa: E203
                    # We want to make sure if this parameter was called
                    # If we are inside a parameter that was called, we want to show only
                    # relevant choices
                    return param

        return None

    def parse_params_arg(self) -> "Optional[Parameter]":
        minus_one_param = None

        cmd_params = deque(
            i
            for i in self.current_command.params  # type: ignore[union-attr]
            if isinstance(i, click.Argument)
        )
        while cmd_params:
            param = _fetch(cmd_params, minus_one_param)

            if param is None:
                continue

            if param.nargs == -1:
                minus_one_param = param

            elif self.ctx.params[param.name] is None:  # type: ignore[index]
                return param

        return minus_one_param


# @lru_cache(maxsize=3)
def currently_introspecting_args(
    cli: "MultiCommand", ctx: "Context", args: "List[str]"
) -> ArgsParsingState:
    return ArgsParsingState(cli, ctx, args)


class CompletionsProvider:
    """Provides Completion items based on the given parameters
    along with the styles provided to it.

    Keyword arguments:
    :param:`cli` - Group Repl CLI
    :param:`styles` - Dictionary of styles in the way of prompt-toolkit module,
        for arguments, options, etc.
    """

    __slots__ = ("styles",)

    def __init__(self, styles: "Dict[str, str]") -> None:
        self.styles = styles

    def get_completion_from_autocompletion_functions(
        self,
        param: "Parameter",
        autocomplete_ctx: "Context",
        args: "Iterable[str]",
        incomplete: str,
    ) -> "Generator[Completion, None, None]":
        if HAS_CLICK_V8:
            autocompletions = param.shell_complete(autocomplete_ctx, incomplete)
        else:
            autocompletions = param.autocompletion(  # type: ignore[attr-defined]
                autocomplete_ctx, args, incomplete
            )

        for autocomplete in autocompletions:
            if isinstance(autocomplete, tuple):
                yield Completion(
                    quotes(autocomplete[0]),
                    -len(incomplete),
                    display_meta=autocomplete[1],
                )

            elif HAS_CLICK_V8 and isinstance(
                autocomplete, click.shell_completion.CompletionItem
            ):
                yield Completion(quotes(autocomplete.value), -len(incomplete))

            elif isinstance(autocomplete, Completion):
                yield autocomplete

            else:
                yield Completion(quotes(str(autocomplete)), -len(incomplete))

    def get_completion_from_choices_click_le_7(
        self, param_type: "click.Choice", incomplete: str
    ) -> "Generator[Completion, None, None]":
        case_insensitive = not getattr(param_type, "case_sensitive", True)

        if case_insensitive:
            incomplete = incomplete.lower()

        for choice in param_type.choices:
            if case_insensitive:
                choice = choice.lower()

            if choice.startswith(incomplete):
                yield Completion(
                    quotes(choice),
                    -len(incomplete),
                    style=self.styles["argument"],
                    display=choice,
                )

    def get_completion_for_Path_types(
        self, incomplete: str
    ) -> "Generator[Completion, None, None]":
        if "*" in incomplete:
            return []  # type: ignore[return-value]

        # print(f'\n{incomplete = }')

        has_space = " " in incomplete
        # quoted = incomplete.count('"') % 2

        # print(f"\n{has_space = } {quoted = } {incomplete = }")

        search_pattern = incomplete.strip("\"'") + "*"
        # if has_space and not quoted:
        #     incomplete = f'"{incomplete}'

        temp_path_obj = Path(search_pattern)

        # quote = ""  # Quote thats used to surround the path in shell

        # if " " in incomplete:
        #     for i in incomplete:
        #         if i in ("'", '"'):
        #             quote = i
        #             break

        completion_txt_len = -len(incomplete) - has_space * 2  # + quoted * 2

        # print(f"{temp_path_obj = }")
        for path in temp_path_obj.parent.glob(temp_path_obj.name):
            #     if " " in path:
            #         if quote:
            #             path = quote + path
            #         else:
            #             if IS_WINDOWS:
            #                 path = repr(path).replace("\\\\", "\\")
            #     else:
            #         if IS_WINDOWS:
            #             path = path.replace("\\", "\\\\")

            path_str = str(path)

            if IS_WINDOWS:
                path_str = path_str.replace("\\\\", "\\")

            if " " in path_str:
                path_str = f'"{path_str}"'

                # if quoted:
                #     path_str = f'"{path_str}'
                # else:
                #     path_str = f'"{path_str}"'

                # completion_txt_len -= 1

            yield Completion(
                path_str,
                completion_txt_len,
                display=path.name,
            )

    def get_completion_for_Boolean_type(
        self, incomplete: str
    ) -> "Generator[Completion, None, None]":
        boolean_mapping = {
            "true": ("1", "true", "t", "yes", "y", "on"),
            "false": ("0", "false", "f", "no", "n", "off"),
        }

        for value, aliases in boolean_mapping.items():
            if any(alias.startswith(incomplete) for alias in aliases):
                yield Completion(
                    quotes(value), -len(incomplete), display_meta="/".join(aliases)
                )

    def get_completion_for_Range_types(
        self, param_type: "Union[click.IntRange, click.FloatRange]"
    ) -> "List[Completion]":
        clamp = " clamped" if param_type.clamp else ""
        display_meta = f"{param_type._describe_range()}{clamp}"

        return [Completion("-", display_meta=display_meta)]

    def get_completion_from_params(
        self,
        ctx: "Context",
        param: "Parameter",
        args: "Iterable[str]",
        incomplete: str,
    ) -> "List[Completion]":
        choices: "List[Completion]" = []
        param_type: "click.ParamType" = param.type

        if isinstance(param_type, _RANGE_TYPES):
            return self.get_completion_for_Range_types(param_type)

        elif isinstance(param_type, click.Tuple):
            return [Completion("-", display=_type.name) for _type in param_type.types]

        # shell_complete method for click.Choice is introduced in click-v8
        elif not HAS_CLICK_V8 and isinstance(param_type, click.Choice):
            choices.extend(
                self.get_completion_from_choices_click_le_7(param_type, incomplete)
            )

        elif isinstance(param_type, click.types.BoolParamType):
            choices.extend(self.get_completion_for_Boolean_type(incomplete))

        elif isinstance(param_type, (click.Path, click.File)):
            choices.extend(self.get_completion_for_Path_types(incomplete))

        elif getattr(param, AUTO_COMPLETION_PARAM, None) is not None:
            choices.extend(
                self.get_completion_from_autocompletion_functions(
                    param,
                    ctx,
                    args,
                    incomplete,
                )
            )

        return choices

    def get_completion_for_command_args(
        self,
        ctx: "Context",
        state: "ArgsParsingState",
        args: "Iterable[str]",
        incomplete: "str",
    ) -> "Generator[Completion, None, None]":
        opt_names = []
        for param in state.current_command.params:  # type: ignore[union-attr]
            if isinstance(param, click.Argument) or getattr(param, "hidden", False):
                continue

            opts = param.opts + param.secondary_opts

            if getattr(param, "is_bool_flag", False) and any(i in args for i in opts):
                continue

            for option in opts:
                if not option.startswith(incomplete):
                    continue

                display_meta = getattr(param, "help", "")

                if not (getattr(param, "count", False) or param.default is None):
                    display_meta += f" [Default={param.default}]"

                if param.metavar is not None:
                    display = param.metavar
                else:
                    display = option

                opt_names.append(
                    Completion(
                        option,
                        -len(incomplete),
                        display=display,
                        display_meta=display_meta,
                        style=self.styles["option"],
                    )
                )

        current_param = state.current_param

        # if current_param is not None:
        #     if isinstance(current_param, click.Argument):
        #         yield from opt_names

        #     if not getattr(current_param, "hidden", False):
        #         yield from self.get_completion_from_params(
        #             ctx, current_param, args, incomplete
        #         )

        # else:
        #     yield from opt_names

        current_param_is_None = current_param is None
        if current_param_is_None or isinstance(current_param, click.Argument):
            yield from opt_names

        if not (current_param_is_None or getattr(current_param, "hidden", False)):
            yield from self.get_completion_from_params(
                ctx, current_param, args, incomplete  # type: ignore[arg-type]
            )

    def get_completions_for_command(
        self,
        ctx: "Context",
        state: "ArgsParsingState",
        args: "Iterable[str]",
        incomplete: str,
    ) -> "Generator[Completion, None, None]":
        current_group = state.current_group
        current_command_exists = state.current_command is not None
        is_chain = getattr(current_group, "chain", False)

        # if curr_group is None:
        #     return

        if current_command_exists:
            yield from self.get_completion_for_command_args(ctx, state, args, incomplete)

        if not current_command_exists or (
            is_chain and any(i is not None for i in ctx.params.values())
        ):
            for name in current_group.list_commands(ctx):
                command = current_group.get_command(ctx, name)
                if getattr(command, "hidden", False):  # type: ignore[union-attr]
                    continue

                elif name.startswith(incomplete):
                    yield Completion(
                        name,
                        -len(incomplete),
                        display_meta=getattr(command, "short_help", ""),
                    )


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

        # if self.nargs == -1 and self.obj.envvar is not None and value == ():
        #     # Replace empty tuple with None so that a value from the
        #     # environment may be tried.
        #     value = None

        state.opts[self.dest] = value  # type: ignore
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
        # ctx.resilient_parsing = True
        ctx.allow_extra_args = True
        ctx.allow_interspersed_args = True

        super().__init__(ctx)

        for opt in ctx.command.params:  # type: ignore[union-attr]
            opt.add_to_parser(self, ctx)

    def add_argument(
        self, obj: "CoreArgument", dest: "t.Optional[str]", nargs: int = 1
    ) -> None:
        """Adds a positional argument named `dest` to the parser.

        The `obj` can be used to identify the option in the order list
        that is returned from the parser.
        """
        self._args.append(Argument(obj, dest=dest, nargs=nargs))

    def _process_args_for_options(self, state: "ParsingState") -> None:
        # Tracking the scattered values using unparsed_args list
        unparsed_args = []

        while state.rargs:
            arg = state.rargs.pop(0)
            # Double dashes always handled explicitly regardless of what
            # prefixes are valid.
            if arg == "--":
                return
            elif arg[:1] in self._opt_prefixes and len(arg) > 1:
                self._process_opts(arg, state)
            elif self.allow_interspersed_args:
                unparsed_args.append(arg)
            else:
                unparsed_args.append(arg)
                break

        # Insert unparsed args into the beginning of the rargs
        state.rargs[0:1] = unparsed_args

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
            if option.obj._flag_needs_value:
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
                option.obj._flag_needs_value
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
