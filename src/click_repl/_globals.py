import sys
import typing as t
from threading import local

import click

if t.TYPE_CHECKING:
    from typing import NoReturn, Union  # noqa: F401

    from .core import ReplContext  # noqa: F401


# Float Range is introduced after IntRange, in click v7
try:
    from click import FloatRange

    _RANGE_TYPES = (click.IntRange, FloatRange)
except ImportError:
    _RANGE_TYPES = (click.IntRange,)  # type: ignore[assignment]


HAS_CLICK6 = click.__version__[0] == "6"
ISATTY = sys.stdin.isatty()

_locals = local()
_locals.ctx_stack = []


def get_current_repl_ctx(
    silent: bool = False,
) -> "Union[ReplContext, None, NoReturn]":
    """Returns the current click-repl context.  This can be used as a way to
    access the current context object from anywhere.  This is a more implicit
    alternative to the :func:`pass_context` decorator.

    Keyword arguments:
    ---
    :param:`silent` - if set to `True` the return value is `None` if no context
        is available.  The default behavior is to raise a :exc:`RuntimeError`.

    Return: :class:`ClickReplContext` if available
    """

    try:
        return _locals.ctx_stack[-1]  # type: ignore[no-any-return]
    except (AttributeError, IndexError):
        if not silent:
            raise RuntimeError("There is no active click-repl context.")

    return None


def push_context(ctx: "ReplContext") -> None:
    """Pushes a new context to the current stack."""
    _locals.ctx_stack.append(ctx)


def pop_context() -> None:
    """Removes the top level from the stack."""
    _locals.ctx_stack.pop()
