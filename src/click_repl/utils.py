from __future__ import with_statement

import os
import shlex
import sys
from collections import defaultdict
from functools import wraps
from threading import local

import click
from prompt_toolkit import PromptSession

from .exceptions import CommandLineParserError, ExitReplException


__all__ = [
    "_execute_internal_and_sys_cmds",
    "_exit_internal",
    "_get_registered_target",
    "_help_internal",
    "_register_internal_command",
    "dispatch_repl_commands",
    "handle_internal_commands",
    "split_arg_string",
    "exit",
]

# typing module introduced in Python 3.5
if sys.version_info >= (3, 5):
    import typing as t

    if t.TYPE_CHECKING:
        from typing import (  # noqa: F401
            Any, Callable, Generator, Iterable, Mapping, NoReturn, Optional, Union,
            List, Dict, Tuple
        )

        from prompt_toolkit.history import History  # noqa: F401

# Abstract datatypes in collections module are moved to collections.abc
# module in Python 3.3
if sys.version_info >= (3, 3):
    from collections.abc import Iterable, Mapping  # noqa: F811
else:
    from collections import Iterable, Mapping


_internal_commands = {}  # type: Dict[str, Tuple[Callable[[], Any], Optional[str]]]
_locals = local()
_locals.__dict__['stack'] = []


class ClickReplContext:
    __slots__ = (
        "group_ctx", "isatty", "prompt_kwargs", "session", "_history", "get_command",
    )

    def __init__(self, group_ctx, isatty, prompt_kwargs):
        # type: (click.Context, bool, Dict[str, Any]) -> None
        self.group_ctx = group_ctx
        self.prompt_kwargs = prompt_kwargs
        self.isatty = isatty

        if isatty:
            self.session = PromptSession(
                **prompt_kwargs
            )  # type: Optional[PromptSession[Dict[str, Any]]]
            self._history = self.session.history  # type: Union[History, List[str]]

            def get_command():
                # type: () -> str
                return self.session.prompt()  # type: ignore[return-value, union-attr]

            self.get_command = get_command  # type: Callable[..., str]

        else:
            self.get_command = sys.stdin.readline
            self.session = None
            self._history = []

    def __enter__(self):
        # type: () -> ClickReplContext
        push_context(self)
        return self

    def __exit__(self, *args):
        # type: (Any) -> None
        pop_context()

    def prompt_reset(self):
        # type: () -> None
        if self.isatty:
            self.session = PromptSession(**self.prompt_kwargs)

    def history(self):
        # type: () -> Generator[str, None, None]
        if self._history is not None:
            yield from self._history.load_history_strings()  # type: ignore[union-attr]


def split_arg_string(string, posix=True):
    # type: (str, bool) -> List[str]
    """Split an argument string as with :func:`shlex.split`, but don't
    fail if the string is incomplete. Ignores a missing closing quote or
    incomplete escape sequence and uses the partial token as-is.
    .. code-block:: python
        split_arg_string("example 'my file")
        ["example", "my file"]
        split_arg_string("example my\\")
        ["example", "my"]
    :param string: String to split.
    """

    lex = shlex.shlex(string, posix=posix, punctuation_chars=True)
    lex.whitespace_split = True
    lex.commenters = ""
    out = []

    try:
        for token in lex:
            out.append(token)
    except ValueError:
        # Raised when end-of-string is reached in an invalid state. Use
        # the partial token as-is. The quote or escape character is in
        # lex.state, not lex.token.
        out.append(lex.token)

    return out


def get_current_click_repl_context(silent=False):
    # type: (bool) -> Union[ClickReplContext, None, NoReturn]
    try:
        return ClickReplContext(**_locals.stack[-1].__dict__)  # type: ignore[call-arg]
    except (AttributeError, IndexError) as e:
        if not silent:
            raise RuntimeError("There is no active click context.") from e

    return None


def push_context(ctx):
    # type: (ClickReplContext) -> None
    """Pushes a new context to the current stack."""
    _locals.__dict__['stack'].append(ctx)


def pop_context():
    # type: () -> None
    """Removes the top level from the stack."""
    _locals.stack.pop()


def pass_context(func):
    # type: (Callable[..., Any]) -> Callable[..., Any]
    repl_ctx = get_current_click_repl_context()
    # command = ctx.command

    @wraps(func)
    def decorator(*args, **kwargs):  # type: ignore[no-untyped-def]
        # type: (...) -> Any
        return func(repl_ctx, *args, **kwargs)

    return decorator


def _register_internal_command(names, target, description=None):
    # type: (Iterable[str], Callable[[], Any], Optional[str]) -> None

    if not hasattr(target, "__call__"):
        raise ValueError("Internal command must be a callable")

    if isinstance(names, str):
        names = [names]

    elif isinstance(names, Mapping) or not isinstance(names, Iterable):
        raise ValueError(
            '"names" must be a string, or an iterable object, but got "{}"'.format(
                type(names).__name__
            )
        )

    for name in names:
        _internal_commands[name] = (target, description)


def _get_registered_target(name, default=None):
    # type: (str, Optional[Any]) -> Union[Callable[[], Any], Any]

    target_info = _internal_commands.get(name)
    if target_info:
        return target_info[0]
    return default


def _exit_internal():
    # type: () -> NoReturn
    raise ExitReplException()


def _help_internal():
    # type: () -> str
    formatter = click.HelpFormatter()
    formatter.write_heading("REPL help")
    formatter.indent()

    with formatter.section("External Commands"):
        formatter.write_text('prefix external commands with "!"')

    with formatter.section("Internal Commands"):
        formatter.write_text('prefix internal commands with ":"')
        info_table = defaultdict(list)

        for mnemonic, target_info in _internal_commands.items():
            info_table[target_info[1]].append(mnemonic)

        formatter.write_dl(  # type: ignore[arg-type]
            (  # type: ignore[arg-type]
                ", ".join(map(":{}".format, sorted(mnemonics))),
                description,
            )
            for description, mnemonics in info_table.items()
        )

    return formatter.getvalue()


_register_internal_command(["q", "quit", "exit"], _exit_internal, "exits the repl")
_register_internal_command(
    ["?", "h", "help"], _help_internal, "displays general help information"
)


def _execute_internal_and_sys_cmds(
    command,
    allow_internal_commands=True,
    allow_system_commands=True,
):
    # type: (str, bool, bool) -> Union[List[str], None, NoReturn]
    """
    Executes internal, system, and all the other registered click commands from the input
    """
    if allow_system_commands and dispatch_repl_commands(command):
        return None

    if allow_internal_commands:
        result = handle_internal_commands(command)
        if isinstance(result, str):
            click.echo(result)
            return None

    try:
        return split_arg_string(command)
    except ValueError as e:
        # click.echo("{}: {}".format(type(e).__name__, e))
        raise CommandLineParserError("{}".format(e))


def exit():
    # type: () -> NoReturn
    """Exit the repl"""
    _exit_internal()


def dispatch_repl_commands(command):
    # type: (str) -> bool
    """
    Execute system commands entered in the repl.

    System commands are all commands starting with "!".
    """
    if command.startswith("!"):
        os.system(command[1:])
        return True

    return False


def handle_internal_commands(command):
    # type: (str) -> Any
    """
    Run repl-internal commands.

    Repl-internal commands are all commands starting with ":".
    """
    if command.startswith(":"):
        target = _get_registered_target(command[1:], default=None)
        if target:
            return target()
