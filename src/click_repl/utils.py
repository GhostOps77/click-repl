from __future__ import with_statement

import click
import os
import shlex
import sys

from collections import defaultdict
from functools import wraps
from threading import local

from .exceptions import CommandLineParserError, ExitReplException

__all__ = [
    "_register_internal_command",
    "_get_registered_target",
    "_execute_command",
    "_help_internal",
    "_exit_internal",
    "dispatch_repl_commands",
    "handle_internal_commands",
    "exit",
]

# typing module introduced in Python 3.5
if sys.version_info >= (3, 5):
    from prompt_toolkit import PromptSession  # noqa: F481
    import typing as t

    if t.TYPE_CHECKING:
        from prompt_toolkit.history import History  # noqa: F401
        from typing import (  # noqa: F401
            Any,
            Callable,
            Iterable,
            Mapping,
            NoReturn,
            Optional,
            Union,
            Generator,
        )

# Abstract datatypes in collections module are moved to collections.abc
# module in Python 3.3
if sys.version_info >= (3, 3):
    from collections.abc import Mapping, Iterable  # noqa: F811
else:
    from collections import Mapping, Iterable


_internal_commands = {}  # type: dict[str, tuple[Callable[[], Any], Optional[str]]]
_locals = local()


class ClickReplContext:
    __slots__ = ("session", "_history")

    def __init__(self, session):
        # type: (PromptSession[dict[str, Any]]) -> None
        self.session = session  # type: PromptSession[dict[str, Any]]
        self._history = self.session.history  # type: History

    def __enter__(self):
        # type: () -> ClickReplContext
        push_context(self)
        return self

    def __exit__(self, *_):
        # type: (Any) -> None
        pop_context()

    @property
    def history(self):
        # type: () -> Generator[str, None, None]
        yield from self._history.load_history_strings()


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
    _locals.__dict__.setdefault("stack", []).append(ctx)


def pop_context():
    # type: () -> None
    """Removes the top level from the stack."""
    _locals.stack.pop()


def pass_context(func):
    # type: (Callable[..., Any]) -> Callable[..., Any]
    ctx = get_current_click_repl_context()
    # command = ctx.command

    @wraps(func)
    def decorator(*args, **kwargs):  # type: ignore[no-untyped-def]
        # type: (...) -> Any
        return func(ctx, *args, **kwargs)

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

    val = formatter.getvalue()  # type: str
    return val


_register_internal_command(["q", "quit", "exit"], _exit_internal, "exits the repl")
_register_internal_command(
    ["?", "h", "help"], _help_internal, "displays general help information"
)


def _execute_command(
    command,
    allow_internal_commands=True,
    allow_system_commands=True,
):
    # type: (str, bool, bool) -> Union[list[str], None, NoReturn]
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
        return shlex.split(command)
    except ValueError as e:
        click.echo("{}: {}".format(type(e).__name__, e))
        raise CommandLineParserError(f"{e}")


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
