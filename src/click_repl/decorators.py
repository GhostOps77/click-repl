"""
`click_repl.decorators`

Decorators to make using click-repl simpler and more similar to click.
"""
import typing as t
from functools import wraps

import click

from ._globals import get_current_repl_ctx
from ._repl import repl

if t.TYPE_CHECKING:
    from typing import Any, Callable, Optional, Union

    from typing_extensions import Concatenate, ParamSpec
    from click import Group

    from .core import ReplContext

    P = ParamSpec("P")
    R = t.TypeVar("R")
    F = t.TypeVar("F", bound=Callable[..., Any])


__all__ = ["pass_context"]


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


def register_repl(
    group: "Optional[Group]" = None, *, name: str = "repl"
) -> "Union[Callable[[Group], Group], Group]":
    """
    A decorator that registers `repl()` as sub-command named `name`
    within the `group`.

    Parameters
    ----------
    group : `click.Group`
        The click group (current CLI) object to which the repl command will be registered.

    name : str
        The name of the repl command in the given Group.

    Raises
    ------
    TypeError
        If the given group is not an instance of click Group.
    """

    def decorator(_group: "click.Group") -> "click.Group":
        nonlocal group

        if group is None:
            group = _group

        if not isinstance(group, click.Group):
            raise TypeError(
                "Expected 'group' to be a type of click.Group, "
                f"but got {type(group).__name__}"
            )

        group.command(name=name)(click.pass_context(repl))

        return group

    if group is None:
        return decorator
    return decorator(group)
