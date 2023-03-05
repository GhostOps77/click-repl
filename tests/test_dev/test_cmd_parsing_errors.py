import pytest
from click_repl import CommandLineParserError
from click_repl.utils import _execute_command


@pytest.mark.parametrize(
    "test_input",
    [
        '!echo "hi',
        "!echo 'hi",
    ],
)
def test_shlex_errors(test_input):
    with pytest.raises(CommandLineParserError):
        _execute_command(
            test_input, allow_internal_commands=False, allow_system_commands=False
        )
