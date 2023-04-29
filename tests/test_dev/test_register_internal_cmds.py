from click_repl._internal_cmds import _register_internal_command, _help_internal
import pytest


def test_register_cmd_from_str():
    _register_internal_command(
        "help2", _help_internal, "temporary internal help command"
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
        _register_internal_command(*test_input)
