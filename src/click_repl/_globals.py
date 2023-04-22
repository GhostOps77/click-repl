from threading import local
import typing as t

if t.TYPE_CHECKING:
    from .core import ClickReplContext  # noqa: F401
    from typing import Union, NoReturn, Any  # noqa: F401


_locals = local()
_locals.stack = []


def text_type(text):
    # type: (Any) -> str
    # fmt: off
    return u"{}".format(text)
    # fmt: on


def get_current_click_repl_context(silent=False):
    # type: (bool) -> Union[ClickReplContext, None, NoReturn]

    try:
        return _locals.stack[-1]  # type: ignore[no-any-return, syntax]
    except (AttributeError, IndexError):
        if not silent:
            raise RuntimeError("There is no active click-repl context.")

    return None


def push_context(ctx):
    # type: (ClickReplContext) -> None
    """Pushes a new context to the current stack."""
    _locals.stack.append(ctx)


def pop_context():
    # type: () -> None
    """Removes the top level from the stack."""
    _locals.stack.pop()
