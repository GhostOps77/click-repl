from __future__ import annotations

import click
from prompt_toolkit.document import Document

from click_repl._internal_cmds import InternalCommandSystem
from click_repl.completer import ClickCompleter


@click.group()
def root_command():
    pass


@root_command.command()
@click.option("--handler", type=click.UNPROCESSED)
def unprocessed_arg(handler):
    pass


c = ClickCompleter(click.Context(root_command), InternalCommandSystem())


def test_unprocessed_arg():
    completions = c.get_completions(Document("unprocessed-arg --handler "))
    assert {x.text for x in completions} == set()
