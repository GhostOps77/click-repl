from __future__ import annotations

import pytest

from click_repl._internal_cmds import InternalCommandSystem, _exit_internal
from click_repl.exceptions import ExitReplException, WrongType

internal_command_system = InternalCommandSystem()


def test_register_cmd_from_str():
    internal_command_system.register_command(
        target=_exit_internal,
        names="exit2",
        description="Temporary internal exit command",
    )

    with pytest.raises(ExitReplException):
        internal_command_system.execute(":exit2")


def test_register_cmd_using_decorator():
    @internal_command_system.register_command(
        names="exit3", description="Temporary internal exit command"
    )
    def _exit3():
        raise ExitReplException()

    with pytest.raises(ExitReplException):
        internal_command_system.execute(":exit3")


@pytest.mark.parametrize(
    "test_input",
    [
        {"names": {"h": "help"}, "target": str},
        {"names": ["h", "help", "?"], "target": ""},
    ],
)
def test_register_func_xfail(test_input):
    with pytest.raises(WrongType):
        internal_command_system.register_command(**test_input)
