import sys
import typing as t
from threading import local
from prompt_toolkit.formatted_text import HTML

import click

if t.TYPE_CHECKING:
    from typing import Any, NoReturn, Union, Optional, Tuple, Callable, Dict  # noqa: F401
    from .parser import ParsingState
    from .core import ReplContext  # noqa: F401


HAS_CLICK6 = click.__version__[0] == "6"
ISATTY = sys.stdin.isatty()

_locals = local()
_locals.ctx_stack = []
_locals._internal_commands = {}
_internal_commands: """Dict[
    str, Tuple[Callable[[], Any], Optional[str]]
]""" = _locals._internal_commands


def get_current_repl_ctx(
    silent: bool = False,
) -> "Union[ReplContext, None, NoReturn]":
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


def push_context(ctx: "ReplContext") -> None:
    """Pushes a new context to the current stack."""
    _locals.ctx_stack.append(ctx)


def pop_context() -> None:
    """Removes the top level from the stack."""
    _locals.ctx_stack.pop()


def toolbar_func() -> "Union[HTML, str]":
    state: "Optional[ParsingState]" = getattr(toolbar_func, "msg", None)
    if state is None:
        return ""

    if state.current_cmd is None:
        return HTML(
            f"<b>{type(state.current_group).__name__} {state.current_group.name}:"
            "</b> &lt;command&gt;"
        )

    out = f"<b>{state.current_cmd.name}: </b>"

    for param in state.current_cmd.params:
        if param in state.remaining_params:
            out += f'<style bg="grey">{param.name} </style>'

        elif param == getattr(state, "current_param", None):
            out += f"<b>{param.name} </b>"

        else:
            out += f"{param.name} "

    # print(f'{val = }')
    return HTML(out.strip())
