import pytest

from click_repl._internal_cmds import _exit_internal, InternalCommandSystem


internal_command_system = InternalCommandSystem(":", "!")


def test_register_cmd_from_str():
    internal_command_system.register_command(
        _exit_internal, "exit2", "Temporary internal exit command"
    )


@pytest.mark.parametrize(
    "test_input",
    [
        ({"h": "help"}, str),
        (["h", "help", "?"], str()),
    ],
)
def test_register_func_xfails(test_input):
    with pytest.raises(ValueError):
        internal_command_system.register_command(*test_input)
