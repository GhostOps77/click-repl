import pytest

import click_repl
from click_repl._internal_cmds import _execute_internal_and_sys_cmds


@pytest.mark.parametrize("test_input", [":help", ":h", ":?"])
def test_internal_help_commands(capsys, test_input):
    _execute_internal_and_sys_cmds(test_input, ":", None)

    captured_stdout = capsys.readouterr().out

    assert (
        captured_stdout
        == """REPL help:

  External/System Commands:
    prefix external commands with "!"

  Internal Commands:
    prefix internal commands with ":"
    :exit, :q, :quit  Exits the repl
    :clear, :cls      Clears screen
    :?, :h, :help     Displays general help information

"""
    )


@pytest.mark.parametrize("test_input", [":exit", ":quit", ":q"])
def test_internal_exit_commands(test_input):
    with pytest.raises(click_repl.ExitReplException):
        _execute_internal_and_sys_cmds(test_input, ":", None)


@pytest.mark.parametrize("test_input", [":exit", ":quit", ":q"])
def test_no_internal_commands(capfd, test_input):
    _execute_internal_and_sys_cmds(test_input, None, None)

    captured_stdout = capfd.readouterr().out.replace("\r\n", "\n")
    assert captured_stdout == ""
