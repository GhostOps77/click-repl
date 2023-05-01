import os
import typing as t
from functools import lru_cache
from glob import iglob

# from pathlib import Path
from shlex import shlex

import click
from prompt_toolkit.completion import Completion

from .exceptions import CommandLineParserError

if t.TYPE_CHECKING:
    from typing import Tuple  # noqa: F401
    from typing import Dict, Generator, List, NoReturn, Optional, Union

    from click import Command, Context, Parameter  # noqa: F401


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
    :param string: String to split.
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


# @lru_cache(maxsize=3)
def get_ctx_for_args(
    cmd: "Command", parsed_args: "List[str]", group_args: "List[str]"
) -> "Tuple[Command, Context]":
    # Resolve context based on click version
    if HAS_CLICK_V8:
        parsed_ctx = click.shell_completion._resolve_context(
            cmd, {}, "", group_args + parsed_args
        )
    else:
        parsed_ctx = click._bashcomplete.resolve_ctx(cmd, "", group_args + parsed_args)

    ctx_command = parsed_ctx.command
    # opt_parser = OptionsParser(ctx_command, parsed_ctx)

    return ctx_command, parsed_ctx


@lru_cache(maxsize=3)
def _split_args(document_text: str) -> "Optional[Tuple[List[str], str]]":
    if document_text.startswith(("!", ":")):
        return None

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

    return args, incomplete


class CompletionParser:
    """Provides Completion items based on the given parameters
    along with the styles provided to it.

    Keyword arguments:
    :param:`styles` -- Dictionary of styles in the way of prompt-toolkit module,
    for arguments, options, etc.
    """

    __slots__ = ("styles",)

    def __init__(self, styles: "Dict[str, str]") -> None:
        self.styles = styles

    def _get_completion_from_autocompletion_functions(
        self,
        param: "Parameter",
        autocomplete_ctx: "Context",
        args: "List[str]",
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
    ) -> "Generator[Completion, None, List[str]]":

        if "*" in incomplete:
            return []

        _expanded_env_incomplete = os.path.expandvars(incomplete)
        search_pattern = (
            _expanded_env_incomplete.strip("'\"").replace("\\\\", "\\") + "*"
        )
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
                yield Completion(
                    value, -len(incomplete), display_meta="/".join(aliases)
                )

    def _get_completion_for_Range_types(
        self, param_type: "Union[click.IntRange, click.FloatRange]"
    ) -> "List[Completion]":

        clamp = " clamped" if param_type.clamp else ""
        display_meta = f"{param_type._describe_range()}{clamp}"

        return [Completion("-", display_meta=display_meta)]

    def _get_completion_from_params(
        self,
        autocomplete_ctx: "Context",
        param: "Parameter",
        args: "List[str]",
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
                    autocomplete_ctx,
                    args,
                    incomplete,
                )
            )

        return choices

    def _get_completion_for_cmd_args(
        self,
        ctx_command: "Command",
        autocomplete_ctx: "Context",
        args: "List[str]",
        incomplete: "str",
    ) -> "Union[List[Completion], NoReturn]":

        choices = []
        param_called = False
        params_list = ctx_command.params
        for index, param in enumerate(params_list):
            if param.nargs == -1:
                params_list.append(params_list.pop(index))

        # print("Currently introspecting argument:", autocomplete_ctx.info_name)
        for param in params_list:
            # print(f'{vars(param) = }')
            for attr in ("hidden", "hide_input"):
                if getattr(param, attr, False):
                    raise CommandLineParserError(
                        f"Click Repl cannot parse a '{attr}' parameter"
                    )

            if isinstance(param, click.Option):
                options_name_list = param.opts + param.secondary_opts
                if param.is_bool_flag and any(i in args for i in options_name_list):
                    continue

                for option in options_name_list:
                    # print(f'{option = }')
                    # We want to make sure if this parameter was called
                    # If we are inside a parameter that was called, we want to show only
                    # relevant choices
                    # print(f'{args[param.nargs * -1 :] = } {incomplete = !r}')
                    if option in args[param.nargs * -1 :] and not param.count:
                        param_called = True
                        # print(f"param called by {param.name}")
                        break

                    # elif option in args and not (param.multiple or param.count):
                    #     break

                    elif option.startswith(incomplete):
                        # print(f'{option} startswith ({incomplete})\n')
                        display_meta = (param.help or "") + (
                            f"[Default={param.default}]" if param.default else ""
                        )

                        choices.append(
                            Completion(
                                option,
                                -len(incomplete),
                                display_meta=display_meta,
                                style=self.styles["option"],
                            )
                        )

                # If we are inside a parameter that was called, we want to show only
                # relevant choices
                # print(f'{param.name = } {param_called = }')
                if param_called and not (param.is_bool_flag or param.count):
                    choices = self._get_completion_from_params(
                        autocomplete_ctx, param, args, incomplete
                    )
                    break

            elif isinstance(param, click.Argument):
                if (
                    autocomplete_ctx.params.get(param.name)  # type: ignore[arg-type]
                    is None
                    or param.nargs == -1
                ):
                    choices.extend(
                        self._get_completion_from_params(
                            autocomplete_ctx, param, args, incomplete
                        )
                    )
                    break

        return choices

    def _get_completions_for_command(
        self, ctx_cmd: "Command", ctx: "Context", args: "List[str]", incomplete: str
    ) -> "Generator[Completion, None, None]":

        if isinstance(ctx_cmd, click.MultiCommand):
            for name in ctx_cmd.list_commands(ctx):
                command = ctx_cmd.get_command(ctx, name)
                if getattr(command, "hidden", False):
                    continue

                elif name.startswith(incomplete):
                    yield Completion(
                        name,
                        -len(incomplete),
                        display_meta=getattr(command, "short_help", ""),
                    )

        else:
            yield from self._get_completion_for_cmd_args(ctx_cmd, ctx, args, incomplete)
