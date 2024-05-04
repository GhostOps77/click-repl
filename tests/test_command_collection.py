from __future__ import annotations

import click
from prompt_toolkit.document import Document

from click_repl.completer import ClickCompleter
from tests import DummyInternalCommandSystem


@click.group()
def foo_group():
    pass


@foo_group.command()
def foo_cmd():
    pass


@click.group()
def foobar_group():
    pass


@foobar_group.command()
def foobar_cmd():
    pass


cmd = click.CommandCollection(sources=(foo_group, foobar_group))


def test_command_collection():
    c = ClickCompleter(click.Context(cmd), DummyInternalCommandSystem())
    completions = list(c.get_completions(Document("foo")))

    assert {x.text for x in completions} == {"foo-cmd", "foobar-cmd"}
