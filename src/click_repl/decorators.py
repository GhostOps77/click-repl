"""
click_repl.decorators

Decorators to make using click_shell simpler and more similar to click.
"""
import typing as t
from functools import wraps

from ._globals import get_current_repl_ctx
from .core import ReplContext

if t.TYPE_CHECKING:
    from typing import Any, Callable, Optional

    from typing_extensions import Concatenate, ParamSpec

    P = ParamSpec("P")
    R = t.TypeVar("R")
    F = t.TypeVar("F", bound=Callable[..., Any])


__all__ = ["pass_context"]

# def repl_cli(
#     func: "Union[Callable[..., Any], str, None]" = None, **attrs: "Any"
# ) -> "Callable[[F], ReplCli]":
#     """Creates a new :class:`ReplCli` with a function as callback.  This
#     works otherwise the same as :func:`command` just that the `cls`
#     parameter is set to :class:`ReplCli`.
#     """

#     def decorator(f: "Union[Callable[..., Any], str, None]") -> ReplCli:
#         attrs.setdefault("cls", ReplCli)
#         return cast(ReplCli, click.group(f, **attrs))

#     if func is not None:
#         return decorator(func)

#     return decorator


def pass_context(
    func: "Callable[Concatenate[Optional[ReplContext], P], R]",
) -> "Callable[P, R]":
    """Marks a callback as wanting to receive the current REPL context
    object as first argument.
    """

    @wraps(func)
    def decorator(*args: "P.args", **kwargs: "P.kwargs") -> "R":
        return func(get_current_repl_ctx(), *args, **kwargs)

    return decorator
