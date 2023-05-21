import os
import typing as t

from prompt_toolkit.completion import Completer, Completion

# from .exceptions import CommandLineParserError
from .utils import _resolve_context
from .parser import ReplParser, _split_args, currently_introspecting_args

__all__ = ["ClickCompleter"]


IS_WINDOWS = os.name == "nt"


if t.TYPE_CHECKING:
    from typing import Dict, Generator, List, Optional, Iterable  # noqa: F401

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
        "parsed_ctx",
        "parsed_args",
        "ctx_command",
        "completion_parser",
        "state",
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

        self.parsed_ctx: "Context" = ctx
        self.parsed_args: "List[str]" = []
        self.ctx_command: "Command" = cli
        self.state = currently_introspecting_args(cli, ctx, [])

        self.internal_cmd_prefix = internal_cmd_prefix
        self.system_cmd_prefix = system_cmd_prefix

        if styles is None:
            styles = dict.fromkeys(("command", "argument", "option"), "")

        self.completion_parser = ReplParser(self.cli, styles)

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

        args, incomplete = _split_args(document.text_before_cursor)

        if self.parsed_args != args:
            self.parsed_args = args
            self.parsed_ctx = _resolve_context(
                self.parsed_args,
                self.cli_ctx,
            )

            self.ctx_command = self.parsed_ctx.command

            self.state = currently_introspecting_args(self.cli, self.parsed_ctx, args)

        # print(f'\n(from get_completions) {vars(self.parsed_ctx) = }\n')

        if getattr(self.ctx_command, "hidden", False):
            return

        # try:
        # print(f'(from completions) {self.parsed_ctx.command} {self.parsed_ctx.params}')
        # print(f' {state = }\n')

        # except Exception as e:
        #     click.echo(f"{type(e).__name__}: {e}")
        # raise CommandLineParserError(f"{type(e).__name__} - {e}")

        yield from self.completion_parser.get_completions_for_command(
            self.parsed_ctx, self.state, args, incomplete
        )


class ReplCompletion(Completion):
    def __init__(
        self,
        text: str,
        display: "AnyFormattedText" = None,
        display_meta: "AnyFormattedText" = None,
        style: str = "",
        selected_style: str = "",
    ) -> None:
        super().__init__(text, -len(text), display, display_meta, style, selected_style)
