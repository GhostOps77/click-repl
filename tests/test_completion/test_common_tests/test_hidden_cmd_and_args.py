import click
import pytest
from prompt_toolkit.document import Document

from click_repl import ClickCompleter


@click.group()
def root_command():
    pass


c = ClickCompleter(click.Context(root_command))


@pytest.mark.skipif(
    click.__version__[0] < "8",
    reason="click-v8 built-in shell complete is not available, so skipped",
)
def test_hidden_option():
    @root_command.command()
    @click.option("--handler", "-h", hidden=True)
    def hidden_option_cmd(handler):
        pass

    completions = c.get_completions(Document("hidden-option-cmd "))
    assert {x.text for x in completions} == set()


@pytest.mark.skipif(
    click.__version__[0] < "8",
    reason="click-v8 built-in shell complete is not available, so skipped",
)
@pytest.mark.parametrize(
    "test_input",
    [
        "args-",
        "args-choices",
        "args-choices-hidden-cmd foo ",
        "args-choices-hidden-cmd --handler ",
        "args-choices-hidden-cmd --handler ",
    ],
)
def test_args_of_hidden_command(test_input):
    @root_command.command(hidden=True)
    @click.argument("handler1", type=click.Choice(("foo", "bar")))
    @click.option("--handler2", type=click.Choice(("foo", "bar")))
    def args_choices_hidden_cmd(handler):
        pass

    completions = c.get_completions(Document(test_input))
    assert {x.text for x in completions} == set()
