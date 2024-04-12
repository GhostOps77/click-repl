"""
Utilities to facilitate the functionality of the module.
"""

from __future__ import annotations

from difflib import get_close_matches
from typing import Generator

import click
from click import Command, Context, Parameter

from ._compat import MultiCommand
from .exceptions import ArgumentPositionError


def _is_help_option(param: click.Option) -> bool:
    """
    Checks whether the given :class:`~click.Option` object is a help option or not.

    Parameters
    ----------
    param
        A click option object.

    Returns
    -------
    bool
        If ``True``, The given :class:`~click.Option` object is a help option.
        else, ``False``.
    """
    has_help_msg_as_help_text = bool(
        get_close_matches(param.help or "", ["Show this message and exit."], cutoff=0.5)
    )

    return (
        param.is_flag
        and not param.expose_value
        and "--help" in param.opts
        and param.is_eager
        and has_help_msg_as_help_text
    )


def is_param_value_incomplete(
    ctx: Context, param: Parameter, check_if_tuple_has_none: bool = True
) -> bool:
    """
    Checks whether the given name of a parameter doesn't recieve it's values completely.

    Parameters
    ----------
    ctx
        :class:`~click.Context` object corresponding to the parameter.

    param
        :class:`~click.Parameter` object to check it's value after parsing it.

    check_if_tuple_has_none
        Flag that checks whether the given parameter stores multiple
        values in a tuple, and the tuple has `None` in it.

    Returns
    -------
    bool
        Whether the given parameter has recieved all of
        it's necessary values from the prompt or not.
    """
    if param.name is None:
        return False

    if param.nargs == -1 or param.multiple:
        return True

    value = ctx.params.get(param.name, None)

    check_if_tuple_has_none = (
        param.multiple or param.nargs != 1
    ) and check_if_tuple_has_none

    return (
        value in (None, ())
        or check_if_tuple_has_none
        and isinstance(value, tuple)
        and None in value
    )

    # return value in (None, ()) or (
    #     check_if_tuple_has_none and isinstance(value, tuple) and None in value
    # )


def iterate_command_params(command: Command) -> Generator[Parameter, None, None]:
    """
    This function is to iterate over parameters of a command in an order such that
    the parameters with `nargs=-1` will be yielded at the very end.

    Parameters
    ----------
    command
        The :class:`~click.Command` object to iterate over it's parameters.

    Yields
    ------
    click.Parameter
        The parameters of the given command.

    Raises
    ------
    ArgumentPositionError
        If the :class:`~click.Argument` object with `nargs=-1` is not
        defined at the very end among other parameters.
    """

    nargs_minus_one_param: tuple[click.Argument, int] | None = None

    for idx, param in enumerate(command.params):
        is_param_argument = isinstance(param, click.Argument)

        if is_param_argument and param.nargs == -1:
            nargs_minus_one_param = (param, idx)  # type: ignore[assignment]

        elif nargs_minus_one_param is not None and is_param_argument:
            minus_one_param, minus_one_param_idx = nargs_minus_one_param
            raise ArgumentPositionError(command, minus_one_param, minus_one_param_idx)

        else:
            yield param

    if nargs_minus_one_param:
        yield nargs_minus_one_param[0]

    return


def _get_group_ctx(ctx: Context) -> Context:
    """
    Checks and returns the appropriate :class:`~click.Context` object to
    start repl on it.

    If there's a parent context object and its command type is :class:`~click.Group`,
    we return its parent context object. A parent context object should be
    available most of the time. If not, then we return the original context object.

    Parameters
    ----------
    ctx
        The :class:`~click.Context` object to check and start repl on it.

    Returns
    -------
    click.Context
        The :class:`~click.Context` object that should be used to start repl on it.
    """
    if ctx.parent is not None and not isinstance(ctx.command, MultiCommand):
        ctx = ctx.parent

    ctx.protected_args = []
    return ctx
