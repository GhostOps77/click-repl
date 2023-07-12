"""
`click_repl._globals`

Global variables, values, and functions that are accessed across
all the files in this module.
"""
import sys
import typing as t
from threading import local

import click

if t.TYPE_CHECKING:
    from .core import ReplContext


# Float Range is introduced after IntRange, in click v7
# Also, _NumberRangeBase abstract class is introduced in click v8
# Therefore, we're gonna use this tuple throughout the code to
# type-check whether the param types are range types, for
# backwards-compatibility for both click v6 and v7
try:
    from click import FloatRange

    _RANGE_TYPES = (click.IntRange, FloatRange)
except ImportError:
    _RANGE_TYPES = (click.IntRange,)  # type: ignore[assignment]


HAS_CLICK6 = click.__version__[0] == "6"
HAS_CLICK8 = click.__version__[0] == "8"

# If ISATTY is False, then we're not gonna run any code
# to generate auto-completions. Most of the code will be inactive
ISATTY = sys.stdin.isatty()


# To store the ReplContext objects generated throughout the Runtime.
_locals = local()
_locals.ctx_stack = []


def get_current_repl_ctx(
    silent: bool = False,
) -> "t.Union[ReplContext, t.NoReturn, None]":
    """
    Returns the current click-repl Context, providing a way to access
    the context from anywhere in the code  This is a more implicit
    alternative to the `pass_context` decorator.

    Parameters
    ----------
    silent :  bool
        If set to True the return value is None if no context
        is available. The default behavior is to raise a `RuntimeError`.

    Returns
    -------
    ctx : click_repl.core.ReplContext
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


def push_context(ctx: "ReplContext") -> None:
    """
    Pushes a new repl context to the current stack.

    Parameters
    ----------
    ctx : click_repl.core.ReplContext
        ReplContext object that should be added to the repl context stack.
    """
    _locals.ctx_stack.append(ctx)


def pop_context() -> None:
    """Removes the top level repl context from the stack."""
    _locals.ctx_stack.pop()
