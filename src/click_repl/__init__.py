"""
Click Repl is a simple Python module that provides REPL support
inside your click app in just some simple steps.
"""
from ._globals import get_current_repl_ctx
from ._internal_cmds import repl_exit
from ._repl import register_repl
from ._repl import repl
from .completer import ClickCompleter
from .completer import ReplCompletion
from .core import ReplCli
from .core import ReplContext
from .decorators import pass_context

__all__ = [
    "get_current_repl_ctx",
    "repl_exit",
    "register_repl",
    "repl",
    "ClickCompleter",
    "ReplCompletion",
    "ReplContext",
    "ReplCli",
    "pass_context",
]

version_info = (0, 2, 1, 3)
__version__ = "0.2.1dev3"
