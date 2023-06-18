import pytest

from click_repl._internal_cmds import _execute_internal_and_sys_cmds


@pytest.mark.parametrize(
    "test_input, expected",
    [("!echo hi", "hi\n"), ("!echo hi hi", "hi hi\n"), ("!", "")],
)
def test_system_commands(capfd, test_input, expected):
    _execute_internal_and_sys_cmds(test_input, None, "!")

    captured_stdout = capfd.readouterr().out.replace("\r\n", "\n")
    assert captured_stdout == expected


@pytest.mark.parametrize(
    "test_input",
    ["!echo hi", "!echo hi hi", "!"],
)
def test_no_system_commands(capfd, test_input):
    _execute_internal_and_sys_cmds(test_input, None, None)

    captured_stdout = capfd.readouterr().out.replace("\r\n", "\n")
    assert captured_stdout == ""
