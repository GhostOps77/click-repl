import click
import os
import sys
from prompt_toolkit.completion import Completion, Completer

from ._parser import (  # type: ignore[attr-defined]
    CompletionParser, get_ctx_for_args, _split_args, text_type
)


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

    def __init__(self, cli, ctx, cli_args=None, styles=None):
        # type: (Group, Context, Optional[List[str]], Optional[Dict[str, str]]) -> None

        self.cli = cli  # type: Group
        self.ctx = ctx  # type: Context

        self.parsed_ctx = self.ctx  # type: Context
        self.parsed_args = []  # type: List[str]
        self.ctx_command = self.cli  # type: Command

        self.cli_args = []  # type: List[str]

        if cli_args is None:
            if self.cli.params:
                self.cli_args.extend(sys.argv[1:])
        else:
            self.cli_args.extend(cli_args)

        if styles is None:
            styles = dict.fromkeys(
                ("command", "argument", "option"), ""
            )

        self.completion_parser = CompletionParser(styles)

    def get_completions(self, document, complete_event=None):
        # type: (Document, Optional[CompleteEvent]) -> Generator[Completion, None, None]

        # Code analogous to click._bashcomplete.do_complete

        tmp = _split_args(document.text_before_cursor)

        if tmp is None:
            return

        args, incomplete = tmp

        if self.parsed_args != args:
            self.parsed_args = args

            self.ctx_command, self.parsed_ctx = get_ctx_for_args(
                self.cli, self.parsed_args, self.cli_args
            )

        # autocomplete_ctx = self.ctx or self.parsed_ctx

        print(f'\n(from get_completions) {vars(self.parsed_ctx) = }\n')
        # print(f'(from get_completions) {vars(autocomplete_ctx) = }\n')

        if getattr(self.ctx_command, "hidden", False):
            return

        choices = []  # type: List[Completion]

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
