"""
Utilities to manage the REPL's internal commands.
"""

from __future__ import annotations

import subprocess
from collections import defaultdict
from collections.abc import Generator, Iterator, Sequence
from dataclasses import dataclass
from typing import Any, Callable, Dict, ItemsView, List, NoReturn, Tuple

import click
from typing_extensions import TypeAlias

from .exceptions import (
    ExitReplException,
    InternalCommandNotFound,
    PrefixNotFound,
    SamePrefix,
    WrongType,
)
from .globals_ import get_current_repl_ctx
from .utils import print_error

__all__ = ["repl_exit", "InternalCommandSystem"]


InternalCommandDict: TypeAlias = Dict[str, Tuple[Callable[[], None], str]]
# Dictionary that holds all the internal command's aliases with their callback, and
# description.

InfoTable: TypeAlias = Dict[Tuple[Callable[[], None], str], List[str]]
# Dictionary that holds all the aliases of a command together in a key: value pair,
# with it's callback and description.


@dataclass
class PrefixTable:
    internal: str | None
    system: str | None

    def items(self) -> ItemsView[str, str | None]:
        return self.__dict__.items()


_MISSING = object()


def _exit_internal() -> NoReturn:
    raise ExitReplException()


def repl_exit() -> NoReturn:
    """Exits the REPL."""
    _exit_internal()


def _help_internal_command() -> None:
    """Displays general help information."""

    formatter = click.HelpFormatter()
    formatter.write_heading("REPL help")
    formatter.indent()

    current_repl_ctx = get_current_repl_ctx(silent=True)
    if current_repl_ctx is None:
        return

    ics_obj = current_repl_ctx.internal_command_system

    if not (ics_obj.system_command_prefix or ics_obj.internal_command_prefix):
        formatter.write_text("No Internal commands are registered with this REPL.")

    if ics_obj.system_command_prefix:
        with formatter.section("External/System Commands"):
            formatter.write_text(
                f'Prefix External/System commands with "{ics_obj.system_command_prefix}".'
            )

    if ics_obj.internal_command_prefix:
        with formatter.section("Internal Commands"):
            formatter.write_text(
                f'Prefix Internal commands with "{ics_obj.internal_command_prefix}".'
            )

            info_table = ics_obj._group_commands_by_callback_and_desc()
            definitions_list: list[tuple[str, str]] = []

            for (_, description), aliases in info_table.items():
                aliases_list_str = ", ".join(f":{i}" for i in sorted(aliases))
                definitions_list.append((aliases_list_str, description))

            formatter.write_dl(definitions_list)

    click.echo(formatter.getvalue())


class InternalCommandSystem:
    """
    Utility for managing and executing internal/system commands from the REPL.
    Commands are triggered by their respective prefixes.

    Parameters
    ----------
    internal_command_prefix
        Prefix to trigger internal commands.

    system_command_prefix
        Prefix to execute bash/other command-line scripts.

    Raises
    ------
    click_repl.exceptions.SamePrefix
        If both :attr:`.internal_command_prefix` and
        :attr:`.system_command_prefix` are same.

    Note
    ----
    The prefixes determine how the commands are recognized and distinguished
    within the REPL. And both the :attr:`.internal_command_prefix` and
    :attr:`.system_command_prefix` should not be same.
    """

    def __init__(
        self,
        internal_command_prefix: str | None = ":",
        system_command_prefix: str | None = "!",
    ) -> None:
        """
        Initializes a `InternalCommandSystem` object.
        """

        if internal_command_prefix and internal_command_prefix == system_command_prefix:
            # We don't want both internal_command_prefix and system_command_prefix
            # to be the same.
            raise SamePrefix(system_command_prefix)

        self.validate_prefix(internal_command_prefix, "internal_command_prefix")
        self.validate_prefix(system_command_prefix, "system_command_prefix")

        self.prefix_table: PrefixTable = PrefixTable(
            internal_command_prefix,
            system_command_prefix,
        )
        """Table to keep track of the prefixes."""

        self._internal_commands: InternalCommandDict = {}
        """Directory of internal commands."""

        self._register_default_internal_commands()

    @property
    def internal_command_prefix(self) -> str | None:
        """
        Prefix to trigger internal commands.

        Returns
        -------
        :class:`str` | None
            The prefix for internal commands, if available.

        Raises
        ------
        click_repl.exceptions.WrongType
            If the value being assigned is not of type :class:`str`.

        click_repl.exceptions.SamePrefix
            If the new prefix thats being assigned is the same as the current prefix.
        """
        return self.prefix_table.internal

    @internal_command_prefix.setter
    def internal_command_prefix(self, value: str | None) -> None:
        self.validate_prefix(value, "internal_command_prefix")

        if value is not None and value == self.prefix_table.system:
            raise SamePrefix(value)

        self.prefix_table.internal = value

    @property
    def system_command_prefix(self) -> str | None:
        """
        Prefix to execute system commands.

        Returns
        -------
        :class:`str` | None
            The prefix for system commands, if available.

        Raises
        ------
        click_repl.exceptions.WrongType
            If the value being assigned is not of type :class:`str`.

        click_repl.exceptions.SamePrefix
            If the new prefix thats being assigned is the same as the current prefix.
        """
        return self.prefix_table.system

    @system_command_prefix.setter
    def system_command_prefix(self, value: str | None) -> None:
        self.validate_prefix(value, "system_command_prefix")

        if value is not None and value == self.prefix_table.internal:
            raise SamePrefix(value)

        self.prefix_table.system = value

    def validate_prefix(self, prefix: str | None, var_name: str) -> None:
        """
        Raises an error if the given ``prefix`` is not in the expected format.

        Parameters
        ----------
        prefix
            The prefix to be checked.

        var_name
            The name of the variable passed to the ``prefix`` argument.

        Raises
        ------
        click_repl.exceptions.WrongType
            If the prefix is not of type :class:`str` or `None`.

        ValueError
            If the prefix is an empty string.
        """

        if prefix is None:
            return

        if not isinstance(prefix, str):
            raise WrongType(prefix, var_name, "str or None")

        elif prefix.strip() == "":
            raise ValueError("Prefix string cannot be empty")

    def dispatch_system_commands(self, command: str) -> None:
        """
        Execute system commands entered in the REPL. System commands
        start with the :attr:`.system_command_prefix` string in the REPL.

        Parameters
        ----------
        command
            Contains the system command that needs to be executed.
        """
        try:
            subprocess.run(command, shell=True)

        except Exception as e:
            print_error(f"{type(e).__name__}: {e}")

    def handle_internal_commands(self, command: str) -> None:
        """
        Run REPL-internal commands that start with the
        :attr:`.internal_command_prefix` string in the REPL.

        Parameters
        ----------
        command
            Contains the internal command that needs to be to be executed.
        """

        target = self.get_command(command, default=None)
        if target is None:
            print_error(f"{command!r}, command not found")

        else:
            target()

    def register_command(
        self,
        target: Callable[[], None] | None = None,
        *,
        names: str | None | Sequence[str] = None,
        description: str | None = None,
    ) -> Callable[[Callable[[], None]], Callable[[], None]] | Callable[[], None]:
        """
        Decorator used to register a new internal command from a given function.

        internal commands are case-insensitive, and this decorator allows
        for easy registration of command names and aliases.

        Parameters
        ----------
        target
            The callback function for the internal command.

        names
            Contains command names and aliases.

        description
            Help text for the internal command.

        Returns
        -------
        Callable[[Callable[[],None]],Callable[[],None]] | Callable[[],None]
            The same function object passed into this decorator,
            or a function that takes and returns the same function when called.
        """

        def decorator(func: Callable[[], None]) -> Callable[[], None]:
            nonlocal target, names, description

            if target is None:
                target = func

            elif not callable(target):
                raise WrongType(target, "target", "function that takes no arguments")

            if description is None:
                description = target.__doc__ or ""

            if names is None:
                names = [target.__name__]

            elif isinstance(names, str):
                names = [names]

            elif not isinstance(names, (Sequence, Generator, Iterator)):
                raise WrongType(names, "names", "string, or a Sequence of strings")

            new_commands_dict: InternalCommandDict = {}

            for name in dict.fromkeys(names):
                if name in self._internal_commands:
                    raise ValueError(
                        f"internal command name/alias already exists: '{name}'"
                    )

                new_commands_dict[name.lower()] = (target, description)

            self._internal_commands.update(new_commands_dict)
            return func

        if target is None:
            return decorator
        return decorator(target)

    def _group_commands_by_callback_and_desc(self) -> InfoTable:
        """
        Groups all the aliases of all the internal commands together from
        :attr:`._internal_commands`.

        Returns
        -------
        InfoTable
            Dictionary that has all the aliases of a command under a single key.
        """
        info_table = defaultdict(list)

        for mnemonic, target_info in self._internal_commands.items():
            info_table[target_info].append(mnemonic)

        return info_table

    def list_commands(self) -> list[list[str]]:
        """
        List of internal commands that are available.

        Returns
        -------
        list[list[str]]
            Contains all the names and aliases of each available internal command.
        """
        return list(self._group_commands_by_callback_and_desc().values())

    def get_command(self, name: str, default: Any = _MISSING) -> Callable[[], None] | Any:
        """
        Retrieves the callback function of the internal command if available.

        Parameters
        ----------
        name
            The name of the desired internal command.

        default
            The sentinel value that has to be returned if the
            internal command with the given name is not found.

        Returns
        -------
        Callable[[],None] | Any
            The callback function of the internal command if found. If not
            found, it returns the value specified in the ``default`` parameter.
        """

        target_info = self._internal_commands.get(name, None)

        if target_info:
            return target_info[0]

        if default == _MISSING:
            raise InternalCommandNotFound(name)

        return default

    def remove_command(self, name: str, remove_all_aliases: bool = True) -> None:
        """
        Removes the internal command with the given name, if it exists.

        Parameters
        ----------
        name
            The name of the internal command to be removed.

        remove_all_aliases
            Determines whether to remove all aliases associated with the command.

        Raises
        ------
        InternalCommandNotFound
            If there's no such internal command with the specific ``name``.
        """
        name = name.lower()
        info_table = self._group_commands_by_callback_and_desc()

        if not remove_all_aliases and name in self._internal_commands:
            self._internal_commands.pop(name)
            return

        else:
            for _, mnemonics in info_table.items():
                if name in mnemonics:
                    for mnemonic in mnemonics:
                        self._internal_commands.pop(mnemonic)
                    return

        raise InternalCommandNotFound(name)

    def get_prefix(self, command: str) -> tuple[str, str | None]:
        """
        Extracts the prefix from the beginning of the ``command`` string.

        Parameters
        ----------
        command
            Input string that needs to be parsed.

        Returns
        -------
        tuple[str,str | None]
            A tuple containing two elements:
            - The type of the prefix.
            - The prefix found at the beginning of the command string.
              ``None`` if it's not known.
        """

        for flag, prefix in self.prefix_table.items():
            if prefix and command.startswith(prefix):  # type: ignore[arg-type]
                return flag, prefix  # type: ignore[return-value]

        return "Not Found", None

    def execute(self, string: str) -> None:
        """
        Executes incoming Internal and System commands.

        Parameters
        ----------
        string
            Input string that has to be parsed and executed.

        Raises
        ------
        PrefixNotFound
            If there's no internal prefix used in the given command.
        """

        flag, prefix = self.get_prefix(string.strip())

        if prefix is None:
            raise PrefixNotFound(
                "Cannot find internal command prefix in the given query."
            )

        command = string[len(prefix) :].lstrip()

        if not command:
            print_error(f"Enter a proper {flag} Command.")

        elif flag == "internal":
            self.handle_internal_commands(command)

        elif flag == "system":
            self.dispatch_system_commands(command)

    def _register_default_internal_commands(self) -> None:
        """
        Registers the default internal commands at the startup.
        """

        self.register_command(
            target=click.clear,
            names=("cls", "clear"),
            description="Clears screen.",
        )

        self.register_command(
            target=_help_internal_command,
            names=("?", "h", "help"),
        )

        self.register_command(target=repl_exit, names=("q", "quit", "exit"))
