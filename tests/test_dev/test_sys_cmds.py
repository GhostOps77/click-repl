import pytest

from click_repl._internal_cmds import InternalCommandSystem


sys_cmds_only_obj = InternalCommandSystem(None, "!")


@pytest.mark.parametrize(
    "test_input, expected",
    [("!echo hi", "hi\n"), ("!echo hi hi", "hi hi\n"), ("!", "")],
)
def test_system_commands(capfd, test_input, expected):
    sys_cmds_only_obj.execute(test_input)

    captured_stdout = capfd.readouterr().out.replace("\r\n", "\n")
    assert captured_stdout == expected


no_sys_cmds_obj = InternalCommandSystem(None, None)


@pytest.mark.parametrize(
    "test_input",
    ["!echo hi", "!echo hi hi", "!"],
)
def test_no_system_commands(capfd, test_input):
    no_sys_cmds_obj.execute(test_input)

    captured_stdout = capfd.readouterr().out.replace("\r\n", "\n")
    assert captured_stdout == ""
