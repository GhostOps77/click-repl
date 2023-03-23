# from click_repl import CommandLineParserError
# from click_repl.utils import _execute_internal_and_sys_cmds
# import pytest


# @pytest.mark.parametrize(
#     "test_input",
#     [
#         '!echo "hi',
#         "!echo 'hi",
#     ],
# )
# def test_shlex_errors(test_input):
#     with pytest.raises(CommandLineParserError):
#         _execute_internal_and_sys_cmds(
#             test_input, allow_internal_commands=False, allow_system_commands=False
#         )
