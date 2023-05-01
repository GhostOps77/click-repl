import click
import pytest
from prompt_toolkit.document import Document

from click_repl import ClickCompleter
from click_repl._globals import HAS_CLICK6


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

    cmd = click.CommandCollection(sources=(foo_group, foobar_group))
    c = ClickCompleter(cmd, click.Context(cmd))
    completions = c.get_completions(Document("foo"))

    if HAS_CLICK6:
        assert {x.text for x in completions} == {"foo_cmd", "foobar_cmd"}
    else:
        assert {x.text for x in completions} == {"foo-cmd", "foobar-cmd"}


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


c3 = ClickCompleter(root_group, click.Context(root_group))


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
    completions = c3.get_completions(Document(test_input))
    if HAS_CLICK6:
        assert set(x.text for x in completions) == expected.replace("-", "_")
    else:
        assert set(x.text for x in completions) == expected
