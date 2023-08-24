import click
import pytest
from prompt_toolkit.document import Document

from click_repl import ClickCompleter


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
    completions = c.get_completions(Document("foo"))

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
    completions = c3.get_completions(Document(test_input))
    assert {x.text for x in completions} == expected


@click.group()
def cli():
    pass


@cli.group(chain=True)
@click.argument("arg", type=click.Choice(["hi", "hi2", "hi3"]))
def chained_group(arg):
    pass


@chained_group.command("subcommand1")
@click.argument("arg1", type=click.Choice(["hlllo", "hello2", "hello3"]))
@click.option("--opt1")
def subcommand1(arg1, opt1):
    pass


@chained_group.command("subcommand2")
@click.option("--opt2")
def subcommand2(opt2):
    pass


c4 = ClickCompleter(click.Context(cli))


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("chained-group ", {"hi", "hi2", "hi3"}),
        ("chained-group hi ", {"subcommand1", "subcommand2"}),
        ("chained-group hi subcommand1 ", {"hlllo", "hello2", "hello3", "--opt1"}),
        ("chained-group hi subcommand1 hlllo ", {"subcommand1", "subcommand2"}),
        (
            "chained-group hi subcommand1 hlllo subcommand2 ",
            {"--opt2", "subcommand1", "subcommand2"},
        ),
    ],
)
def test_chained_group(test_input, expected):
    completions = c4.get_completions(Document(test_input))
    assert {x.text for x in completions} == expected
