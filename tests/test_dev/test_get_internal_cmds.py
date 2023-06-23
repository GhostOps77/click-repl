import pytest

import click_repl
from click_repl._internal_cmds import InternalCommandSystem
from click_repl._internal_cmds import repl_exit as repl_exit


internal_command_system = InternalCommandSystem(":", "!")


@pytest.mark.parametrize("test_input", ["exit", "quit", "q"])
def test_get_registered_target_exit_cmd(test_input):
    assert internal_command_system.get_command(test_input) == repl_exit


@pytest.mark.parametrize("test_input", ["hi", "hello", "76q358767"])
def test_get_registered_target_with_default_value(test_input):
    assert internal_command_system.get_command(test_input, "Not Found") == "Not Found"


def test_exit_repl_function():
    with pytest.raises(click_repl.exceptions.ExitReplException):
        click_repl._internal_cmds.repl_exit()
