from __future__ import annotations

import click
import pytest
from prompt_toolkit.document import Document

from click_repl.completer import ClickCompleter
from tests import InternalCommandSystem


@click.group()
def main():
    pass


@main.command()
@click.option("-s", "--shout", is_flag=True)
def store_true_flag(shout):
    pass


@main.command()
@click.option("-I/-O", "--on/--off")
def bool_flag(on):
    pass


c = ClickCompleter(click.Context(main), InternalCommandSystem())


@pytest.mark.parametrize(
    "test_input, shortest_opts_only, expected",
    [
        ("store-true-flag ", False, {"-s", "--shout"}),
        ("store-true-flag -", False, {"-s", "--shout"}),
        ("store-true-flag --s", False, {"--shout"}),
        ("store-true-flag --shout ", False, set()),
        ("store-true-flag ", True, {"-s"}),
        ("store-true-flag -", True, {"-s", "--shout"}),
        ("store-true-flag --s", True, {"--shout"}),
        ("store-true-flag --shout ", True, set()),
    ],
)
def test_store_true_flags(test_input, shortest_opts_only, expected):
    c.shortest_opt_names_only = shortest_opts_only
    completions = c.get_completions(Document(test_input))
    assert {i.text for i in completions} == expected


@pytest.mark.parametrize(
    "test_input, shortest_opts_only, expected",
    [
        ("bool-flag ", False, {"-I", "-O", "--on", "--off"}),
        ("bool-flag --", False, {"--on", "--off"}),
        ("bool-flag --on ", False, set()),
        ("bool-flag ", True, {"-I", "-O"}),
        ("bool-flag --", True, {"--on", "--off"}),
        ("bool-flag --on ", True, set()),
    ],
)
def test_boolean_flags(test_input, shortest_opts_only, expected):
    c.shortest_opt_names_only = shortest_opts_only
    completions = c.get_completions(Document(test_input))
    assert {i.text for i in completions} == expected
