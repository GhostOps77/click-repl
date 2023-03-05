from __future__ import unicode_literals

import shlex
import sys
from typing import Generator, Optional, Union  # noqa: F401

import click
from prompt_toolkit.completion import (CompleteEvent, Completer,  # noqa: F401
                                       Completion)
from prompt_toolkit.document import Document  # noqa: F401

__all__ = ["ClickCompleter"]

# Handle backwards compatibility between Click<=7.0 and >=8.0
try:
    import click.shell_completion

    HAS_CLICK_V8 = True
    AUTO_COMPLETION_PARAM = "shell_complete"

except (ImportError, ModuleNotFoundError):
    import click._bashcomplete

    HAS_CLICK_V8 = False
    AUTO_COMPLETION_PARAM = "autocompletion"


PY2 = sys.version_info[0] == 2
if PY2:
    text_type = unicode  # noqa: F821
else:
    text_type = str  # noqa


class ClickCompleter(Completer):
    __slots__ = ("cli", "ctx")

    def __init__(self, cli, ctx=None):
        # type: (click.Command, Optional[click.Context]) -> None

        self.cli = cli
        self.ctx = ctx

    def _get_completion_from_autocompletion_functions(
        self,
        param,
        autocomplete_ctx,
        args,
        incomplete,
    ):
        # type: (click.Parameter, click.Context, list[str], str) -> list[Completion]

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

    def _get_completion_from_choices(self, param, incomplete):
        # type: (Union[click.Argument, click.Option], str) -> list[Completion]

        return [
            Completion(text_type(choice), -len(incomplete))
            for choice in param.type.choices  # type: ignore[attr-defined]
        ]

    def _get_completion_from_params(
        self,
        ctx_command,  # type: click.Command
        incomplete,  # type: str
        autocomplete_ctx,  # type: click.Context
        args,  # type: list[str]
    ):
        # type: (...) -> tuple[list[Completion], list[Completion], bool]

        choices = []
        param_choices = []
        param_called = False

        for param in ctx_command.params:
            if getattr(param, "hidden", False):
                continue

            if isinstance(param, click.Option):
                for options in (param.opts, param.secondary_opts):
                    for option in options:
                        choices.append(
                            Completion(
                                text_type(option),
                                -len(incomplete),
                                display_meta=text_type(param.help),
                            )
                        )

                        # We want to make sure if this parameter was called
                        if option in args[param.nargs * -1 :]:  # noqa: E203
                            param_called = True

                if (
                    param_called
                    and getattr(param, AUTO_COMPLETION_PARAM, None) is not None
                ):
                    param_choices.extend(
                        self._get_completion_from_autocompletion_functions(
                            param,
                            autocomplete_ctx,
                            args,
                            incomplete,
                        )
                    )

                elif not HAS_CLICK_V8 and isinstance(param.type, click.Choice):
                    param_choices.extend(
                        self._get_completion_from_choices(param, incomplete)
                    )

            elif isinstance(param, click.Argument):
                if isinstance(param.type, click.Choice):
                    choices.extend(self._get_completion_from_choices(param, incomplete))

                elif (
                    not HAS_CLICK_V8
                    and getattr(param, AUTO_COMPLETION_PARAM, None) is not None
                ):
                    choices = self._get_completion_from_autocompletion_functions(
                        param,
                        autocomplete_ctx,
                        args,
                        incomplete,
                    )

        return choices, param_choices, param_called

    def get_completions(self, document, complete_event=None):
        # type: (Document, Optional[CompleteEvent]) -> Generator[Completion, None, None]

        # Code analogous to click._bashcomplete.do_complete

        try:
            args = shlex.split(document.text_before_cursor)
        except ValueError:
            # Invalid command, perhaps caused by missing closing quotation.
            return

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
        #     return  #type: ignore[unreachable]

        autocomplete_ctx = self.ctx or ctx
        ctx_command = ctx.command

        if getattr(ctx_command, "hidden", False):
            return

        choices, param_choices, param_called = self._get_completion_from_params(
            ctx_command, incomplete, autocomplete_ctx, args
        )

        if isinstance(ctx_command, click.MultiCommand):
            for name in ctx_command.list_commands(ctx):
                command = ctx_command.get_command(ctx, name)
                if getattr(command, "hidden", False):
                    continue

                choices.append(
                    Completion(
                        text_type(name),
                        -len(incomplete),
                        display_meta=getattr(command, "short_help", ""),
                    )
                )

        # If we are inside a parameter that was called, we want to show only
        # relevant choices
        if param_called:
            choices = param_choices

        for item in choices:
            if item.text.startswith(incomplete):
                yield item
