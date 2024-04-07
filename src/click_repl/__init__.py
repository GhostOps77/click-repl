"""
**click-repl** is a simple Python module that provides REPL support
inside your click app in just some simple steps.
"""

from __future__ import annotations

from ._internal_cmds import repl_exit
from ._repl import Repl, ReplCli, repl
from .core import ReplContext
from .decorators import pass_context, register_repl

__all__ = [
    "repl_exit",
    "Repl",
    "repl",
    "ReplCli",
    "ReplContext",
    "pass_context",
    "register_repl",
]

version_info = (0, 2, 1, 10)
__version__ = "0.2.1dev10"
