from __future__ import annotations

import pytest

from click_repl._internal_cmds import InternalCommandSystem
from click_repl._internal_cmds import _exit_internal
from click_repl.exceptions import WrongType

internal_command_system = InternalCommandSystem(":", "!")


def test_register_cmd_from_str():
    internal_command_system.register_command(
        target=_exit_internal,
        names="exit2",
        description="Temporary internal exit command",
    )


@pytest.mark.parametrize(
    "test_input",
    [
        {"names": {"h": "help"}, "target": str},
        {"names": ["h", "help", "?"], "target": ""},
    ],
)
def test_register_func_xfails(test_input):
    with pytest.raises(WrongType):
        internal_command_system.register_command(**test_input)
