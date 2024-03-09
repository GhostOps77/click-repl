from __future__ import annotations

import click
import pytest
from prompt_toolkit.document import Document

from click_repl._internal_cmds import InternalCommandSystem
from click_repl.completer import ClickCompleter


@click.group(invoke_without_command=True)
@click.option("--user", required=True)
@click.pass_context
def cmd(ctx, user):
    pass


@cmd.command()
@click.option("--opt")
def c1(user):
    pass


c = ClickCompleter(cmd.make_context("", args=["--user", "hi"]), InternalCommandSystem())


@pytest.mark.parametrize("test_input, expected", [(" ", {"c1"}), ("c1 ", {"--opt"})])
def test_subcommand_invocation_from_group(test_input, expected):
    completions = c.get_completions(Document(test_input))
    assert {x.text for x in completions} == expected


@click.group(invoke_without_command=True)
@click.argument("arg", required=False)
@click.option("--opt", nargs=5, required=True)
@click.pass_context
def cli(ctx, arg, opt):
    pass


@cli.command()
@click.argument("cmd_arg", type=click.Choice(["foo", "foo2"]))
def cmd(cmd_arg):
    pass


c2 = ClickCompleter(
    cli.make_context("", args=["--opt", "hi1", "hi2", "hi3", "hi4", "hi5", "hii"]),
    InternalCommandSystem(),
)


@pytest.mark.parametrize(
    "test_input, expected", [(" ", {"cmd"}), ("cmd ", {"foo", "foo2"})]
)
def test_subcommand_invocation_for_group_with_opts(test_input, expected):
    completions = c2.get_completions(Document(test_input))
    assert {x.text for x in completions} == expected
