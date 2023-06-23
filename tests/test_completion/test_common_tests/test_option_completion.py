import click
import pytest

from click_repl import ClickCompleter
from tests import TestDocument


@click.group()
def root_command():
    pass


c = ClickCompleter(click.Context(root_command))


def test_option_choices():
    @root_command.command()
    @click.option("--handler", type=click.Choice(("foo", "bar")))
    def option_choices(handler):
        pass

    completions = c.get_completions(TestDocument("option-choices --handler "))
    assert {x.text for x in completions} == {"foo", "bar"}


@root_command.command()
@click.option("--foo", type=click.BOOL)
def bool_option(foo):
    pass


@pytest.mark.parametrize(
    "test_input, expected",
    [
        ("bool-option --foo ", {"true", "false"}),
        ("bool-option --foo t", {"true"}),
    ],
)
def test_boolean_option(test_input, expected):
    completions = c.get_completions(TestDocument(test_input))
    assert {x.text for x in completions} == expected


@root_command.command()
@click.option("--handler", "-h", type=click.Choice(("foo", "bar")), help="Demo option")
def option_cmd(handler):
    pass


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("option-cmd ", {"--handler", "-h"}),
        ("option-cmd -h", {"-h"}),
        ("option-cmd --h", {"--handler"}),
    ],
)
def test_option_completion(test_input, expected):
    completions = c.get_completions(TestDocument(test_input))
    assert {x.text for x in completions} == expected
