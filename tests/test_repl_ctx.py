from __future__ import annotations

import click
import pytest

import click_repl
from click_repl._internal_cmds import InternalCommandSystem
from click_repl.core import ReplContext
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


def test_repl_ctx_info_dict():
    repl_ctx = ReplContext(
        click.Context(click.Command(test_repl_ctx_info_dict)), InternalCommandSystem()
    )
    assert repl_ctx.to_info_dict() == {
        "group_ctx": repl_ctx.group_ctx,
        "prompt_kwargs": repl_ctx.prompt_kwargs,
        "internal_command_system": repl_ctx.internal_command_system,
        "session": repl_ctx.session,
        "parent": repl_ctx.parent,
        "_history": repl_ctx._history,
        "current_state": repl_ctx.current_state,
        "bottombar": repl_ctx.bottombar,
    }
