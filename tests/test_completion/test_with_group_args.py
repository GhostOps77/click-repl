import click
from click_repl import ClickCompleter, repl
from prompt_toolkit.document import Document
import pytest


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


cli_args = ['--user', 'hi']
c = ClickCompleter(cmd, cmd.make_context('', args=cli_args))
c.ctx_args = cli_args


@pytest.mark.parametrize("test_input, expected", [(" ", "c1"), ("c1 ", "--user")])
def test_subcommand_invocation_from_group(test_input, expected):
    completions = c.get_completions(Document(test_input))
    assert {x.text for x in completions} == {expected}


@click.group(invoke_without_command=True)
@click.argument('rg', required=False)
@click.option('--opt', nargs=5, required=True)
@click.pass_context
def cli(ctx, arg, opt):
    pass


@cli.command()
@click.argument('cmd_arg', type=click.Choice(['foo', 'foo2']))
def cmd(cmd_arg):
    pass


cli_args = ['--opt', 'hi1', 'hi2', 'hi3', 'hi4', 'hi5', 'hii']
c2 = ClickCompleter(cli, cli.make_context(
    '', args=cli_args
))
c2.ctx_args = cli_args


@pytest.mark.parametrize("test_input, expected", [
    (" ", {"cmd"}), ("cmd ", {'foo', 'foo2'})
])
def test_subcommand_invocation_for_group_with_opts(test_input, expected):
    completions = c2.get_completions(Document(test_input))
    assert {x.text for x in completions} == expected
