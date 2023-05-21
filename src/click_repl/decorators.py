import typing as t
from functools import wraps

from ._globals import get_current_repl_ctx

if t.TYPE_CHECKING:
    from typing import Callable, Optional

    from .core import ClickReplContext

    P = t.ParamSpec("P")
    R = t.TypeVar("R")


def pass_context(
    func: "Callable[t.Concatenate[Optional[ClickReplContext], P], R]",
) -> "Callable[P, R]":
    """Marks a callback as wanting to receive the current REPL context
    object as first argument.
    """

    @wraps(func)
    def decorator(*args: "P.args", **kwargs: "P.kwargs") -> "R":
        return func(get_current_repl_ctx(), *args, **kwargs)

    return decorator
