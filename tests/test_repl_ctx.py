import click
import pytest

import click_repl
from tests import mock_stdin


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    if ctx.invoked_subcommand is None:
        click_repl.repl(ctx)


@cli.command()
def hello():
    print("Hello!")


@cli.command()
@click_repl.pass_context
def reply(repl_ctx):
    assert repl_ctx.prompt_message is None
    assert list(repl_ctx.history()) == ["reply", "hello"]


def test_repl_ctx_history(capsys):
    with mock_stdin("hello\nreply\n"):
        with pytest.raises(SystemExit):
            cli(args=[], prog_name="test_repl_ctx_history")

    assert capsys.readouterr().out.replace("\r\n", "\n") == "Hello!\n"
