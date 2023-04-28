from threading import local
import click
import typing as t

if t.TYPE_CHECKING:
    from .core import ClickReplContext  # noqa: F401
    from typing import Union, NoReturn  # noqa: F401


HAS_CLICK6 = click.__version__[0] == "6"
_locals = local()
_locals.stack = []


def get_current_repl_ctx(
    silent: bool = False
) -> 'Union[ClickReplContext, None, NoReturn]':
    try:
        return _locals.stack[-1]  # type: ignore[no-any-return, syntax]
    except (AttributeError, IndexError):
        if not silent:
            raise RuntimeError("There is no active click-repl context.")

    return None


def push_context(ctx: 'ClickReplContext') -> None:
    """Pushes a new context to the current stack."""
    _locals.stack.append(ctx)


def pop_context() -> None:
    """Removes the top level from the stack."""
    _locals.stack.pop()
