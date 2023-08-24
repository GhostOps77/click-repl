"""
`click_repl._globals`

Global variables, values, and functions that are accessed across
all the files in this module.
"""
import os
import sys
import typing as t
from threading import local

import click

if t.TYPE_CHECKING:
    from typing import Union, NoReturn
    from .core import ReplContext


# _NumberRangeBase class is defined in click v8.
# Therefore, this tuple is used to check for the
# range type ParamType objects.
_RANGE_TYPES = (click.IntRange, click.FloatRange)

# The only ParamType classes that have their
# get_metavar method's functionality defined.
_METAVAR_PARAMS = (click.Choice, click.DateTime)
HAS_CLICK8 = click.__version__[0] == "8"

_PATH_TYPES = (click.Path, click.File)

# If ISATTY is False, then we're not gonna run any code
# to generate auto-completions. Most of the code will be inactive
ISATTY = sys.stdin.isatty()

IS_WINDOWS = os.name == "nt"

# The method name for shell completion in click < v8 is "autocompletion".
# Therefore, this conditional statement is used to handle backwards compatibility
# for click < v8. If the click version is 8 or higher, the parameter is set to
# "shell_complete". Otherwise, it is set to "autocompletion".
AUTO_COMPLETION_PARAM = "shell_complete" if HAS_CLICK8 else "autocompletion"

# To store the ReplContext objects generated throughout the Runtime.
_locals = local()
_locals.ctx_stack = []


def get_current_repl_ctx(silent: bool = False) -> "Union[ReplContext, NoReturn, None]":
    """
    Returns the current click-repl Context, providing a way to access
    the context from anywhere in the code  This is a more implicit
    alternative to the `pass_context` decorator.

    Parameters
    ----------
    silent : bool
        If set to True the return value is None if no context
        is available. The default behavior is to raise a `RuntimeError`.

    Returns
    -------
    ctx : `ReplContext`
        ReplContext object if available.

    Raises
    ------
    RuntimeError
        If there's no Context object in the stack.
    """

    try:
        return _locals.ctx_stack[-1]  # type: ignore[no-any-return]
    except (AttributeError, IndexError):
        if not silent:
            raise RuntimeError("There is no active click-repl context.")

    return None


def _push_context(ctx: "ReplContext") -> None:
    """
    Pushes a new repl context to the current stack.

    Parameters
    ----------
    ctx : `ReplContext`
        ReplContext object that should be added to the repl context stack.
    """
    _locals.ctx_stack.append(ctx)


def _pop_context() -> None:
    """Removes the top level repl context from the stack."""
    _locals.ctx_stack.pop()
