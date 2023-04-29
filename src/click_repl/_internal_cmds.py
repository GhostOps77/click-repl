import click
import os
from collections import defaultdict
from threading import local
import typing as t

from .exceptions import ExitReplException
from ._parser import split_arg_string


if t.TYPE_CHECKING:
    from typing import (  # noqa: F401
        Any, Callable, Iterable, NoReturn, Optional, Union,
        List, Dict, Tuple
    )


_locals = local()
_internal_commands = _locals.__dict__  # type: Dict[str, Tuple[Callable[[], Any], Optional[str]]]  # noqa: E501


def exit() -> 'NoReturn':
    """Exit the repl"""
    _exit_internal()


def dispatch_repl_commands(command: str) -> bool:
    """
    Execute system commands entered in the repl.

    System commands are all commands starting with "!".
    """
    if command.startswith("!"):
        os.system(command[1:])
        return True

    return False


def handle_internal_commands(command: str) -> 'Any':
    """
    Run repl-internal commands.

    Repl-internal commands are all commands starting with ":".
    """
    if command.startswith(":"):
        target = _get_registered_target(command[1:], default=None)
        if target:
            return target()


def _register_internal_command(
    names: 'Iterable[str]', target: 'Callable[[], Any]', description: 'Optional[str]' = None
) -> None:

    if not callable(target):
        raise ValueError("Internal command must be a callable")

    if isinstance(names, str):
        names = [names]

    elif isinstance(names, t.Mapping) or not isinstance(names, t.Iterable):
        raise ValueError(
            '"names" must be a string,'
            f'or an iterable object, but got "{type(names).__name__}"'
        )

    for name in names:
        _internal_commands[name] = (target, description)


def _get_registered_target(
    name: str, default: 'Optional[Any]' = None
) -> 'Union[Callable[[], Any], Any]':

    target_info = _internal_commands.get(name)
    if target_info:
        return target_info[0]
    return default


def _exit_internal() -> 'NoReturn':
    raise ExitReplException()


def _help_internal() -> str:
    formatter = click.HelpFormatter()
    formatter.write_heading("REPL help")
    formatter.indent()

    with formatter.section("External/System Commands"):
        formatter.write_text('prefix external commands with "!"')

    with formatter.section("Internal Commands"):
        formatter.write_text('prefix internal commands with ":"')
        info_table = defaultdict(list)

        for mnemonic, target_info in _internal_commands.items():
            info_table[target_info[1]].append(mnemonic)

        formatter.write_dl((  # type: ignore[arg-type]
                ", ".join(map(":{}".format, sorted(mnemonics))),
                description,
            ) for description, mnemonics in info_table.items()
        )

    return formatter.getvalue()


_register_internal_command(["q", "quit", "exit"], _exit_internal, "Exits the repl")
_register_internal_command(
    ["?", "h", "help"], _help_internal, "Displays general help information"
)


def _execute_internal_and_sys_cmds(
    command: str,
    allow_internal_commands: bool = True,
    allow_system_commands: bool = True,
) -> 'Optional[List[str]]':
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

    return split_arg_string(command)
