import os
import typing as t

from prompt_toolkit.completion import Completer
from prompt_toolkit.completion import Completion

from ._internal_cmds import InternalCommandSystem
from .bottom_bar import TOOLBAR
from .parser import CompletionsProvider
from .utils import _resolve_state

__all__ = ["ClickCompleter"]

IS_WINDOWS = os.name == "nt"


if t.TYPE_CHECKING:
    from typing import Dict, Final, Generator, Optional  # noqa: F401

    from click import Context, MultiCommand  # noqa: F401
    from prompt_toolkit.completion import CompleteEvent  # noqa: F401
    from prompt_toolkit.document import Document  # noqa: F401
    from prompt_toolkit.formatted_text import AnyFormattedText  # noqa: F401


class ClickCompleter(Completer):
    """Custom prompt Completion provider for the click-repl app.

    Keyword arguments:
    ---
    :param:`ctx` - The given :class:`~click.MultiCommand`'s Context.
    :param:`cli_args` - List of arguments passed to the group (passed from command line).
    :param:`styles` - Dictionary of style mapping for the Completion objects.
    """

    # __slots__ = (
    #     "cli",
    #     "cli_ctx",
    #     "parsed_args",
    #     "parsed_ctx",
    #     "ctx_command",
    #     "internal_command_prefix",
    #     "system_command_prefix",
    #     "completion_parser",
    #     "state",
    # )

    def __init__(
        self,
        ctx: "Context",
        internal_commands_system: "InternalCommandSystem",
        styles: "Optional[Dict[str, str]]" = None,
    ) -> None:
        self.cli_ctx: "Final[Context]" = ctx
        self.cli: "Final[MultiCommand]" = ctx.command  # type: ignore[assignment]

        # self.parsed_args: "Tuple[str, ...]" = ()
        # self.parsed_ctx: "Context" = ctx
        # self.ctx_command: "Command" = self.cli
        # self.state: "ArgsParsingState" = currently_introspecting_args(self.cli, ctx, [])

        if styles is None:
            styles = {
                "command": "",
                "option": "",
                "argument": "",
            }

        self.internal_commands_system = internal_commands_system
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

        if self.internal_commands_system.get_prefix(document.text_before_cursor):
            TOOLBAR.state_reset()
            return

        try:
            # # To Detect the changes in the args
            # if self.parsed_args != args:
            #     # print('different cmds')
            #     self.parsed_args = args

            parsed_ctx, ctx_command, state, args, incomplete = _resolve_state(
                self.cli_ctx, document.text_before_cursor
            )

            # print(f'\n(from get_completions) {vars(self.parsed_ctx) = }\n')
            # print(f"\n{self.state = }")
            TOOLBAR.update_state(state)  # type: ignore[attr-defined]

            if getattr(ctx_command, "hidden", False):
                return

            # print(f'{self.state = }')
            yield from self.completion_parser.get_completions_for_command(
                parsed_ctx, state, args, incomplete
            )

        except Exception:
            TOOLBAR.state_reset()
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
        **attrs: "t.Any"
    ) -> None:
        attrs.setdefault("start_position", -len(text))

        super().__init__(
            text=text,
            display=display,
            display_meta=display_meta,
            style=style,
            selected_style=selected_style,
            **attrs,
        )
