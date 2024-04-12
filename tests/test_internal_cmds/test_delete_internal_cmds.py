from __future__ import annotations

import pytest

from click_repl.exceptions import InternalCommandNotFound
from click_repl.internal_commands import InternalCommandSystem
from click_repl.internal_commands import repl_exit as repl_exit

internal_command_system = InternalCommandSystem()


@pytest.mark.parametrize("command_name", ["exit", "help"])
def test_delete_existing_internal_commands(command_name):
    internal_command_system.remove_command(command_name, remove_all_aliases=False)
    assert internal_command_system.get_command(command_name, None) is None


@pytest.mark.parametrize("test_input", ["hi", "hello", "76q358767"])
def test_xfail_delete_non_existing_internal_commandsands(test_input):
    with pytest.raises(InternalCommandNotFound):
        assert internal_command_system.remove_command(test_input)


@pytest.mark.parametrize("command_name", ["q", "?"])
def test_delete_existing_internal_commands_with_all_of_its_prefixes(command_name):
    internal_command_system.remove_command(command_name)
    assert internal_command_system.get_command(command_name, None) is None
