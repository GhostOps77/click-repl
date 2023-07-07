"""
Click Repl is a simple Python module that provides REPL support
inside your click app in just some simple steps.
"""
from ._globals import get_current_repl_ctx
from ._internal_cmds import repl_exit
from ._repl import Repl, register_repl, repl
from .completer import ClickCompleter, ReplCompletion
from .core import ReplCli, ReplContext
from .decorators import pass_context
from .exceptions import ExitReplException, InternalCommandException

__all__ = [
    "get_current_repl_ctx",
    "repl_exit",
    "register_repl",
    "repl",
    "Repl",
    "ClickCompleter",
    "ReplCompletion",
    "ReplContext",
    "ReplCli",
    "pass_context",
    "ExitReplException",
    "InternalCommandException",
]

version_info = (0, 2, 1, 4)
__version__ = "0.2.1dev4"
