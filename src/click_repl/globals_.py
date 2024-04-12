"""
Global variables, values, and functions that are accessed across
all the files in this module.
"""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING, NoReturn

from ._ctx_stack import _context_stack

if TYPE_CHECKING:
    from .core import ReplContext

if sys.version_info < (3, 8):
    from importlib_metadata import version
else:
    from importlib.metadata import version


CLICK_VERSION: tuple[int, int, int] = tuple(  # type:ignore[assignment]
    int(i) for i in version("click").split(".")
)

IS_CLICK_GE_8 = CLICK_VERSION[0] >= 8
# The shell complete method is implemented for almost every classes in click.

IS_CLICK_GE_8_2 = CLICK_VERSION >= (8, 2)
# click deprecated many things in this version.

IS_WINDOWS = os.name == "nt"

ISATTY = sys.stdin.isatty()
"""
Flag indicating whether the program is running in a TTY (terminal) environment.
If `False`, auto-completion code will be inactive.
"""

CLICK_REPL_DEV_ENV = os.getenv("CLICK_REPL_DEV_ENV", None) is not None
"""
Environmental flag for click-repl. Enable it only for debugging purposes.

:meta hide-value:
"""


def get_current_repl_ctx(silent: bool = False) -> ReplContext | NoReturn | None:
    """
    Retrieves the current click-repl context.

    This function provides a way to access the context from anywhere
    in the code. This function serves as a more implicit alternative to the
    :func:`~click.core.pass_context` decorator.

    Parameters
    ----------
    silent
        If set to :obj:`True`, the function returns :obj:`None` if no context
        is available. The default behavior is to raise a :exc:`~RuntimeError`.

    Returns
    -------
    :class:`~click_repl.core.ReplContext` | None
        REPL context object if available, or :obj:`None` if ``silent`` is :obj:`True`.

    Raises
    ------
    RuntimeError
        If there's no context object in the stack and ``silent`` is :obj:`False`.
    """

    try:
        return _context_stack[-1]
    except IndexError:
        if not silent:
            raise RuntimeError("There is no active click-repl context.")

    return None
