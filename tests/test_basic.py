import click
from click_repl import ClickCompleter
from prompt_toolkit.document import Document


@click.group()
def root_command():
    pass


c = ClickCompleter(root_command)


def test_arg_completion():
    @root_command.command()
    @click.argument("handler", type=click.Choice(("foo", "bar")))
    def arg_cmd(handler):
        pass

    completions = list(c.get_completions(Document("arg-cmd ")))
    assert {x.text for x in completions} == {"foo", "bar"}


def test_option_completion():
    @root_command.command()
    @click.option(
        "--handler", "-h", type=click.Choice(("foo", "bar")), help="Demo option"
    )
    def option_cmd(handler):
        pass

    completions = list(c.get_completions(Document("option-cmd ")))
    assert {x.text for x in completions} == {"--handler", "-h"}

    completions = list(c.get_completions(Document("option-cmd -h")))
    assert {x.text for x in completions} == {"-h"}

    completions = list(c.get_completions(Document("option-cmd --h")))
    assert {x.text for x in completions} == {"--handler"}
