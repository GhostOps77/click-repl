from __future__ import annotations

import os
import shlex
from collections import defaultdict
from typing import (Any, Callable, Iterable, Mapping, NoReturn,  # noqa: F401
                    Optional, Union)

import click.parser

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

_internal_commands = {}


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
