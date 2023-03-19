from __future__ import unicode_literals

import click
import shlex
import sys

from pathlib import Path

# from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit.completion import (
    Completer,
    Completion,  # PathCompleter
)

__all__ = ["ClickCompleter"]

# typing module introduced in Python 3.5
if sys.version_info >= (3, 5):
    import typing as t

    if t.TYPE_CHECKING:
        from click import Context, Command, Parameter  # noqa: F401
        from prompt_toolkit.document import Document  # noqa: F401
        from prompt_toolkit.completion import CompleteEvent  # noqa: F401
        from typing import Any, Generator, Optional, Union  # noqa: F401


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
    return "{}".format(text)


class ClickCompleter(Completer):
    __slots__ = ("cli", "ctx", "styles")

    def __init__(self, cli, ctx=None, styles=None):
        # type: (Command, Optional[Context], Optional[dict[str, str]]) -> None

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

    def _get_completion_from_choices_click7(
        self,
        param,
        incomplete
    ):
        # type: (Parameter, str) -> list[Completion]

        return [
            Completion(text_type(choice), -len(incomplete), style=self.styles['argument'])
            for choice in param.type.choices  # type: ignore[attr-defined]
        ]

    def _get_completion_for_Path_types(self, param, args, incomplete):
        # type: (Union[Parameter, click.Option], list[str], str) -> list[Completion]

        return [
            Completion(text_type(i), -len(incomplete), display=text_type(i.name))
            for i in Path().glob("{}*".format(incomplete))
        ]

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

    def _get_completion_from_params(
        self,
        ctx_command,  # type: Command
        incomplete,  # type: str
        autocomplete_ctx,  # type: Context
        args,  # type: list[str]
    ):
        # type: (...) -> tuple[list[Completion], list[Completion], bool]

        choices = []
        param_choices = []
        param_called = False

        for param in ctx_command.params:
            if getattr(param, "hidden", False):
                continue

            elif isinstance(param, click.Option):
                for option in (param.opts + param.secondary_opts):
                    # We want to make sure if this parameter was called
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
                    if not HAS_CLICK_V8 and isinstance(param.type, click.Choice):
                        param_choices.extend(
                            self._get_completion_from_choices_click7(
                                param, incomplete
                            )
                        )

                    elif isinstance(param.type, click.types.BoolParamType):
                        param_choices.extend(
                            self._get_completion_for_Boolean_type(param, incomplete)
                        )

                    elif isinstance(param.type, (click.Path, click.File)):
                        param_choices.extend(
                            self._get_completion_for_Path_types(param, args, incomplete)
                        )

                    elif getattr(param, AUTO_COMPLETION_PARAM, None) is not None:
                        param_choices.extend(
                            self._get_completion_from_autocompletion_functions(
                                param,
                                autocomplete_ctx,
                                args,
                                incomplete,
                            )
                        )

                    # elif isinstance(param.type, click.File):
                    #     param_choices.extend(
                    #         self._get_completion_for_File_types(param, args, incomplete)
                    #     )

            elif isinstance(param, click.Argument):
                if not HAS_CLICK_V8 and isinstance(param.type, click.Choice):
                    choices.extend(
                        self._get_completion_from_choices_click7(param, incomplete)
                    )

                elif isinstance(param.type, click.types.BoolParamType):
                    choices.extend(
                        self._get_completion_for_Boolean_type(param, incomplete)
                    )

                elif isinstance(param.type, (click.Path, click.File)):
                    choices.extend(
                        self._get_completion_for_Path_types(param, args, incomplete)
                    )

                # elif isinstance(param.type, click.File):
                #     choices.extend(
                #         self._get_completion_for_File_types(param, args, incomplete)
                #     )

                elif getattr(param, AUTO_COMPLETION_PARAM, None) is not None:
                    choices.extend(
                        self._get_completion_from_autocompletion_functions(
                            param,
                            autocomplete_ctx,
                            args,
                            incomplete,
                        )
                    )

        return choices, param_choices, param_called

    def get_completions(self, document, complete_event=None):
        # type: (Document, Optional[CompleteEvent]) -> Generator[Completion, None, None]

        # Code analogous to click._bashcomplete.do_complete

        try:
            args = shlex.split(document.text_before_cursor, posix=False)
        except ValueError:
            # Invalid command, perhaps caused by missing closing quotation.
            return

        choices = []  # type: list[Completion]
        param_choices = []  # type: list[Completion]
        param_called = False
        cursor_within_command = (
            document.text_before_cursor.rstrip() == document.text_before_cursor
        )

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
            choices, param_choices, param_called = self._get_completion_from_params(
                ctx_command, incomplete, autocomplete_ctx, args
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
        if param_called:
            choices = param_choices

        # for item in choices:
        #     # if item.text.startswith(incomplete):
        #         yield item
        yield from choices
