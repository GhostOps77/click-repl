import os
import click
import typing as t
from collections import defaultdict
from collections.abc import Mapping, Iterable
from prompt_toolkit.shortcuts import clear

from .exceptions import ExitReplException
from ._globals import _internal_commands


if t.TYPE_CHECKING:
    from typing import Any, Optional, NoReturn, Union, Callable


def exit() -> "NoReturn":
    """Exit the repl"""
    _exit_internal()


def dispatch_repl_commands(command: str, system_cmd_prefix: str) -> bool:
    """
    Execute system commands entered in the repl.

    System commands are all commands starting with
    the given :param:`system_cmd_prefix`.
    """
    if command.startswith(system_cmd_prefix):
        os.system(command[len(system_cmd_prefix) :])
        return True

    return False


def handle_internal_commands(command: str, internal_cmd_prefix: str) -> "Any":
    """
    Run repl-internal commands.

    Repl-internal commands are all commands starting with
    the given `internal_cmd_prefix`.
    """
    if command.startswith(internal_cmd_prefix):
        target = _get_registered_target(command[len(internal_cmd_prefix) :], default=None)
        if target:
            return target()


def _register_internal_command(
    names: "Iterable[str]",
    target: "Callable[[], Any]",
    description: "Optional[str]" = None,
) -> None:
    if not callable(target):
        raise ValueError("Internal command must be a callable")

    if isinstance(names, str):
        names = [names]

    elif isinstance(names, Mapping) or not isinstance(names, Iterable):
        raise ValueError(
            '"names" must be a string, or an iterable object, '
            f'but got "{type(names).__name__}"'
        )

    for name in names:
        _internal_commands[name] = (target, description)


def _get_registered_target(
    name: str, default: "Optional[Any]" = None
) -> "Union[Callable[[], Any], Any]":
    target_info = _internal_commands.get(name)
    if target_info:
        return target_info[0]
    return default


def _exit_internal() -> "NoReturn":
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

        formatter.write_dl(
            (  # type: ignore[arg-type]
                ", ".join(f":{i}" for i in sorted(mnemonics)),
                description,
            )
            for description, mnemonics in info_table.items()
        )

    return formatter.getvalue()


_register_internal_command(("q", "quit", "exit"), _exit_internal, "Exits the repl")
_register_internal_command(("cls", "clear"), clear, "Clears screen")
_register_internal_command(
    ("?", "h", "help"), _help_internal, "Displays general help information"
)


def _execute_internal_and_sys_cmds(
    command: str,
    internal_cmd_prefix: "Optional[str]",
    system_cmd_prefix: "Optional[str]",
) -> None:
    """
    Executes internal, system, and all the other registered click commands from the input
    """
    if system_cmd_prefix is not None and dispatch_repl_commands(
        command, system_cmd_prefix
    ):
        return None

    if internal_cmd_prefix is not None:
        result = handle_internal_commands(command, internal_cmd_prefix)
        if isinstance(result, str):
            click.echo(result)
            return None
