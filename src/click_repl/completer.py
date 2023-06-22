import os
import typing as t
from prompt_toolkit.completion import Completer, Completion

from .parser import (
    get_args_and_incomplete_from_args,
    currently_introspecting_args,
    CompletionsProvider,
)
from .utils import get_parsed_ctx_and_state
from .bottom_bar import TOOLBAR


__all__ = ["ClickCompleter"]

IS_WINDOWS = os.name == "nt"


if t.TYPE_CHECKING:
    from typing import Dict, Generator, List, Optional, Final  # noqa: F401

    from prompt_toolkit.formatted_text import AnyFormattedText  # noqa: F401
    from click import Context, MultiCommand, Command  # noqa: F401
    from prompt_toolkit.completion import CompleteEvent  # noqa: F401
    from prompt_toolkit.document import Document  # noqa: F401
    from .parser import ArgsParsingState


class ClickCompleter(Completer):
    """Custom prompt Completion provider for the click-repl app.

    Keyword arguments:
    ---
    :param:`ctx` - The given :class:`~click.MultiCommand`'s Context.
    :param:`cli_args` - List of arguments passed to the group (passed from command line).
    :param:`styles` - Dictionary of style mapping for the Completion objects.
    """

    __slots__ = (
        "cli",
        "cli_ctx",
        "parsed_args",
        "parsed_ctx",
        "internal_cmd_prefix",
        "system_cmd_prefix",
        "completion_parser",
        "state",
    )

    def __init__(
        self,
        ctx: "Context",
        internal_cmd_prefix: "Optional[str]" = None,
        system_cmd_prefix: "Optional[str]" = None,
        styles: "Optional[Dict[str, str]]" = None,
    ) -> None:
        self.cli_ctx: "Final[Context]" = ctx
        self.cli: "Final[MultiCommand]" = ctx.command  # type: ignore[assignment]

        self.parsed_args: "List[str]" = []
        self.parsed_ctx: "Context" = ctx
        self.ctx_command: "Command" = self.cli
        self.state: "ArgsParsingState" = currently_introspecting_args(self.cli, ctx, [])

        self.internal_cmd_prefix = internal_cmd_prefix
        self.system_cmd_prefix = system_cmd_prefix

        if styles is None:
            styles = {
                "command": "ansiblack",
                "option": "ansiblack",
                "argument": "ansiblack",
            }

        self.completion_parser: "Final[CompletionsProvider]" = CompletionsProvider(styles)

    def get_completions(
        self, document: "Document", complete_event: "Optional[CompleteEvent]" = None
    ) -> "Generator[Completion, None, None]":
        """Provides :class:`~prompt_toolkit.completion.Completion`
        objects from the obtained command line string.
        Code analogous to :func:`~click._bashcomplete.do_complete`.

        Keyword arguments:
        ---
        :param:`document` - :class:`~prompt_toolkit.document.Document` object
        containing the incomplete command line string
        :param:`complete_event` - :class:`~prompt_toolkit.completion.CompleteEvent`
        object of the current prompt.

        Yield: :class:`~prompt_toolkit.completion.Completion` objects for
            command line autocompletion
        """

        if (
            self.internal_cmd_prefix is not None
            and self.system_cmd_prefix is not None
            and document.text.startswith(
                (self.internal_cmd_prefix, self.system_cmd_prefix)
            )
        ):
            return

        args, incomplete = get_args_and_incomplete_from_args(document.text_before_cursor)

        try:
            # To Detect the changes in the args
            if self.parsed_args != args:
                self.parsed_args = args

                self.parsed_ctx, self.ctx_command, self.state = get_parsed_ctx_and_state(
                    self.cli_ctx, args
                )

            # print(f'\n(from get_completions) {vars(self.parsed_ctx) = }\n')
            # print(f"\n{self.state = }")
            TOOLBAR.update_state(self.state)  # type: ignore[attr-defined]

            if getattr(self.ctx_command, "hidden", False):
                return

            yield from self.completion_parser.get_completions_for_command(
                self.parsed_ctx, self.state, self.parsed_args, incomplete
            )

        except Exception:
            # raise e
            pass


class ReplCompletion(Completion):
    __slots__ = (
        "text",
        "start_position",
        "display",
        "_display_meta",
        "style",
        "selected_style",
    )

    def __init__(
        self,
        text: str,
        display: "AnyFormattedText" = None,
        display_meta: "AnyFormattedText" = None,
        style: str = "",
        selected_style: str = "",
    ) -> None:
        super().__init__(text, -len(text), display, display_meta, style, selected_style)
