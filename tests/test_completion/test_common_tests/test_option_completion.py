import click
from click_repl import ClickCompleter
from prompt_toolkit.document import Document
import pytest


@click.group()
def root_command():
    pass


c = ClickCompleter(root_command)


def test_option_choices():
    @root_command.command()
    @click.option("--handler", type=click.Choice(("foo", "bar")))
    def option_choices(handler):
        pass

    completions = list(c.get_completions(Document("option-choices --handler ")))
    assert {x.text for x in completions} == {"foo", "bar"}


def test_boolean_option():
    @root_command.command()
    @click.option("--foo", type=click.BOOL)
    def bool_option(foo):
        pass

    completions = list(c.get_completions(Document("bool-option --foo ")))
    assert {x.text for x in completions} == {"true", "false"}

    completions = list(c.get_completions(Document("bool-option --foo t")))
    assert {x.text for x in completions} == {"true"}


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
    completions = list(c.get_completions(Document(test_input)))
    assert {x.text for x in completions} == expected
