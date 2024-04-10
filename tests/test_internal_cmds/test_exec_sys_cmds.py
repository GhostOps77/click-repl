from __future__ import annotations

import pytest

from click_repl._internal_command import InternalCommandSystem
from click_repl.exceptions import PrefixNotFound

sys_commands_only_obj = InternalCommandSystem(None)


@pytest.mark.parametrize(
    "test_input, expected",
    [
        ("!echo hi", "hi\n"),
        ("!echo hi hi", "hi hi\n"),
    ],
)
def test_system_commands(capfd, test_input, expected):
    sys_commands_only_obj.execute(test_input)

    captured_stdout = capfd.readouterr().out.replace("\r\n", "\n")
    assert captured_stdout == expected


no_sys_commands_obj = InternalCommandSystem(None, None)


@pytest.mark.parametrize(
    "test_input",
    ["!echo hi", "!echo hi hi", "!"],
)
def test_no_system_commands(test_input):
    with pytest.raises(PrefixNotFound):
        no_sys_commands_obj.execute(test_input)
