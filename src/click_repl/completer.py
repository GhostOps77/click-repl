import os
import typing as t

from prompt_toolkit.completion import Completer, Completion

# from .core import toolbar_func

# from .exceptions import CommandLineParserError
from .utils import get_parsed_ctx_and_state
from .parser import CompletionsProvider

__all__ = ["ClickCompleter"]


IS_WINDOWS = os.name == "nt"


if t.TYPE_CHECKING:
    from typing import Dict, Generator, List, Optional  # noqa: F401

    from prompt_toolkit.formatted_text import AnyFormattedText  # noqa: F401
    from click import Command, Context, Group  # noqa: F401
    from prompt_toolkit.completion import CompleteEvent  # noqa: F401
    from prompt_toolkit.document import Document  # noqa: F401


class ClickCompleter(Completer):
    """Custom prompt Completion provider for the click-repl app.

    Keyword arguments:
    ---
    :param:`cli` - The Group/MultiCommand Object that has all the subcommands.
    :param:`ctx` - The given Group's Context.
    :param:`cli_args` - List of arguments passed to the group (passed from command line).
    :param:`styles` - Dictionary of style mapping for the Completion objects.
    """

    __slots__ = (
        "cli",
        "cli_ctx",
        "internal_cmd_prefix",
        "system_cmd_prefix",
        "completion_parser",
    )

    def __init__(
        self,
        cli: "Group",
        ctx: "Context",
        internal_cmd_prefix: str = ":",
        system_cmd_prefix: str = "!",
        styles: "Optional[Dict[str, str]]" = None,
    ) -> None:
        self.cli: "Group" = cli
        self.cli_ctx: "Context" = ctx

        self.internal_cmd_prefix = internal_cmd_prefix
        self.system_cmd_prefix = system_cmd_prefix

        if styles is None:
            styles = dict.fromkeys(("command", "argument", "option"), "")

        self.completion_parser = CompletionsProvider(self.cli, styles)

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

        if document.text.startswith((self.internal_cmd_prefix, self.system_cmd_prefix)):
            return

        try:
            (
                parsed_ctx,
                parsed_args,
                incomplete,
                ctx_command,
                state,
            ) = get_parsed_ctx_and_state(self.cli_ctx, document.text_before_cursor)

            # print(f'\n(from get_completions) {vars(self.parsed_ctx) = }\n')
            # print(f'{self.state = }')

            if getattr(ctx_command, "hidden", False):
                return

            # except Exception as e:
            #     click.echo(f"{type(e).__name__}: {e}")
            # raise CommandLineParserError(f"{type(e).__name__} - {e}")

            yield from self.completion_parser.get_completions_for_command(
                parsed_ctx, state, parsed_args, incomplete
            )

        except Exception:
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
