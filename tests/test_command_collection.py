import click
import pytest

from click_repl import ClickCompleter
from tests import _to_click6_text
from tests import TestDocument


def test_command_collection():
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

    ctx = click.Context(click.CommandCollection(sources=(foo_group, foobar_group)))
    c = ClickCompleter(ctx)
    completions = c.get_completions(TestDocument("foo"))

    assert {x.text for x in completions} == {
        _to_click6_text(i) for i in ("foo-cmd", "foobar-cmd")
    }


@click.group()
def root_group():
    pass


@root_group.group()
def first_level_command():
    pass


@first_level_command.command()
def second_level_command_one():
    pass


@first_level_command.command()
def second_level_command_two():
    pass


c3 = ClickCompleter(click.Context(root_group))


@pytest.mark.parametrize(
    "test_input, expected",
    [
        (" ", {"first-level-command"}),
        (
            "first-level-command ",
            {
                "second-level-command-one",
                "second-level-command-two",
            },
        ),
    ],
)
def test_completion_multilevel_command(test_input, expected):
    completions = c3.get_completions(TestDocument(test_input))
    assert {x.text for x in completions} == {_to_click6_text(i) for i in expected}
