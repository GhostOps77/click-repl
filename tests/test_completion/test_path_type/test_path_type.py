import click
from click_repl import ClickCompleter
from prompt_toolkit.document import Document
import glob


@click.group()
def root_command():
    pass


c = ClickCompleter(root_command)


def test_path_type_arg():
    @root_command.command()
    @click.argument("path", type=click.Path())
    def path_type_arg(path):
        pass

    completions = list(c.get_completions(Document("path-type-arg ")))
    assert {x.text for x in completions} == set(glob.glob("*"))

    # completions = list(c.get_completions(Document("path-type-arg ../click")))
    # assert {x.display[0][1] for x in completions} == {
    #     ntpath.basename(i) for i in glob.glob("../click*")
    # }

    completions = list(c.get_completions(Document("path-type-arg ../*")))
    assert {x.text for x in completions} == set()
