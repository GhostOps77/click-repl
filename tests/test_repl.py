import contextlib
import sys
from io import StringIO

import click
import pytest

import click_repl


@contextlib.contextmanager
def mock_stdin(text):
    old_stdin = sys.stdin
    try:
        sys.stdin = StringIO(text)
        yield sys.stdin
    finally:
        sys.stdin = old_stdin


def test_simple_repl():
    @click.group()
    def cli():
        pass

    @cli.command()
    @click.option("--baz", is_flag=True)
    def foo(baz):
        print("Foo!")

    @cli.command()
    @click.option("--foo", is_flag=True)
    def bar(foo):
        print("Bar!")

    click_repl.register_repl(cli)

    with pytest.raises(SystemExit):
        cli(args=[], prog_name="test_simple_repl")


def test_repl_dispatches_subcommand(capsys):
    @click.group(invoke_without_command=True)
    @click.pass_context
    def cli(ctx):
        if ctx.invoked_subcommand is None:
            click_repl.repl(ctx)

    @cli.command()
    def foo():
        print("Foo!")

    with mock_stdin("foo\n"):
        with pytest.raises(SystemExit):
            cli(args=[], prog_name="test_repl_dispatch_subcommand")

    assert capsys.readouterr().out.replace("\r\n", "\n") == "Foo!\n"


def test_group_command_called(capsys):
    @click.group(invoke_without_command=True)
    @click.pass_context
    def cli(ctx):
        print("cli()")
        if ctx.invoked_subcommand is None:
            click_repl.repl(ctx)

    @cli.command()
    def foo():
        print("Foo!")

    @cli.command()
    def bar():
        print("Bar!")

    with mock_stdin("foo\nbar\n"):
        with pytest.raises(SystemExit):
            cli(args=[], prog_name="test_group_called")

    assert capsys.readouterr().out.replace("\r\n", "\n") == (
        "cli()\ncli()\nFoo!\ncli()\nBar!\n"
    )


def test_independant_args(capsys):
    @click.group(invoke_without_command=True)
    @click.argument("argument")
    @click.pass_context
    def cli(ctx, argument):
        print(f"cli({argument})")
        if ctx.invoked_subcommand is None:
            click_repl.repl(ctx)

    @cli.command()
    def foo():
        print("Foo!")

    with mock_stdin("foo\n"):
        with pytest.raises(SystemExit):
            cli(args=["command-line-argument"], prog_name="test_group_called_once")
    assert capsys.readouterr().out.replace("\r\n", "\n") == (
        "cli(command-line-argument)\ncli(command-line-argument)\nFoo!\n"
    )


def test_independant_options(capsys):
    @click.group(invoke_without_command=True)
    @click.option("--option")
    @click.pass_context
    def cli(ctx, option):
        print(f"cli({option})")
        if ctx.invoked_subcommand is None:
            click_repl.repl(ctx)

    @cli.command()
    def foo():
        print("Foo!")

    with mock_stdin("foo\n"):
        with pytest.raises(SystemExit):
            cli(
                args=["--option", "command-line-argument"],
                prog_name="test_independant_options",
            )
    assert capsys.readouterr().out.replace("\r\n", "\n") == (
        "cli(command-line-argument)\ncli(command-line-argument)\nFoo!\n"
    )


@click.group(invoke_without_command=True)
@click.argument("argument")
@click.option("--option1", default=1, type=click.STRING)
@click.option("--option2")
@click.pass_context
def cmd(ctx, argument, option1, option2):
    print(f"cli({argument}, {option1}, {option2})")
    if ctx.invoked_subcommand is None:
        click_repl.repl(ctx)


@cmd.command()
def foo():
    print("Foo!")


@pytest.mark.parametrize(
    "args, expected",
    [
        (["hi"], "cli(hi, 1, None)\ncli(hi, 1, None)\nFoo!\n"),
        (
            ["--option1", "opt1", "hi"],
            "cli(hi, opt1, None)\ncli(hi, opt1, None)\nFoo!\n",
        ),
        (["--option2", "opt2", "hi"], "cli(hi, 1, opt2)\ncli(hi, 1, opt2)\nFoo!\n"),
        (
            ["--option1", "opt1", "--option2", "opt2", "hi"],
            "cli(hi, opt1, opt2)\ncli(hi, opt1, opt2)\nFoo!\n",
        ),
    ],
)
def test_group_with_multiple_args(capsys, args, expected):
    with mock_stdin("foo\n"):
        with pytest.raises(SystemExit):
            cmd(args=args, prog_name="test_group_with_multiple_args")
    assert capsys.readouterr().out.replace("\r\n", "\n") == expected


def test_inputs(capfd):
    @click.group(invoke_without_command=True)
    @click.pass_context
    def cli(ctx):
        if ctx.invoked_subcommand is None:
            ctx.invoke(repl)

    @cli.command()
    def repl():
        click_repl.repl(click.get_current_context())

    try:
        cli(args=[], prog_name="test_inputs")
    except (SystemExit, Exception) as e:
        if (
            type(e).__name__ == "prompt_toolkit.output.win32.NoConsoleScreenBufferError"
            and str(e) == "No Windows console found. Are you running cmd.exe?"
        ):
            pass

    captured_stdout = capfd.readouterr().out.replace("\r\n", "\n")
    assert captured_stdout == ""


def test_subcommand_invocation(capfd):
    @click.group(invoke_without_command=True)
    @click.pass_context
    def group_level1(ctx):
        print("from level1")
        if not ctx.invoked_subcommand:
            click_repl.repl(ctx)

    @group_level1.group(invoke_without_command=True)
    @click.pass_context
    def group_level2(ctx):
        print("from level2")
        if not ctx.invoked_subcommand:
            click_repl.repl(ctx)

    @group_level2.command()
    def lvl2_command():
        print("from lvl2 command")

    with mock_stdin("group-level2\nlvl2-command\n"):
        with pytest.raises(SystemExit):
            group_level1(args=[], prog_name="test_subcommand_invocation")
    assert (
        capfd.readouterr().out.replace("\r\n", "\n")
        == """from level1
from level1
from level2
from level2
from lvl2 command
"""
    )
