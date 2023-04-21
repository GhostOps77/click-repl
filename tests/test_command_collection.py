import click
from click_repl import ClickCompleter, repl
from prompt_toolkit.document import Document
import pytest


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

    assert {x.text for x in completions} == {"foo-cmd", "foobar-cmd"}


@click.group(invoke_without_command=True)
@click.option("--user", required=True)
@click.pass_context
def cmd(ctx, user):
    if ctx.invoked_subcommand is None:
        click.echo("Top-level user: {}".format(user))
        repl(ctx)


@cmd.command()
@click.option("--user")
def c1(user):
    click.echo("Executed C1 with {}!".format(user))


c2 = ClickCompleter(cmd, click.Context(cmd))


@pytest.mark.parametrize("test_input,expected", [(" ", {"c1"}), ("c1 c1", {"--user"})])
def test_subcommand_invocation_from_group(test_input, expected):
    completions = c2.get_completions(Document(test_input))
    assert {x.text for x in completions} == expected


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


@pytest.mark.parametrize("test_input, expected", [
    (" ", {"first-level-command"}),
    ("first-level-command ", {
        "second-level-command-one",
        "second-level-command-two",
    })
])
def test_completion_multilevel_command(test_input, expected):
    completions = c3.get_completions(Document(test_input))
    assert set(x.text for x in completions) == expected
