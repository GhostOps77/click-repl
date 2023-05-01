import sys
import typing as t
from threading import local

import click

if t.TYPE_CHECKING:
    from typing import NoReturn, Union, List, Any, Iterable  # noqa: F401
    from click import MultiCommand  # noqa: F401
    from .core import ClickReplContext  # noqa: F401


HAS_CLICK6 = click.__version__[0] == "6"
ISATTY = sys.stdin.isatty()
_locals = local()
_locals.ctx_stack = []
_locals.cli_args_stack = {}


def get_current_repl_ctx(
    silent: bool = False,
) -> "Union[ClickReplContext, None, NoReturn]":
    """Returns the current click-repl context.  This can be used as a way to
    access the current context object from anywhere.  This is a more implicit
    alternative to the :func:`pass_context` decorator.

    Keyword arguments:
    ---
    :param:`silent` - if set to `True` the return value is `None` if no context
        is available.  The default behavior is to raise a :exc:`RuntimeError`.

    Return: :class:`ClickReplContext` if available
    """

    try:
        return _locals.ctx_stack[-1]  # type: ignore[no-any-return]
    except (AttributeError, IndexError):
        if not silent:
            raise RuntimeError("There is no active click-repl context.")

    return None


def push_context(ctx: "ClickReplContext") -> None:
    """Pushes a new context to the current stack."""
    _locals.ctx_stack.append(ctx)


def pop_context() -> None:
    """Removes the top level from the stack."""
    _locals.ctx_stack.pop()


def _get_cli_argv(
    group: "MultiCommand",
    default: "Any" = None,
) -> "Union[List[Any], NoReturn]":
    """Returns args for the current click-repl Group CLI.

    Keyword arguments:
    ---
    :param:`group` - The Group object for the respective group args
    :param:`default` - Default sentinel value, the return value is
        whatever available in that parameter if no args were
        available and if its not None. The default behavior is to
        raise a :exc:`RuntimeError`.

    Return: List of string of the respective group args if available
    """

    return _locals.cli_args_stack.get(group, default)  # type: ignore[no-any-return]


def _push_args(group: "MultiCommand", args: "Iterable[str]" = []) -> None:
    """Pushes a new context to the current stack."""
    _locals.cli_args_stack[group] = args
