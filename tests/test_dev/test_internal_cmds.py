import pytest

import click_repl
from click_repl._internal_cmds import InternalCommandSystem


internal_command_system = InternalCommandSystem(":", "!")


@pytest.mark.parametrize("test_input", [":help", ":h", ":?"])
def test_internal_help_commands(capsys, test_input):
    internal_command_system.execute(test_input)

    captured_stdout = capsys.readouterr().out.replace("\r\n", "\n")

    assert (
        captured_stdout
        == """REPL help:

  External/System Commands:
    Prefix External commands with "!"

  Internal Commands:
    Prefix Internal commands with ":"
    :exit, :q, :quit  Exits the REPL
    :clear, :cls      Clears screen
    :?, :h, :help     Displays general help information

"""
    )


@pytest.mark.parametrize("test_input", [":exit", ":quit", ":q"])
def test_internal_exit_commands(test_input):
    with pytest.raises(click_repl.ExitReplException):
        internal_command_system.execute(test_input)


no_internal_cmds_obj = InternalCommandSystem(None, None)


@pytest.mark.parametrize("test_input", [":exit", ":quit", ":q"])
def test_no_internal_commands(capfd, test_input):
    no_internal_cmds_obj.execute(test_input)

    captured_stdout = capfd.readouterr().out.replace("\r\n", "\n")
    assert captured_stdout == ""
