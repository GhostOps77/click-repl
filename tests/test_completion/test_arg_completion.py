from __future__ import annotations

import click
import pytest
from prompt_toolkit.document import Document

from click_repl.completer import ClickCompleter
from tests import DummyInternalCommandSystem


@click.group()
def root_command():
    pass


@root_command.command()
@click.argument("foo", type=click.BOOL)
def bool_arg(foo):
    pass


@root_command.command()
@click.argument("handler", type=click.Choice(("foo", "bar")))
def arg_choices(handler):
    pass


@root_command.command()
@click.argument("handler", type=click.Choice(("foo", "bar"), case_sensitive=False))
def arg_choices_case_insensitive(handler):
    pass


c = ClickCompleter(click.Context(root_command), DummyInternalCommandSystem())


@pytest.mark.parametrize(
    "test_input, expected",
    [
        ("bool-arg ", {"true", "false"}),
        ("bool-arg t", {"true"}),
        ("bool-arg true ", set()),
    ],
)
def test_boolean_arg(test_input, expected):
    completions = c.get_completions(Document(test_input))
    assert {x.text for x in completions} == expected


@pytest.mark.parametrize(
    "test_input, expected",
    [
        ("arg-choices ", {"foo", "bar"}),
        ("arg-choices f", {"foo"}),
        ("arg-choices foo ", set()),
    ],
)
def test_arg_choices(test_input, expected):
    completions = c.get_completions(Document(test_input))
    assert {x.text for x in completions} == expected


@pytest.mark.parametrize(
    "test_input, expected",
    [
        ("arg-choices-case-insensitive ", {"foo", "bar"}),
        ("arg-choices-case-insensitive F", {"foo"}),
        ("arg-choices-case-insensitive fO", {"foo"}),
        ("arg-choices-case-insensitive B", {"bar"}),
        ("arg-choices-case-insensitive Bar ", set()),
    ],
)
def test_arg_choices_case_insensitive(test_input, expected):
    completions = c.get_completions(Document(test_input))
    assert {x.text for x in completions} == expected
