import click
import pytest
from prompt_toolkit.document import Document

from click_repl import ClickCompleter, repl


@click.group(invoke_without_command=True)
@click.option("--user", required=True)
@click.pass_context
def cmd(ctx, user):
    if ctx.invoked_subcommand is None:
        click.echo(f"Top-level user: {user}")
        repl(ctx)


@cmd.command()
@click.option("--user")
def c1(user):
    click.echo(f"Executed C1 with {user}!")


c = ClickCompleter(cmd.make_context("", args=["--user", "hi"]))


@pytest.mark.parametrize("test_input, expected", [(" ", "c1"), ("c1 ", "--user")])
def test_subcommand_invocation_from_group(test_input, expected):
    completions = c.get_completions(Document(test_input))
    assert {x.text for x in completions} == {expected}


@click.group(invoke_without_command=True)
@click.argument("rg", required=False)
@click.option("--opt", nargs=5, required=True)
@click.pass_context
def cli(ctx, arg, opt):
    pass


@cli.command()
@click.argument("cmd_arg", type=click.Choice(["foo", "foo2"]))
def cmd(cmd_arg):
    pass


c2 = ClickCompleter(
    cli.make_context("", args=["--opt", "hi1", "hi2", "hi3", "hi4", "hi5", "hii"])
)


@pytest.mark.parametrize(
    "test_input, expected", [(" ", {"cmd"}), ("cmd ", {"foo", "foo2"})]
)
def test_subcommand_invocation_for_group_with_opts(test_input, expected):
    completions = c2.get_completions(Document(test_input))
    assert {x.text for x in completions} == expected
