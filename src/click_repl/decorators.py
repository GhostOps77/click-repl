"""
`click_repl.decorators`

Decorators to make using click-repl simpler and more similar to click.
"""

from __future__ import annotations

import typing as t
from functools import wraps
from typing import Any
from typing import Callable

import click
from click import Group
from typing_extensions import Concatenate
from typing_extensions import ParamSpec

from ._globals import get_current_repl_ctx
from ._repl import repl
from .core import ReplContext

P = ParamSpec("P")
R = t.TypeVar("R")
F = t.TypeVar("F", bound=Callable[..., Any])


__all__ = ["pass_context"]


def pass_context(
    func: Callable[Concatenate[ReplContext | None, P], R],
) -> Callable[P, R]:
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
    def decorator(*args: P.args, **kwargs: P.kwargs) -> R:
        return func(get_current_repl_ctx(), *args, **kwargs)

    return decorator


def register_repl(
    group: Group | None = None,
    *,
    name: str = "repl",
    remove_cmd_before_repl: bool = False,
) -> Callable[[Group], Group] | Group:
    """
    A decorator that registers `repl()` as sub-command named `name`
    within the `group`.

    Parameters
    ----------
    group : `click.Group`
        The click group (current CLI) object to which the repl command will be registered.

    name : str
        The name of the repl command in the given Group.

    remove_cmd_before_repl : bool
        Flag that determines whether to remove the repl command from the group,
        before it's execution or not.

    Raises
    ------
    TypeError
        If the given group is not an instance of click Group.
    """

    def decorator(_group: Group) -> Group:
        nonlocal group

        if group is not None:
            _group = group

        if not isinstance(_group, Group):
            raise TypeError(
                "Expected 'group' to be a type of click.Group, "
                f"but got {type(_group).__name__}"
            )

        if name in _group.commands:
            raise ValueError(f"Command {name!r} already exists in Group {_group.name!r}")

        @wraps(repl)
        def _repl(ctx: click.Context, *args: Any, **kwargs: Any) -> None:
            if remove_cmd_before_repl:
                _group.commands.pop(name)

            repl(ctx, *args, **kwargs)
            _group.command(name=name)(click.pass_context(_repl))

        _group.command(name=name)(click.pass_context(_repl))

        return _group

    if group is None:
        return decorator
    return decorator(group)
