"""
Click Repl is a simple Python module that provides REPL support
inside your click app in just some simple steps.
"""

from ._globals import get_current_repl_ctx
from ._internal_cmds import exit
from ._repl import register_repl, repl
from .completer import ClickCompleter, ReplCompletion
from .core import ReplContext
from .decorators import pass_context, repl_cli
from .exceptions import (
    CommandLineParserError,
    ExitReplException,
    InternalCommandException,
)

__all__ = [
    "ClickCompleter",
    "ReplCompletion",
    "get_current_repl_ctx",
    "exit",
    "register_repl",
    "repl",
    "ReplContext",
    "pass_context",
    "repl_cli",
    "CommandLineParserError",
    "ExitReplException",
    "InternalCommandException",
]

version_info = (0, 2, 1, 1)
__version__ = "0.2.1dev2"
