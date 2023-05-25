"""
click_repl.decorators

Decorators to make using click_shell simpler and more similar to click.
"""

import click
import typing as t
from typing import cast
from functools import wraps

from .core import ClickReplContext, ReplCli

from ._globals import get_current_repl_ctx

if t.TYPE_CHECKING:
    from typing import Callable, Optional, Any, Union

    P = t.ParamSpec("P")
    R = t.TypeVar("R")
    F = t.TypeVar("F", bound=Callable[..., Any])


def repl_cli(
    name: "Union[Callable[..., Any], str]", **attrs: "Any"
) -> "Callable[[F], ReplCli]":
    """Creates a new :class:`ReplCli` with a function as callback.  This
    works otherwise the same as :func:`command` just that the `cls`
    parameter is set to :class:`ReplCli`.
    """

    attrs.setdefault("cls", ReplCli)
    return cast(ReplCli, click.command(name, **attrs))


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
