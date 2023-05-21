import click
from click_repl import ClickCompleter
from prompt_toolkit.document import Document


@click.group()
def root_command():
    pass


@root_command.command()
@click.option("--handler", type=click.UNPROCESSED)
def unprocessed_arg(handler):
    pass


c = ClickCompleter(root_command, click.Context(root_command))


def test_unprocessed_arg():
    completions = list(c.get_completions(Document("unprocessed-arg --handler ")))
    assert {x.text for x in completions} == set()
