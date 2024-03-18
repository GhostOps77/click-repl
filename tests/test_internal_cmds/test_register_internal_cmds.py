from __future__ import annotations

import pytest

from click_repl.exceptions import ExitReplException, WrongType
from click_repl.internal_commands import InternalCommandSystem, _exit_internal

internal_command_system = InternalCommandSystem()


def test_register_command_from_str():
    internal_command_system.register_command(
        target=_exit_internal,
        names="exit2",
        description="Temporary internal exit command",
    )

    with pytest.raises(ExitReplException):
        internal_command_system.execute(":exit2")


def test_register_command_using_decorator():
    @internal_command_system.register_command(
        names="exit3", description="Temporary internal exit command"
    )
    def _exit3():
        raise ExitReplException()

    with pytest.raises(ExitReplException):
        internal_command_system.execute(":exit3")


def test_register_duplicate_command():
    with pytest.raises(ValueError):

        @internal_command_system.register_command(
            names="exit3", description="Temporary internal exit command"
        )
        def duplicate_command():
            pass


@pytest.mark.parametrize(
    "test_input",
    [
        {"names": {"h": "help"}, "target": str},
        {"names": ["h", "help", "?"], "target": ""},
    ],
)
def test_register_function_usage_of_unknown_types_xfail(test_input):
    with pytest.raises(WrongType):
        internal_command_system.register_command(**test_input)
