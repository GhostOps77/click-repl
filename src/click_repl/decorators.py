"""
Decorators to make using click-repl simpler and more similar to click.
"""

from __future__ import annotations

import typing as t
from functools import wraps
from typing import Any, Callable

import click
from typing_extensions import Concatenate, ParamSpec

from ._compat import MultiCommand
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
    Marks a callback as wanting to receive the current REPL context
    object as its first argument.

    Parameters
    ----------
    func
        The callback function to pass context as it's first parameter.

    Returns
    -------
    Callable[P,R]
        The decorated callback function that receives the current repl
        context object as its first argument.
    """

    @wraps(func)
    def decorator(*args: P.args, **kwargs: P.kwargs) -> R:
        return func(get_current_repl_ctx(), *args, **kwargs)

    return decorator


def register_repl(
    group: MultiCommand | None = None,
    *,
    name: str = "repl",
    remove_command_before_repl: bool = False,
) -> Callable[[MultiCommand], MultiCommand] | MultiCommand:
    """
    A decorator that registers :func:`~click_repl._repl.repl()` as sub-command
    named ``name`` within the ``group``.

    Parameters
    ----------
    group
        The click group (current CLI) object to which the repl command will be registered.

    name
        The name of the repl command in the given Group.

    remove_command_before_repl
        Flag that determines whether to remove the repl command from the group,
        before it's execution or not.

    Returns
    -------
    Callable[[Group],Group] | Group
        The same ``group`` or a callback that returns the same group, but
        the group has a repl command registered to it.

    Raises
    ------
    TypeError
        If the given group is not an instance of click Group.
    """

    def decorator(_group: MultiCommand) -> MultiCommand:
        nonlocal group

        if group is not None:
            _group = group

        if not isinstance(_group, MultiCommand):
            raise TypeError(
                "Expected 'group' to be a type of click.Group, "
                f"but got {type(_group).__name__}"
            )

        if name in _group.commands:
            raise ValueError(f"Command {name!r} already exists in Group {_group.name!r}")

        @wraps(repl)
        def _repl(ctx: click.Context, *args: Any, **kwargs: Any) -> None:
            if remove_command_before_repl:
                _group.commands.pop(name)

            repl(ctx, *args, **kwargs)
            _group.command(name=name)(click.pass_context(_repl))

        _group.command(name=name)(click.pass_context(_repl))

        return _group

    if group is None:
        return decorator
    return decorator(group)
