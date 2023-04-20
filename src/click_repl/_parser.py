import typing as t
import click
# from functools import lru_cache
from shlex import shlex


if t.TYPE_CHECKING:
    from typing import List, Tuple  # noqa: F401
    from click import Context, Command  # noqa: F401


# Handle backwards compatibility for click<=8
try:
    import click.shell_completion

    HAS_CLICK_V8 = True
    AUTO_COMPLETION_PARAM = "shell_complete"
except (ImportError, ModuleNotFoundError):
    import click._bashcomplete  # type: ignore[import]

    HAS_CLICK_V8 = False
    AUTO_COMPLETION_PARAM = "autocompletion"


def split_arg_string(string, posix=True):
    # type: (str, bool) -> "List[str]"
    """Split an argument string as with :func:`shlex.split`, but don't
    fail if the string is incomplete. Ignores a missing closing quote or
    incomplete escape sequence and uses the partial token as-is.
    .. code-block:: python
        split_arg_string("example 'my file")
        ["example", "my file"]
        split_arg_string("example my\\")
        ["example", "my"]
    :param string: String to split.
    """

    lex = shlex(string, posix=posix, punctuation_chars=True)
    lex.whitespace_split = True
    lex.commenters = ""
    out = []  # type: List[str]

    try:
        out.extend(lex)
    except ValueError:
        # Raised when end-of-string is reached in an invalid state. Use
        # the partial token as-is. The quote or escape character is in
        # lex.state, not lex.token.
        out.append(lex.token)

    return out


# @lru_cache(maxsize=3)
def get_ctx_for_args(cmd, parsed_args, cli_args):
    # type: (Command, List[str], List[str]) -> Tuple[Command, Context]

    # Resolve context based on click version
    if HAS_CLICK_V8:
        parsed_ctx = click.shell_completion._resolve_context(
            cmd, {}, "", cli_args + parsed_args
        )
    else:
        parsed_ctx = click._bashcomplete.resolve_ctx(
            cmd, "", cli_args + parsed_args
        )

    ctx_command = parsed_ctx.command
    # opt_parser = OptionsParser(ctx_command, parsed_ctx)

    return ctx_command, parsed_ctx
