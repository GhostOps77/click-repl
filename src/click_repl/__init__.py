"""
Click Repl is a simple Python module that provides REPL support
inside your click app in just some simple steps.
"""

from ._completer import ClickCompleter
from ._globals import get_current_repl_ctx
from ._internal_cmds import exit
from ._repl import register_repl, repl
from .core import ClickReplContext, pass_context
from .exceptions import (
    CommandLineParserError,
    ExitReplException,
    InternalCommandException,
)

__all__ = [
    "ClickCompleter",
    "get_current_repl_ctx",
    "exit",
    "register_repl",
    "repl",
    "ClickReplContext",
    "pass_context",
    "CommandLineParserError",
    "ExitReplException",
    "InternalCommandException",
]

__version__ = "0.2.1dev1"
