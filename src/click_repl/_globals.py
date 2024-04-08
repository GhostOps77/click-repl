"""
Global variables, values, and functions that are accessed across
all the files in this module.
"""

from __future__ import annotations

import os
import sys
from threading import local
from typing import TYPE_CHECKING, NoReturn

from ._types import CompletionDisplayStyleDict, CompletionStyleDict

if sys.version_info < (3, 8):
    from importlib_metadata import version
else:
    from importlib.metadata import version

if TYPE_CHECKING:
    from .core import ReplContext


CLICK_VERSION: tuple[int, int, int] = tuple(  # type:ignore[assignment]
    int(i) for i in version("click").split(".")
)

HAS_CLICK_GE_8 = CLICK_VERSION[0] >= 8
HAS_CLICK_GE_8_2 = CLICK_VERSION >= (8, 2)

IS_WINDOWS = os.name == "nt"

ISATTY = sys.stdin.isatty()
"""If it is ``False``, then we're not gonna run any code
   to generate auto-completions. Most of the code will be inactive"""

CLICK_REPL_DEV_ENV = os.getenv("CLICK_REPL_DEV_ENV", None) is not None
"""click-repl Environmental flag. Enable it only for debugging."""

DEFAULT_COMPLETION_STYLE_CONFIG = {
    # For Boolean type.
    "autocompletion-menu.parameter.type.bool.totrue": "fg:#44e80e",
    "autocompletion-menu.parameter.type.bool.tofalse": "fg:red",
}
"""Default token style configuration for :class:`~click_repl.completer.ClickCompleter`"""


DEFAULT_COMPLETION_STYLE_CONFIG.update(
    dict.fromkeys(
        [
            # Command
            "autocompletion-menu.command.name",
            "autocompletion-menu.group.name",
            # Parameter types.
            "autocompletion-menu.parameter.argument.name",
            "autocompletion-menu.parameter.option.name",
            "autocompletion-menu.parameter.option.name.separator",
            # For Path types.
            "autocompletion-menu.parameter.type.path.directory",
            "autocompletion-menu.parameter.type.path.file",
            "autocompletion-menu.parameter.type.path",
            # For Boolean type.
            "autocompletion-menu.parameter.type.bool",
            # For Range types.
            "autocompletion-menu.parameter.type.range.integer",
            "autocompletion-menu.parameter.type.range.float",
            # Internal Command
            "autocompletion-menu.internalcommand.name",
            # Default values text
            "autocompletion-menu.parameter.default.text",
            "autocompletion-menu.parameter.default.value",
            # Flag values text
            "autocompletion-menu.parameter.flag-value.text",
            "autocompletion-menu.parameter.flag-value.value",
            # Misc.
            "autocompletion-menu.symbols.bracket",
            "autocompletion-menu.space",
        ],
        "",
    )
)

DEFAULT_COMPLETION_STYLE_DICT: CompletionStyleDict = {
    "internal-command": CompletionDisplayStyleDict(),
    "command": CompletionDisplayStyleDict(),
    "group": CompletionDisplayStyleDict(),
    "argument": CompletionDisplayStyleDict(),
    "option": CompletionDisplayStyleDict(),
}
"""Default display text configuration for :class:`~prompt_toolkit.completion.Completion`"""

DEFAULT_BOTTOMBAR_STYLE_CONFIG = {
    # Group
    "bottom-bar.group.name": "bold",
    "bottom-bar.group.type": "bold",
    # Command
    "bottom-bar.command.name": "bold",
    "bottom-bar.command.type": "bold",
    # Misc. for Parameter.
    "bottom-bar.parameter.nargs.counter": "fg:green",
    # Base Paramter
    "bottom-bar.parameter.inuse": "bold underline",
    "bottom-bar.parameter.used": "strike",
    # ParamType tokens especially for Tuple type.
    "bottom-bar.parameter.type.inuse": "bold underline",
    "bottom-bar.parameter.type.used": "strike",
    # For displaying Exceptions
    "bottom-bar.error": "fg:white bg:red",
    "bottom-bar.error.exception-class-name": "bold",
    "bottom-bar.error.message": "bold",
}
"""Default token style configuration for :class:`~click_repl.bottom_bar.BottomBar`"""

DEFAULT_BOTTOMBAR_STYLE_CONFIG.update(
    dict.fromkeys(
        [
            # Group
            "bottom-bar.group.metavar",
            # Command
            "bottom-bar.command.metavar",
            "bottom-bar.parameter.type.name",
            # Primitive datatypes.
            "bottom-bar.parameter.type.string",
            "bottom-bar.parameter.type.integer",
            "bottom-bar.parameter.type.float",
            # Range types.
            "bottom-bar.parameter.type.range.integer",
            "bottom-bar.parameter.type.range.float",
            "bottom-bar.parameter.type.range.descriptor",
            # Path types.
            "bottom-bar.parameter.type.path",
            "bottom-bar.parameter.type.file",
            # For Boolean type options.
            "bottom-bar.parameter.type.bool",
            # Other arbitrary types.
            "bottom-bar.parameter.type.composite",
            "bottom-bar.parameter.type.choice",
            "bottom-bar.parameter.type.datetime",
            "bottom-bar.parameter.type.uuid",
            "bottom-bar.parameter.type.unprocessed",
            # Misc.
            "bottom-bar.space",
            "bottom-bar.symbol",
            "bottom-bar.ellipsis",
            "bottom-bar.symbol.bracket",
            # Misc. for Parameter.
            "bottom-bar.parameter.nargs",
            "bottom-bar.parameter.argument.name",
            "bottom-bar.parameter.option.name",
            # Base Paramter
            "bottom-bar.paramter.name",
            "bottom-bar.parameter.type",
            "bottom-bar.parameter.unused",
            # ParamType tokens especially for Tuple type.
            "bottom-bar.parameter.type.unused",
        ],
        "",
    )
)

DEFAULT_PROMPTSESSION_STYLE_CONFIG = {
    "bottom-toolbar": "fg:lightblue bg:default noreverse"
}
"""Default token style configuration for :class:`~prompt_toolkit.PromptSession`"""

DEFAULT_PROMPTSESSION_STYLE_CONFIG.update(DEFAULT_BOTTOMBAR_STYLE_CONFIG)
DEFAULT_PROMPTSESSION_STYLE_CONFIG.update(DEFAULT_COMPLETION_STYLE_CONFIG)


# To store the ReplContext objects generated throughout the Runtime.
_locals = local()
_ctx_stack: list[ReplContext] = []
_locals.ctx_stack = _ctx_stack


def get_current_repl_ctx(silent: bool = False) -> ReplContext | NoReturn | None:
    """
    Returns the current click-repl context, providing a way to access
    the context from anywhere in the code  This is a more implicit
    alternative to the :func:`~click.decorators.pass_context` decorator.

    Parameters
    ----------
    silent
        If set to ``True``, the return value is ``None`` if no context
        is available. The default behavior is to raise a :exc:`~RuntimeError`.

    Returns
    -------
    :class:`~click_repl.core.ReplContext` | None
        ``ReplContext`` object, if available.

    Raises
    ------
    RuntimeError
        If there's no context object in the stack and ``silent`` is ``False``.
    """

    try:
        return _ctx_stack[-1]
    except (AttributeError, IndexError):
        if not silent:
            raise RuntimeError("There is no active click-repl context.")

    return None


def _push_context(ctx: ReplContext) -> None:
    """
    Pushes a new repl context to the current stack.

    Parameters
    ----------
    ctx
        :class:`~click_repl.core.ReplContext` object that should be
        added to the repl context stack.
    """
    _locals.ctx_stack.append(ctx)


def _pop_context() -> None:
    """Removes the top level repl context from the stack."""
    _locals.ctx_stack.pop()
