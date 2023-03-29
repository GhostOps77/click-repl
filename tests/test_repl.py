import click
import click_repl
import contextlib
import sys
import pytest
from io import StringIO


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
        print("cli({})".format(argument))
        if ctx.invoked_subcommand is None:
            click_repl.repl(ctx)

    @cli.command()
    def foo():
        print("Foo!")

    with mock_stdin("foo\n"):
        with pytest.raises(SystemExit):
            cli(args=["command-line-argument"], prog_name="test_group_called_once")
    assert capsys.readouterr().out.replace('\r\n', '\n') == (
        "cli(command-line-argument)\ncli(command-line-argument)\nFoo!\n"
    )


def test_independant_options(capsys):
    @click.group(invoke_without_command=True)
    @click.option("--option")
    @click.pass_context
    def cli(ctx, option):
        print("cli({})".format(option))
        if ctx.invoked_subcommand is None:
            click_repl.repl(ctx)

    @cli.command()
    def foo():
        print("Foo!")

    with mock_stdin("foo\n"):
        with pytest.raises(SystemExit):
            cli(
                args=["--option", "command-line-argument"],
                prog_name="test_group_called_once"
            )
    assert capsys.readouterr().out.replace('\r\n', '\n') == (
        "cli(command-line-argument)\ncli(command-line-argument)\nFoo!\n"
    )


@pytest.mark.parametrize("args, expected", [
    (['hi'], "cli(hi, None, None)\ncli(hi, None, None)\nFoo!\n"),
    (['hi', '--option1', 'opt1'], "cli(hi, opt1, None)\ncli(hi, opt1, None)\nFoo!\n"),
    (['hi', '--option2', 'opt2'], "cli(hi, None, opt2)\ncli(hi, None, opt2)\nFoo!\n"),
    (['hi', '--option1', 'opt1', '--option2', 'opt2'],
     "cli(hi, opt1, opt2)\ncli(hi, opt1, opt2)\nFoo!\n"),
])
def test_group_with_multiple_args(capsys, args, expected):
    @click.group(invoke_without_command=True)
    @click.argument("argument")
    @click.option("--option1", default=1)
    @click.option("--option1")
    @click.pass_context
    def cli(ctx, argument, option1, option2):
        print("cli({}, {}, {})".format(argument, option1, option2))
        if ctx.invoked_subcommand is None:
            click_repl.repl(ctx)

    @cli.command()
    def foo():
        print("Foo!")

    with mock_stdin("foo\n"):
        with pytest.raises(SystemExit):
            cli(
                args=args,
                prog_name="test_group_called_once"
            )
    assert capsys.readouterr().out.replace('\r\n', '\n') == expected


def test_exit_repl_function():
    with pytest.raises(click_repl.exceptions.ExitReplException):
        click_repl.utils.exit()


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
