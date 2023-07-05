"""
click_repl.decorators

Decorators to make using click_repl simpler and more similar to click.
"""
import typing as t
from functools import wraps

from ._globals import get_current_repl_ctx

if t.TYPE_CHECKING:
    from typing import Any, Callable
    from .core import ReplContext

    from typing_extensions import Concatenate, ParamSpec

    P = ParamSpec("P")
    R = t.TypeVar("R")
    F = t.TypeVar("F", bound=Callable[..., Any])


__all__ = ["pass_context"]


# def repl_cli(
#     func: "Union[Callable[..., Any], str, None]" = None, **attrs: "Any"
# ) -> "Callable[[F], ReplCli]":
#     """Creates a new `ReplCli` with a function as callback.  This
#     works otherwise the same as `command` just that the `cls`
#     parameter is set to `ReplCli`.
#     """

#     def decorator(f: "Union[Callable[..., Any], str, None]") -> ReplCli:
#         attrs.setdefault("cls", ReplCli)
#         return cast(ReplCli, click.group(f, **attrs))

#     if func is not None:
#         return decorator(func)

#     return decorator


def pass_context(
    func: "Callable[Concatenate[t.Optional[ReplContext], P], R]",
) -> "Callable[P, R]":
    """
    A Decorator that marks a callback as wanting to receive
    the current REPL context object as its first argument.

    Parameters
    ----------
    func : Any function.
        The callback function to decorate.

    Returns
    -------
    The decorated callback function that recieves the current repl
    context object as its first argument.
    """

    @wraps(func)
    def decorator(*args: "P.args", **kwargs: "P.kwargs") -> "R":
        return func(get_current_repl_ctx(), *args, **kwargs)

    return decorator
