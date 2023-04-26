"""
Click Repl is a simple Python module that provides REPL support
inside your click app in just some simple steps.
"""

from ._completer import ClickCompleter as ClickCompleter  # noqa: F401

from ._repl import register_repl as register_repl  # noqa: F401
from ._repl import repl as repl  # noqa: F401

from .exceptions import CommandLineParserError as CommandLineParserError  # noqa: F401
from .exceptions import ExitReplException as ExitReplException  # noqa: F401
from .exceptions import (  # noqa: F401
    InternalCommandException as InternalCommandException,
)
from .utils import exit as exit  # noqa: F401

from .core import ClickReplContext as ClickReplContext  # noqa: F401
from .core import pass_context as pass_context  # noqa: F401

from ._globals import (  # noqa: F401
    get_current_repl_ctx as get_current_repl_ctx
)


__version__ = "0.2.1dev1"
