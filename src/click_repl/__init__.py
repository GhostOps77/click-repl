"""
**click-repl** is a simple Python module that provides REPL support
inside your click app in just some simple steps.
"""

from __future__ import annotations

from ._repl import Repl, ReplGroup, register_repl, repl
from .core import ReplContext, pass_context
from .internal_commands import repl_exit

__all__ = [
    "pass_context",
    "register_repl",
    "Repl",
    "ReplGroup",
    "ReplContext",
    "repl",
    "repl_exit",
]


version_info = (0, 2, 1, 11)
__version__ = "0.2.1dev11"
