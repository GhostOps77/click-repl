"""
`click_repl._globals`

Global variables, values, and functions that are accessed across
all the files in this module.
"""
from __future__ import annotations

import os
import sys
import typing as t
from threading import local
from typing import NoReturn

import click
from prompt_toolkit.formatted_text import StyleAndTextTuples as StyleAndTextTuples

if t.TYPE_CHECKING:
    from .core import ReplContext


# TBottomBar = Token.BottomBar
# TAutocompletionMenu = Token.AutocompletionMenu


DEFAULT_COMPLETION_STYLE_CONFIG = {
    # Command
    "autocompletion-menu.command.name": "",
    "autocompletion-menu.multicommand.name": "",
    "autocompletion-menu.multicommand.group.name": "",
    # Parameter types.
    "autocompletion-menu.parameter.argument.name": "",
    "autocompletion-menu.parameter.option.name": "",
    "autocompletion-menu.parameter.option.name.separator": "",
    # For Path types.
    "autocompletion-menu.parameter.type.path.directory": "",
    "autocompletion-menu.parameter.type.path.file": "",
    "autocompletion-menu.parameter.type.path": "",
    # For Boolean type.
    "autocompletion-menu.parameter.type.bool.totrue": "fg:#44e80e",
    "autocompletion-menu.parameter.type.bool.tofalse": "fg:red",
    "autocompletion-menu.parameter.type.bool": "",
    # For Range types.
    "autocompletion-menu.parameter.type.range.integer": "",
    "autocompletion-menu.parameter.type.range.float": "",
    # Internal Command
    "autocompletion-menu.internalcommand.name": "",
    # Default values text
    "autocompletion-menu.parameter.default.text": "",
    "autocompletion-menu.parameter.default.value": "",
    # Flag values text
    "autocompletion-menu.parameter.flag-value.text": "",
    "autocompletion-menu.parameter.flag-value.value": "",
    # Misc.
    "autocompletion-menu.symbols.bracket": "",
    "autocompletion-menu.space": "",
}


DEFAULT_BOTTOMBAR_STYLE_CONFIG = {
    # MultiCommand
    "bottom-bar.multicommand.name": "bold",
    "bottom-bar.multicommand.type": "bold",
    "bottom-bar.multicommand.metavar": "",
    # Command
    "bottom-bar.command.name": "bold",
    "bottom-bar.command.type": "bold",
    "bottom-bar.command.metavar": "",
    "bottom-bar.parameter.type.name": "",
    # Primitive datatypes.
    "bottom-bar.parameter.type.string": "",
    "bottom-bar.parameter.type.integer": "",
    "bottom-bar.parameter.type.float": "",
    # Range types.
    "bottom-bar.parameter.type.range.integer": "",
    "bottom-bar.parameter.type.range.float": "",
    "bottom-bar.parameter.type.range.descriptor": "",
    # Path types.
    "bottom-bar.parameter.type.path": "",
    "bottom-bar.parameter.type.file": "",
    # For Boolean type options.
    "bottom-bar.parameter.type.bool": "",
    # Other arbitrary types.
    "bottom-bar.parameter.type.composite": "",
    "bottom-bar.parameter.type.choice": "",
    "bottom-bar.parameter.type.datetime": "",
    "bottom-bar.parameter.type.uuid": "",
    "bottom-bar.parameter.type.unprocessed": "",
    # Misc. for Parameter.
    "bottom-bar.parameter.nargs": "",
    "bottom-bar.parameter.nargs.counter": "fg:green",
    "bottom-bar.parameter.argument.name": "",
    "bottom-bar.parameter.option.name": "",
    # Base Paramter
    "bottom-bar.paramter.name": "",
    "bottom-bar.parameter.type": "",
    "bottom-bar.parameter.unused": "",
    "bottom-bar.parameter.inuse": "bold underline",
    "bottom-bar.parameter.used": "strike",
    # ParamType tokens especially for Tuple type.
    "bottom-bar.parameter.type.unused": "",
    "bottom-bar.parameter.type.inuse": "bold underline",
    "bottom-bar.parameter.type.used": "strike",
    # Misc.
    "bottom-bar.space": "",
    "bottom-bar.symbol": "",
    "bottom-bar.ellipsis": "",
    "bottom-bar.symbol.bracket": "",
    # For displaying Exceptions
    "bottom-bar.error": "fg:white bg:red",
    "bottom-bar.error.exception-class-name": "bold",
    "bottom-bar.error.message": "bold",
}


OTHER_MISC_STYLE_CONFIGS = {
    "misc.bold": "bold",
    "misc.underline": "underline",
    "misc.strike": "strike",
    "misc.italic": "italic",
    "misc.blink": "blink",
    "misc.reverse": "reverse",
    "misc.hidden": "hidden",
    "misc.nobold": "nobold",
    "misc.nounderline": "nounderline",
    "misc.nostrike": "nostrike",
    "misc.noitalic": "noitalic",
    "misc.noblink": "noblink",
    "misc.noreverse": "noreverse",
    "misc.nohidden": "nohidden",
}


DEFAULT_PROMPTSESSION_STYLE_CONFIG = (
    {"bottom-toolbar": "fg:lightblue bg:default noreverse"}
    | DEFAULT_BOTTOMBAR_STYLE_CONFIG
    | DEFAULT_COMPLETION_STYLE_CONFIG
    | OTHER_MISC_STYLE_CONFIGS
)


HAS_CLICK_GE_8 = click.__version__[0] >= "8"

# _NumberRangeBase class is defined in click v8.
# Therefore, this tuple is used to check for the
# range type ParamType objects.
_RANGE_TYPES = (click.IntRange, click.FloatRange)

if HAS_CLICK_GE_8:
    _RANGE_TYPES += (click.types._NumberRangeBase,)  # type:ignore[assignment]

# The only ParamType classes that have their
# get_metavar method's functionality defined.
_PARAMS_WITH_METAVAR = (click.Choice, click.DateTime)

_PATH_TYPES = (click.Path, click.File)

# If ISATTY is False, then we're not gonna run any code
# to generate auto-completions. Most of the code will be inactive
ISATTY = sys.stdin.isatty()

IS_WINDOWS = os.name == "nt"

AUTO_COMPLETION_FUNC_ATTR = (
    "_custom_shell_complete" if HAS_CLICK_GE_8 else "autocompletion"
)

# click repl environmental flag. Enable it only for debugging.
CLICK_REPL_DEV_ENV = os.getenv("CLICK_REPL_DEV_ENV", None) is not None

# To store the ReplContext objects generated throughout the Runtime.
_locals = local()
ctx_stack: list[ReplContext] = []
_locals.ctx_stack = ctx_stack
# ctx_stack = _locals.ctx_stack


def get_current_repl_ctx(silent: bool = False) -> ReplContext | NoReturn | None:
    """
    Returns the current click-repl Context, providing a way to access
    the context from anywhere in the code  This is a more implicit
    alternative to the `pass_context` decorator.

    Parameters
    ----------
    silent : bool
        If set to True the return value is None if no context
        is available. The default behavior is to raise a `RuntimeError`.

    Returns
    -------
    ctx : `ReplContext`, optional
        ReplContext object if available.

    Raises
    ------
    RuntimeError
        If there's no Context object in the stack.
    """

    try:
        return ctx_stack[-1]
    except (AttributeError, IndexError):
        if not silent:
            raise RuntimeError("There is no active click-repl context.")

    return None


def _push_context(ctx: ReplContext) -> None:
    """
    Pushes a new repl context to the current stack.

    Parameters
    ----------
    ctx : `ReplContext`
        ReplContext object that should be added to the repl context stack.
    """
    _locals.ctx_stack.append(ctx)


def _pop_context() -> None:
    """Removes the top level repl context from the stack."""
    _locals.ctx_stack.pop()
