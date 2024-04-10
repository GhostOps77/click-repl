from __future__ import annotations

import click
import pytest
from prompt_toolkit.document import Document

from click_repl._internal_command import InternalCommandSystem
from click_repl.completer import ClickCompleter


@click.group()
def main():
    pass


completer = ClickCompleter(click.Context(main), InternalCommandSystem(";", "!"))


@pytest.mark.parametrize(
    "test_input, expected",
    [
        (";", {"?", "q", "cls"}),
        (";h", {"help"}),
        (";e", {"exit"}),
        (";q", {"quit"}),
        (";c", {"cls"}),
        (";cls", set()),
    ],
)
def test_internal_command_suggestion(test_input, expected):
    completions = completer.get_completions(Document(test_input))
    assert {i.text for i in completions} == expected
