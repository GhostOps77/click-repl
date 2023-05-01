import pytest

import click_repl
from click_repl._internal_cmds import (_exit_internal, _get_registered_target,
                                       _help_internal)


@pytest.mark.parametrize("test_input", ["help", "h", "?"])
def test_get_registered_target_help_cmd(test_input):
    assert _get_registered_target(test_input) == _help_internal


@pytest.mark.parametrize("test_input", ["exit", "quit", "q"])
def test_get_registered_target_exit_cmd(test_input):
    assert _get_registered_target(test_input) == _exit_internal


@pytest.mark.parametrize("test_input", ["hi", "hello", "76q358767"])
def test_get_registered_target_with_default_value(test_input):
    assert _get_registered_target(test_input, "Not Found") == "Not Found"


def test_exit_repl_function():
    with pytest.raises(click_repl.exceptions.ExitReplException):
        click_repl._internal_cmds.exit()
