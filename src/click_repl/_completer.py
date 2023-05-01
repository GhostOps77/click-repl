import os
import typing as t

import click
from prompt_toolkit.completion import Completer, Completion

from ._parser import Completioner, _split_args, _get_ctx_for_args

__all__ = ["ClickCompleter"]


IS_WINDOWS = os.name == "nt"


if t.TYPE_CHECKING:
    from typing import Dict, Generator, List, Optional, Tuple  # noqa: F401

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
        "ctx",
        "cli_args",
        "internal_cmd_prefix",
        "system_cmd_prefix",
        "parsed_ctx",
        "parsed_args",
        "ctx_command",
        "completion_parser",
    )

    def __init__(
        self,
        cli: "Group",
        ctx: "Context",
        cli_args: "List[str]" = [],
        internal_cmd_prefix: str = ":",
        system_cmd_prefix: str = "!",
        styles: "Optional[Dict[str, str]]" = None,
    ) -> None:
        self.cli: "Group" = cli
        self.ctx: "Context" = ctx

        self.parsed_ctx: "Context" = self.ctx
        self.parsed_args: "List[str]" = []
        self.ctx_command: "Command" = self.cli
        self.cli_args: "List[str]" = cli_args

        self.internal_cmd_prefix = internal_cmd_prefix
        self.system_cmd_prefix = system_cmd_prefix

        if styles is None:
            styles = dict.fromkeys(("command", "argument", "option"), "")

        self.completion_parser = Completioner(styles)

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

            self.ctx_command, self.parsed_ctx = _get_ctx_for_args(
                self.cli, tuple(self.parsed_args), tuple(self.cli_args)
            )

        # autocomplete_ctx = self.ctx or self.parsed_ctx

        # print(f'\n(from get_completions) {vars(self.parsed_ctx) = }\n')
        # if self.parsed_ctx.parent is not None:
        #   print(f'\n(parent ctx) {self.parsed_ctx.parent.command = }\n')

        # print(f'\n{self.cli_args = }')
        # print(f'(from get_completions) {vars(autocomplete_ctx) = }\n')

        if getattr(self.ctx_command, "hidden", False):
            return

        choices: "List[Completion]" = []

        try:
            choices.extend(
                self.completion_parser._get_completions_for_command(
                    self.ctx_command, self.parsed_ctx, args, incomplete
                )
            )

        except Exception as e:
            click.echo(f"{type(e).__name__}: {e}")

        yield from choices


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
