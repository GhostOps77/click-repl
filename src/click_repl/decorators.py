"""
click_repl.decorators

Decorators to make using click_shell simpler and more similar to click.
"""

import click
import typing as t
from typing import cast
from functools import wraps

from .core import ReplContext, ReplCli

from ._globals import get_current_repl_ctx

if t.TYPE_CHECKING:
    from typing import Callable, Optional, Any, Union

    P = t.ParamSpec("P")
    R = t.TypeVar("R")
    F = t.TypeVar("F", bound=Callable[..., Any])


def repl_cli(
    func: "Union[Callable[..., Any], str, None]" = None, *args, **attrs: "Any"
) -> "Callable[[F], ReplCli]":
    """Creates a new :class:`ReplCli` with a function as callback.  This
    works otherwise the same as :func:`command` just that the `cls`
    parameter is set to :class:`ReplCli`.
    """

    def decorator(f: "Union[Callable[..., Any], str, None]") -> ReplCli:
        attrs.setdefault("cls", ReplCli)
        return cast(ReplCli, click.group(f, *args, **attrs))

    if func is not None:
        return decorator(func)

    return decorator


def pass_context(
    func: "Callable[t.Concatenate[Optional[ReplContext], P], R]",
) -> "Callable[P, R]":
    """Marks a callback as wanting to receive the current REPL context
    object as first argument.
    """

    @wraps(func)
    def decorator(*args: "P.args", **kwargs: "P.kwargs") -> "R":
        return func(get_current_repl_ctx(), *args, **kwargs)

    return decorator
