import click
import os
import sys
from prompt_toolkit.completion import Completion, Completer

from ._parser import get_ctx_for_args, split_arg_string
from ._completions_parser import CompletionParser, text_type


__all__ = ["ClickCompleter"]


IS_WINDOWS = os.name == "nt"

# typing module introduced in Python 3.5
if sys.version_info >= (3, 5):
    import typing as t

    if t.TYPE_CHECKING:
        from typing import Dict, Generator, Optional, List  # noqa: F401
        from click import Command, Context, Group  # noqa: F401
        from prompt_toolkit.completion import CompleteEvent  # noqa: F401
        from prompt_toolkit.document import Document  # noqa: F401


class ClickCompleter(Completer):
    """Custom prompt Completion provider"""

    __slots__ = (
        "cli", "ctx", "ctx_args", "parsed_ctx", "parsed_args",
        "ctx_command", "completion_parser", "opt_parser"
    )

    def __init__(self, cli, ctx, styles=None):
        # type: (Group, Context, Optional[Dict[str, str]]) -> None

        self.cli = cli  # type: Group
        self.ctx = ctx  # type: Context
        self.ctx_args = sys.argv[1:]  # type: List[str]

        self.parsed_ctx = self.ctx  # type: Context
        self.parsed_args = []  # type: List[str]

        self.ctx_command = self.cli  # type: Command

        if styles is None:
            styles = dict.fromkeys(
                ("command", "argument", "option"), ""
            )

        self.completion_parser = CompletionParser(styles)

    def get_completions(self, document, complete_event=None):
        # type: (Document, Optional[CompleteEvent]) -> Generator[Completion, None, None]

        # Code analogous to click._bashcomplete.do_complete

        document_text_before_cursor = document.text_before_cursor

        if document_text_before_cursor.startswith(("!", ":")):
            return

        # try:
        args = split_arg_string(document_text_before_cursor, posix=False)
        # except ValueError:
        #     # Invalid command, perhaps caused by missing closing quotation.
        #     return

        choices = []  # type: List[Completion]
        cursor_within_command = (
            document_text_before_cursor.rstrip() == document_text_before_cursor
        )

        if args and cursor_within_command:
            # We've entered some text and no space, give completions for the
            # current word.
            incomplete = args.pop()
        else:
            # We've not entered anything, either at all or for the current
            # command, so give all relevant completions for this context.
            incomplete = ""

        if self.parsed_args != args:
            self.parsed_args = args

            self.ctx_command, self.parsed_ctx = get_ctx_for_args(
                self.cli, self.parsed_args, self.ctx_args
            )

        # print(f'\n(from get_completions) {vars(self.parsed_ctx) = }\n')
        # print(f'(from get_completions) {vars(autocomplete_ctx) = }\n')

        if getattr(self.ctx_command, "hidden", False):
            return

        try:
            # choices.extend(
            #     self._get_completion_for_cmd_args(
            #         ctx_command, incomplete, autocomplete_ctx, args
            #     )
            # )
            if isinstance(self.ctx_command, click.MultiCommand):
                for name in self.ctx_command.list_commands(self.parsed_ctx):
                    command = self.ctx_command.get_command(self.parsed_ctx, name)
                    if getattr(command, "hidden", False):
                        continue

                    elif name.startswith(incomplete):
                        choices.append(
                            Completion(
                                text_type(name),
                                -len(incomplete),
                                display_meta=getattr(command, "short_help", ""),
                            )
                        )

            else:
                choices.extend(
                    self.completion_parser._get_completion_for_cmd_args(
                        self.ctx_command,
                        incomplete,
                        self.parsed_ctx,
                        args,
                    )
                )

        except Exception as e:
            click.echo("{}: {}".format(type(e).__name__, str(e)))

        for item in choices:
            yield item
