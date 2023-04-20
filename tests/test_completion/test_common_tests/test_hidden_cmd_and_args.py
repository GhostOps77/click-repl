import click
from click_repl import ClickCompleter
from prompt_toolkit.document import Document
import pytest


@click.group()
def root_command():
    pass


c = ClickCompleter(root_command, click.Context(root_command))


def test_hidden_cmd():
    @root_command.command(hidden=True)
    @click.option("--handler", "-h")
    def hidden_cmd(handler):
        pass

    completions = c.get_completions(Document("hidden-"))
    assert {x.text for x in completions} == set()


def test_hidden_option():
    @root_command.command()
    @click.option("--handler", "-h", hidden=True)
    def hidden_option_cmd(handler):
        pass

    completions = c.get_completions(Document("hidden-option-cmd "))
    assert {x.text for x in completions} == set()


@root_command.command(hidden=True)
@click.argument("handler1", type=click.Choice(("foo", "bar")))
@click.option("--handler2", type=click.Choice(("foo", "bar")))
def args_choices_hidden_cmd(handler):
    pass


@pytest.mark.parametrize("test_input", [
    "args-choices-hidden-cmd foo ",
    "args-choices-hidden-cmd --handler "
])
def test_args_of_hidden_command(test_input):
    completions = c.get_completions(Document(test_input))
    assert {x.text for x in completions} == set()
