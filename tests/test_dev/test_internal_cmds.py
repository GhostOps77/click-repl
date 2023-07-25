import click
import pytest

from click_repl._internal_cmds import InternalCommandSystem
from click_repl.core import ReplContext
from click_repl.exceptions import ExitReplException


@click.command()
def dummy_cmd():
    pass


internal_command_system = InternalCommandSystem(":", "!")
repl_ctx = ReplContext(click.Context(dummy_cmd), internal_command_system, {})


@pytest.mark.parametrize("test_input", [":help", ":h", ":?"])
def test_internal_help_commands(capsys, test_input):
    with repl_ctx:
        internal_command_system.execute(test_input)

    captured_stdout = capsys.readouterr().out.replace("\r\n", "\n")

    assert (
        captured_stdout
        == """REPL help:

  External/System Commands:
    Prefix External/System commands with "!".

  Internal Commands:
    Prefix Internal commands with ":".
    :clear, :cls      Clears screen.
    :exit, :q, :quit  Exits the REPL.
    :?, :h, :help     Displays general help information.

"""
    )


@pytest.mark.parametrize("test_input", [":exit", ":quit", ":q"])
def test_internal_exit_commands(test_input):
    with pytest.raises(ExitReplException):
        internal_command_system.execute(test_input)


no_internal_cmds_obj = InternalCommandSystem(None, None)


@pytest.mark.parametrize("test_input", [":exit", ":quit", ":q"])
def test_no_internal_commands(capfd, test_input):
    no_internal_cmds_obj.execute(test_input)

    captured_stdout = capfd.readouterr().out.replace("\r\n", "\n")
    assert captured_stdout == ""
