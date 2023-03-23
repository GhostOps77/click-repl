from __future__ import unicode_literals

import ntpath
import os
import sys
from glob import iglob

import click
from prompt_toolkit.completion import Completion  # PathCompleter
from prompt_toolkit.completion import Completer

from .utils import split_arg_string

__all__ = ["ClickCompleter"]

# Path module is introduced in Python 3.4
PY34 = sys.version_info >= (3, 4)
if PY34:
    import pathlib

# typing module introduced in Python 3.5
if sys.version_info >= (3, 5):
    import typing as t

    if t.TYPE_CHECKING:
        from typing import Any, Generator, Optional, Union  # noqa: F401

        from click import Command, Context, Group, Parameter  # noqa: F401
        from prompt_toolkit.completion import CompleteEvent  # noqa: F401
        from prompt_toolkit.document import Document  # noqa: F401


# Handle backwards compatibility between Click<=7.0 and >=8.0
try:
    import click.shell_completion

    HAS_CLICK_V8 = True
    AUTO_COMPLETION_PARAM = "shell_complete"
except (ImportError, ModuleNotFoundError):
    import click._bashcomplete  # type: ignore[import]

    HAS_CLICK_V8 = False
    AUTO_COMPLETION_PARAM = "autocompletion"


def text_type(text):
    # type: (Any) -> str
    return u"{}".format(text)


class ClickCompleter(Completer):
    __slots__ = ("cli", "ctx", "styles")

    def __init__(self, cli, ctx=None, styles=None):
        # type: (Group, Optional[Context], Optional[dict[str, str]]) -> None

        self.cli = cli  # type: Command
        self.ctx = ctx  # type: Optional[Context]
        self.styles = styles if styles is not None else {
            'command': '',
            'argument': '',
            'option': ''
        }  # type: dict[str, str]

    def _get_completion_from_autocompletion_functions(
        self,
        param,
        autocomplete_ctx,
        args,
        incomplete,
    ):
        # type: (Parameter, Context, list[str], str) -> list[Completion]

        param_choices = []

        if HAS_CLICK_V8:
            autocompletions = param.shell_complete(autocomplete_ctx, incomplete)
        else:
            autocompletions = param.autocompletion(  # type: ignore[attr-defined]
                autocomplete_ctx, args, incomplete
            )

        for autocomplete in autocompletions:
            if isinstance(autocomplete, tuple):
                param_choices.append(
                    Completion(
                        text_type(autocomplete[0]),
                        -len(incomplete),
                        display_meta=autocomplete[1],
                    )
                )

            elif HAS_CLICK_V8 and isinstance(
                autocomplete, click.shell_completion.CompletionItem
            ):
                param_choices.append(
                    Completion(text_type(autocomplete.value), -len(incomplete))
                )

            else:
                param_choices.append(
                    Completion(text_type(autocomplete), -len(incomplete))
                )

        return param_choices

    def _get_completion_from_choices_click_le_7(
        self,
        param,
        incomplete
    ):
        # type: (Parameter, str) -> list[Completion]

        if getattr(param.type, 'case_sensitive', None) is not None:
            incomplete = incomplete.lower()
            return [
                Completion(
                    text_type(choice),
                    -len(incomplete),
                    style=self.styles['argument'],
                    display=text_type(repr(choice) if ' ' in choice else choice),
                )
                for choice in param.type.choices  # type: ignore[attr-defined]
                if choice.lower().startswith(incomplete)
            ]

        else:
            return [
                Completion(
                    text_type(choice),
                    -len(incomplete),
                    style=self.styles['argument'],
                    display=text_type(repr(choice) if ' ' in choice else choice)
                )
                for choice in param.type.choices  # type: ignore[attr-defined]
                if choice.startswith(incomplete)
            ]

    def _get_completion_for_Path_types(self, param, args, incomplete):
        # type: (Parameter, list[str], str) -> list[Completion]

        choices = []
        search_pattern = incomplete.strip('\'"\t\n\r\v ').replace("\\\\", "\\")

        if '*' in incomplete:
            return []

        search_pattern += '*'
        quote = ''

        if ' ' in incomplete:
            for i in incomplete:
                if i in ("'", '"'):
                    quote = i
                    break

        for path in iglob(search_pattern):
            if isinstance(param.type, click.Path):
                if param.type.resolve_path:
                    if PY34:
                        path = os.fsdecode(pathlib.Path(path).resolve())

                    else:
                        path = os.path.realpath(path)

            if ' ' in path:
                if quote:
                    path = quote + path
                else:
                    path = repr(path).replace("\\\\", "\\")
            else:
                path = path.replace('\\', '\\\\')

            choices.append(
                Completion(
                    text_type(path),
                    -len(incomplete),
                    display=text_type(ntpath.basename(path.strip('\'"')))
                )
            )

        return choices

    # def _get_completion_for_File_types(self, param, args, incomplete):
    #     # type: (Union[Parameter, click.Option], list[str], str) -> list[Completion]

    #     # attrs = vars(param)

    #     return list(
    #         Completion(text_type(i), -len(incomplete), display=text_type(i.name))
    #         for i in filter(
    #             lambda item: item.is_file(), Path().glob("{}*".format(incomplete))
    #         )
    #     )

    def _get_completion_for_Boolean_type(self, param, incomplete):
        # type: (Union[Parameter, click.Option], str) -> list[Completion]
        return [
            Completion(
                text_type(k),
                -len(incomplete),
                display_meta=text_type("/".join(v))
            )
            for k, v in {
                "true": ("1", "true", "t", "yes", "y", "on"),
                "false": ("0", "false", "f", "no", "n", "off"),
            }.items()
            if any(i.startswith(incomplete) for i in v)
        ]

    def _get_completion_from_params(self, autocomplete_ctx, args, param, incomplete):
        # type: (Context, list[str], Parameter, str) -> list[Completion]
        choices = []  # type: list[Completion]
        param_type = param.type  # type: click.ParamType

        # shell_complete method for click.Choice is intorduced in click-v8
        if not HAS_CLICK_V8 and isinstance(param_type, click.Choice):
            choices.extend(
                self._get_completion_from_choices_click_le_7(param, incomplete)
            )

        elif isinstance(param_type, click.types.BoolParamType):
            choices.extend(
                self._get_completion_for_Boolean_type(param, incomplete)
            )

        elif isinstance(param_type, (click.Path, click.File)):
            choices.extend(
                self._get_completion_for_Path_types(param, args, incomplete)
            )

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
        ctx_command,  # type: Command
        incomplete,  # type: str
        autocomplete_ctx,  # type: Context
        args,  # type: list[str]
    ):
        # type: (...) -> list[Completion]

        choices = []
        # param_choices = []
        param_called = False

        # if HAS_CLICK_V8:
        #     choices = ctx_command.shell_complete(autocomplete_ctx, incomplete)
        #     return choices

        for param in ctx_command.params:
            # print(f'{vars(param) = }')
            if isinstance(param.type, click.types.UnprocessedParamType):
                return []

            elif getattr(param, "hidden", False):
                continue

            elif isinstance(param, click.Option):
                for option in (param.opts + param.secondary_opts):
                    # We want to make sure if this parameter was called
                    # If we are inside a parameter that was called, we want to show only
                    # relevant choices
                    if option in args[param.nargs * -1 :]:  # noqa: E203
                        param_called = True
                        break

                    elif option.startswith(incomplete):
                        choices.append(
                            Completion(
                                text_type(option),
                                -len(incomplete),
                                display_meta=text_type(param.help or ""),
                                style=self.styles['option']
                            )
                        )

                if param_called:
                    choices = self._get_completion_from_params(
                        autocomplete_ctx, args, param, incomplete
                    )

            elif isinstance(param, click.Argument):
                choices.extend(
                    self._get_completion_from_params(
                        autocomplete_ctx, args, param, incomplete
                    )
                )

        return choices

    def get_completions(self, document, complete_event=None):
        # type: (Document, Optional[CompleteEvent]) -> Generator[Completion, None, None]

        # Code analogous to click._bashcomplete.do_complete

        # try:
        args = split_arg_string(document.text_before_cursor, posix=False)
        # except ValueError:
        #     # Invalid command, perhaps caused by missing closing quotation.
        #     return

        choices = []  # type: list[Completion]
        # param_choices = []  # type: list[Completion]
        # param_called = False
        cursor_within_command = (
            document.text_before_cursor.rstrip() == document.text_before_cursor
        )

        # print(f'{args = }')
        # print(f'{document.text = }')
        # print(f'{document.text_before_cursor.rstrip() = }')

        if document.text_before_cursor.startswith(('!', ':')):
            return

        if args and cursor_within_command:
            # We've entered some text and no space, give completions for the
            # current word.
            incomplete = args.pop()
        else:
            # We've not entered anything, either at all or for the current
            # command, so give all relevant completions for this context.
            incomplete = ""

        # Resolve context based on click version
        if HAS_CLICK_V8:
            ctx = click.shell_completion._resolve_context(self.cli, {}, "", args)
        else:
            ctx = click._bashcomplete.resolve_ctx(self.cli, "", args)

        # if ctx is None:
        #     return  # type: ignore[unreachable]

        autocomplete_ctx = self.ctx or ctx
        ctx_command = ctx.command

        if getattr(ctx_command, "hidden", False):
            return

        try:
            choices.extend(
                self._get_completion_for_cmd_args(
                    ctx_command, incomplete, autocomplete_ctx, args
                )
            )

            if isinstance(ctx_command, click.MultiCommand):
                for name in ctx_command.list_commands(ctx):
                    command = ctx_command.get_command(ctx, name)
                    if getattr(command, "hidden", False):
                        continue

                    elif name.lower().startswith(incomplete.lower()):
                        choices.append(
                            Completion(
                                text_type(name),
                                -len(incomplete),
                                display_meta=getattr(command, 'short_help', ""),
                            )
                        )

        except Exception as e:
            click.echo("{}: {}".format(type(e).__name__, str(e)))

        # If we are inside a parameter that was called, we want to show only
        # relevant choices
        # if param_called:
        #     choices = param_choices

        for item in choices:
            # if item.text.startswith(incomplete):
            yield item
        # yield from choices
