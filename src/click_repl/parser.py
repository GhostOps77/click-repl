import os
import typing as t
from functools import lru_cache
from glob import iglob

# from pathlib import Path
from shlex import shlex

import click
from prompt_toolkit.completion import Completion

# from .utils import _resolve_context
# from .exceptions import CommandLineParserError

if t.TYPE_CHECKING:
    from typing import Dict, Generator, List, Tuple, Union, Optional, Iterable

    from click import Command, Context, Parameter, MultiCommand  # noqa: F401


IS_WINDOWS = os.name == "nt"

# Float Range is introduced after IntRange, in click v7
try:
    from click import FloatRange

    _Range_types = (click.IntRange, FloatRange)
except ImportError:
    _Range_types = (click.IntRange,)  # type: ignore[assignment]


# Handle backwards compatibility for click<=8
try:
    import click.shell_completion  # noqa: F401

    HAS_CLICK_V8 = True
    AUTO_COMPLETION_PARAM = "shell_complete"
except ImportError:
    import click._bashcomplete  # type: ignore[import]

    HAS_CLICK_V8 = False
    AUTO_COMPLETION_PARAM = "autocompletion"


def split_arg_string(string: str, posix: bool = True) -> "List[str]":
    """Split an argument string as with :func:`shlex.split`, but don't
    fail if the string is incomplete. Ignores a missing closing quote or
    incomplete escape sequence and uses the partial token as-is.
    .. code-block:: python
        split_arg_string("example 'my file")
        ["example", "my file"]
        split_arg_string("example my\\")
        ["example", "my"]

    :param `string`: String to split.
    :param `posix`: Split string in posix style (default: True)

    Return: A list that contains the splitted string
    """

    lex = shlex(string, posix=posix, punctuation_chars=True)
    lex.whitespace_split = True
    lex.commenters = ""
    out: "List[str]" = []

    try:
        out.extend(lex)
    except ValueError:
        # Raised when end-of-string is reached in an invalid state. Use
        # the partial token as-is. The quote or escape character is in
        # lex.state, not lex.token.
        out.append(lex.token)

    return out


@lru_cache(maxsize=3)
def _split_args(document_text: str) -> "Tuple[Tuple[str, ...], str]":
    args = split_arg_string(document_text, posix=False)
    cursor_within_command = document_text.rstrip() == document_text

    if args and cursor_within_command:
        # We've entered some text and no space, give completions for the
        # current word.
        incomplete = args.pop()
    else:
        # We've not entered anything, either at all or for the current
        # command, so give all relevant completions for this context.
        incomplete = ""

    return tuple(args), incomplete


class ParsingState:
    __slots__ = (
        "cli",
        "ctx",
        "args",
        "current_group",
        "current_cmd",
        "current_param",
        # 'parsed_params',
        "remaining_params",
    )

    def __init__(self, cli: "MultiCommand", ctx: "Context", args: "Tuple[str]") -> None:
        self.cli = cli
        self.ctx = ctx
        self.args = args

        self.current_group: "Optional[MultiCommand]" = None
        self.current_cmd: "Optional[Command]" = None
        self.current_param: "Optional[Parameter]" = None

        # self.parsed_params: 'List[Parameter]' = []
        self.remaining_params: "List[Parameter]" = []

        self.parse_ctx(ctx, args)

    def __str__(self) -> str:
        return (
            f"{getattr(self.current_group, 'name', None)}"
            f" > {getattr(self.current_cmd, 'name', None)}"
            f" > {getattr(self.current_param, 'name', None)}"
        )

    def _parse_cmd(self, ctx: "Context") -> None:
        ctx_cmd = ctx.command
        parent_group = None
        if ctx.parent is not None:
            parent_group = ctx.parent.command

        self.current_group = parent_group  # type: ignore[assignment]
        is_cli = ctx_cmd == self.cli

        if all(value is not None for value in ctx.params.values()) or is_cli:
            # if is_cli:
            #     self.current_cmd = None

            if isinstance(ctx_cmd, click.MultiCommand):
                self.current_group = ctx_cmd

            elif isinstance(ctx_cmd, click.Command):
                self.current_group = parent_group  # type: ignore[assignment]
                self.current_cmd = ctx_cmd

        else:
            self.current_cmd = ctx_cmd

        if self.current_cmd is not None:
            minus_one_args = []
            for param in self.current_cmd.params:
                if ctx.params.get(param.name, None) is None:  # type: ignore[arg-type]
                    if param.nargs == -1:
                        minus_one_args.append(param)
                    else:
                        self.remaining_params.append(param)

            self.remaining_params += minus_one_args

    def _parse_params(self, ctx: "Context", args: "Tuple[str]") -> None:
        skip_arguments = False

        for param in ctx.command.params:
            if isinstance(param, click.Option):
                options_name_list = param.opts + param.secondary_opts

                if param.is_bool_flag and any(i in args for i in options_name_list):
                    continue

                for option in options_name_list:
                    # We want to make sure if this parameter was called
                    # If we are inside a parameter that was called, we want to show only
                    # relevant choices
                    if option in args[param.nargs * -1 :] and not param.count:
                        self.current_param = param
                        return

            elif (
                isinstance(param, click.Argument)
                and param in self.remaining_params
                and not skip_arguments
                and (
                    ctx.params.get(param.name) is None  # type: ignore[arg-type]
                    or param.nargs == -1
                )
            ):
                self.current_param = param
                skip_arguments = True

    def parse_ctx(self, ctx: "Context", args: "Tuple[str]") -> None:
        # 'Tuple[Optional[MultiCommand], Optional[Command], Optional[Parameter]]'
        self._parse_cmd(ctx)
        self._parse_params(ctx, args)


@lru_cache(maxsize=3)  # Make a decorator around this decorator to catch the latest value
def currently_introspecting_args(
    cli: "MultiCommand", ctx: "Context", args: "Tuple[str]"
) -> ParsingState:
    return ParsingState(cli, ctx, args)


class ReplParser:
    """Provides Completion items based on the given parameters
    along with the styles provided to it.

    Keyword arguments:
    :param:`cli` - Group Repl CLI
    :param:`styles` - Dictionary of styles in the way of prompt-toolkit module,
        for arguments, options, etc.
    """

    __slots__ = (
        "cli",
        "styles",
    )

    def __init__(self, cli: "MultiCommand", styles: "Dict[str, str]") -> None:
        self.cli = cli
        self.styles = styles

    def _get_completion_from_autocompletion_functions(
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
                    autocomplete[0],
                    -len(incomplete),
                    display_meta=autocomplete[1],
                )

            elif HAS_CLICK_V8 and isinstance(
                autocomplete, click.shell_completion.CompletionItem
            ):
                yield Completion(autocomplete.value, -len(incomplete))

            elif isinstance(autocomplete, Completion):
                yield autocomplete

            else:
                yield Completion(str(autocomplete), -len(incomplete))

    def _get_completion_from_choices_click_le_7(
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
                    choice,
                    -len(incomplete),
                    style=self.styles["argument"],
                    display=repr(choice) if " " in choice else choice,
                )

    def _get_completion_for_Path_types(
        self, incomplete: str
    ) -> "Generator[Completion, None, None]":
        if "*" in incomplete:
            return

        _expanded_env_incomplete = os.path.expandvars(incomplete)
        search_pattern = _expanded_env_incomplete.strip("'\"").replace("\\\\", "\\") + "*"
        quote = ""  # Quote thats used to surround the path in shell

        if " " in _expanded_env_incomplete:
            for i in incomplete:
                if i in ("'", '"'):
                    quote = i
                    break

        for path in iglob(search_pattern):
            if " " in path:
                if quote:
                    path = quote + path
                else:
                    if IS_WINDOWS:
                        path = repr(path).replace("\\\\", "\\")
            else:
                if IS_WINDOWS:
                    path = path.replace("\\", "\\\\")

            yield Completion(
                path,
                -len(incomplete),
                display=os.path.basename(path.strip("'\"")),
            )

    def _get_completion_for_Boolean_type(
        self, incomplete: str
    ) -> "Generator[Completion, None, None]":
        boolean_mapping = {
            "true": ("1", "true", "t", "yes", "y", "on"),
            "false": ("0", "false", "f", "no", "n", "off"),
        }

        for value, aliases in boolean_mapping.items():
            if any(alias.startswith(incomplete) for alias in aliases):
                yield Completion(value, -len(incomplete), display_meta="/".join(aliases))

    def _get_completion_for_Range_types(
        self, param_type: "Union[click.IntRange, click.FloatRange]"
    ) -> "List[Completion]":
        clamp = " clamped" if param_type.clamp else ""
        display_meta = f"{param_type._describe_range()}{clamp}"

        return [Completion("-", display_meta=display_meta)]

    def _get_completion_from_params(
        self,
        ctx: "Context",
        param: "Parameter",
        args: "Iterable[str]",
        incomplete: str,
    ) -> "List[Completion]":
        choices: "List[Completion]" = []
        param_type: "click.ParamType" = param.type

        if isinstance(param_type, _Range_types):
            return self._get_completion_for_Range_types(param_type)

        elif isinstance(param_type, click.Tuple):
            return [Completion("", display=_type.name) for _type in param_type.types]

        # shell_complete method for click.Choice is intorduced in click-v8
        elif not HAS_CLICK_V8 and isinstance(param_type, click.Choice):
            choices.extend(
                self._get_completion_from_choices_click_le_7(param_type, incomplete)
            )

        elif isinstance(param_type, click.types.BoolParamType):
            choices.extend(self._get_completion_for_Boolean_type(incomplete))

        elif isinstance(param_type, (click.Path, click.File)):
            choices.extend(self._get_completion_for_Path_types(incomplete))

        elif getattr(param, AUTO_COMPLETION_PARAM, None) is not None:
            choices.extend(
                self._get_completion_from_autocompletion_functions(
                    param,
                    ctx,
                    args,
                    incomplete,
                )
            )

        return choices

    def _get_completion_for_cmd_args(
        self,
        ctx: "Context",
        state: "ParsingState",
        args: "Iterable[str]",
        incomplete: "str",
    ) -> "Generator[Completion, None, None]":

        param_choices = []
        for param in state.current_cmd.params:  # type: ignore[union-attr]
            if (
                isinstance(param, click.Option) and not param.hidden
            ):  # type: ignore[union-attr]
                options_name_list = param.opts + param.secondary_opts

                if param.is_bool_flag and any(i in args for i in options_name_list):
                    continue

                for option in options_name_list:
                    if option.startswith(incomplete):
                        display_meta = ""

                        if param.default is not None:
                            display_meta += f" [Default={param.default}]"

                        if param.metavar is not None:
                            display = param.metavar
                        else:
                            display = option

                        param_choices.append(
                            Completion(
                                option,
                                -len(incomplete),
                                display=display,
                                display_meta=display_meta,
                                style=self.styles["option"],
                            )
                        )

        curr_param = state.current_param

        if curr_param is not None:
            if isinstance(curr_param, click.Argument):
                yield from param_choices

            if not getattr(curr_param, "hidden", False):
                yield from self._get_completion_from_params(
                    ctx, curr_param, args, incomplete
                )

        else:
            yield from param_choices

    def _get_completions_for_command(
        self,
        ctx: "Context",
        state: "ParsingState",
        args: "Iterable[str]",
        incomplete: str,
    ) -> "Generator[Completion, None, None]":

        curr_group = state.current_group
        curr_cmd_exists = state.current_cmd is not None
        is_chain = getattr(curr_group, "chain", False)

        if curr_group is not None:
            if curr_cmd_exists:
                yield from self._get_completion_for_cmd_args(ctx, state, args, incomplete)

            if (not state.remaining_params and is_chain) or not curr_cmd_exists:
                for name in curr_group.list_commands(ctx):
                    command = curr_group.get_command(ctx, name)
                    if command.hidden:  # type: ignore[union-attr]
                        continue

                    elif name.startswith(incomplete):
                        yield Completion(
                            name,
                            -len(incomplete),
                            display_meta=getattr(command, "short_help", ""),
                        )
