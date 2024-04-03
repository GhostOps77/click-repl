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

from ._globals import get_current_repl_ctx
from .exceptions import ExitReplException, PrefixNotFound, SamePrefix, WrongType
from .utils import print_error

CallableNone: TypeAlias = Callable[[], None]
InternalCommandDict: TypeAlias = Dict[str, Tuple[CallableNone, str]]
InfoTable: TypeAlias = Dict[Tuple[CallableNone, str], List[str]]


@dataclass
class PrefixTable:
    internal: str | None
    system: str | None

    def items(self) -> ItemsView[str, str | None]:
        return self.__dict__.items()


__all__ = ["repl_exit", "InternalCommandSystem"]


def _exit_internal() -> NoReturn:
    raise ExitReplException()


def repl_exit() -> NoReturn:
    """Exits the REPL."""
    _exit_internal()


def _help_internal_cmd() -> None:
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
                aliases_list_str = ", ".join([f":{i}" for i in sorted(aliases)])
                definitions_list.append((aliases_list_str, description))

            formatter.write_dl(definitions_list)

    click.echo(formatter.getvalue())


class InternalCommandSystem:
    """
    A utility for managing and executing internal/system commands
    from the REPL. Commands are triggered by their respective prefix.

    Parameters
    ----------
    internal_command_prefix
        Prefix to trigger internal commands.

    system_command_prefix
        Prefix to execute bash/other command-line scripts.

    Raises
    ------
    :exc:`~click_repl.exceptions.SamePrefix`
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
        shell: bool = True,
    ) -> None:
        """
        Initializes a `InternalCommandSystem` object.
        """

        if internal_command_prefix and internal_command_prefix == system_command_prefix:
            # We don't want both internal_command_prefix and system_command_prefix
            # to be the same.
            raise SamePrefix(system_command_prefix)

        self.check_prefix_validity(internal_command_prefix, "internal_command_prefix")
        self.check_prefix_validity(system_command_prefix, "system_command_prefix")

        self.prefix_table: PrefixTable = PrefixTable(
            internal_command_prefix,
            system_command_prefix,
        )
        """Table to keep track of the prefixes."""

        self.shell: bool = shell
        """Determines whether the system commands should be executed
        through the shell or not."""

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
        :exc:`~click_repl.exceptions.WrongType`
            If the value being assigned is not a str type.

        :exc:`~click_repl.exceptions.SamePrefix`
            If the new prefix thats being assigned is the same as the current prefix.
        """
        return self.prefix_table.internal

    @internal_command_prefix.setter
    def internal_command_prefix(self, value: str | None) -> None:
        self.check_prefix_validity(value, "internal_command_prefix")

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
        :exc:`~click_repl.exceptions.WrongType`
            If the value being assigned is not a :class:`str` type.

        :exc:`~click_repl.exceptions.SamePrefix`
            If the new prefix thats being assigned is the same as the current prefix.
        """
        return self.prefix_table.system

    @system_command_prefix.setter
    def system_command_prefix(self, value: str | None) -> None:
        self.check_prefix_validity(value, "system_command_prefix")

        if value is not None and value == self.prefix_table.internal:
            raise SamePrefix(value)

        self.prefix_table.system = value

    def check_prefix_validity(self, prefix: str | None, var_name: str) -> None:
        """
        Raises an error if the given ``prefix`` is not in the expected format.

        Parameters
        ----------
        prefix
            The prefix to be checked.

        var_name
            The name of the variable thats been passed to the ``prefix`` argument.

        Raises
        ------
        :exc:`~click_repl.exceptions.WrongType`
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
        Execute System commands entered in the REPL. system commands
        start with the :attr:`.system_command_prefix` string in the REPL.

        Parameters
        ----------
        command
            Contains the system command that needs to be executed.
        """
        try:
            subprocess.run(command, shell=self.shell)

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
        target: CallableNone | None = None,
        *,
        names: str | None | Sequence[str] = None,
        description: str | None = None,
    ) -> Callable[[CallableNone], CallableNone] | CallableNone:
        """
        A decorator used to register a new internal command from a given function.

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
        Callable[[CallableNone],CallableNone] | CallableNone
            The same function object passed into this decorator,
            or a function that takes and returns the same function when called.

        Example
        -------
        The following example demonstrate how to register the ``kill``
        function as an internal command:

        .. code-block:: python

            from click_repl._internal_cmds import InternalCommandSystem
            ics_obj = InternalCommandSystem()

            # Register it with some custom aliases
            @ics_obj.register_command(
                names=['kill', 'pkill],
                description='Kills certain process'
            )
            def kill():
                ...

            # Function's docstring is the command's description.
            @ics_obj.register_command
            def kill():
                '''Kills certain process'''
                ...

        """

        def decorator(func: CallableNone) -> CallableNone:
            nonlocal target, names, description

            if target is None:
                target = func

            if not callable(target):
                raise WrongType(target, "target", "function that takes no arguments")

            if names is None:
                names = [target.__name__]

            if description is None:
                description = target.__doc__ or ""

            if isinstance(names, str):
                names = [names]

            elif not isinstance(names, (Sequence, Generator, Iterator)):
                raise WrongType(names, "names", "string, or a Sequence of strings")

            for name in names:
                self._internal_commands[name.lower()] = (target, description)

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

    def get_command(self, name: str, default: Any = None) -> CallableNone | Any:
        """
        Retrieves the callback function of the internal command,
        if available. Otherwise, returns the provided sentinel value
        from the default parameter.

        Parameters
        ----------
        name
            The name of the desired internal command.

        default
            The sentinel value that has to be returned if the
            internal command with the given name is not found.

        Returns
        -------
        CallableNone | Any
            The callback function of the internal command if found. If not
            found, it returns the value specified in the ``default`` parameter.
        """

        target_info = self._internal_commands.get(name, None)

        if target_info:
            return target_info[0]

        return default

    def get_prefix(self, command: str) -> tuple[str, str | None]:
        """
        Extracts the prefix from the beginning of a command string.

        Parameters
        ----------
        command
            Input string that has to be parsed.

        Returns
        -------
        tuple[str,str | None]
            The first string is a flag that denotes the type of the prefix.
            The next optional string is the prefix that can be found at the
            beginning of the command string.
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
        :exc:`~click_repl.exceptions.PrefixNotFound`
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
        Registers new Internal commands at the startup.
        """

        self.register_command(
            target=click.clear,
            names=("cls", "clear"),
            description="Clears screen.",
        )

        self.register_command(
            target=_help_internal_cmd,
            names=("?", "h", "help"),
        )

        self.register_command(target=repl_exit, names=("q", "quit", "exit"))
