"""
`click_repl._internal_cmds`

Utilities to manage the REPL's internal commands.
"""

from __future__ import annotations

import subprocess
from collections import defaultdict
from collections.abc import Generator, Iterator, Sequence
from typing import Any, Callable, Dict, List, NoReturn, Tuple

import click
from typing_extensions import TypeAlias, TypedDict

from ._globals import get_current_repl_ctx
from .exceptions import ExitReplException, PrefixNotFound, SamePrefix, WrongType
from .utils import print_error

CallableNone: TypeAlias = Callable[[], None]
InternalCommandDict: TypeAlias = Dict[str, Tuple[CallableNone, str]]
InfoTable: TypeAlias = Dict[Tuple[CallableNone, str], List[str]]


class PrefixTable(TypedDict):
    Internal: str | None
    System: str | None


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

            info_table = ics_obj._group_commands_by_callback_and_description()
            formatter.write_dl(
                [
                    (
                        ", ".join([f":{i}" for i in sorted(mnemonics)]),
                        description,
                    )
                    for (_, description), mnemonics in info_table.items()
                ]
            )

    click.echo(formatter.getvalue())


class InternalCommandSystem:
    """
    A utility for managing and executing internal/system commands
    from the REPL. Commands are triggered by their respective prefix.

    Attributes
    ----------
    internal_command_prefix
    system_command_prefix

    prefix_table : PrefixTable
        Table to keep track of the prefixes.

    shell : bool
        Flag that tells whether to run the system commands through shell or not.

    Notes
    -----
    The prefixes determine how the commands are recognized and distinguished
    within the REPL. And both the `internal_command_prefix` and `system_command_prefix`
    should not be same.
    """

    def __init__(
        self,
        internal_command_prefix: str | None = ":",
        system_command_prefix: str | None = "!",
        shell: bool = True,
    ) -> None:
        """
        Initializes a `InternalCommandSystem` object.

        Parameters
        ----------
        internal_command_prefix : str
            Prefix to trigger internal commands.

        system_command_prefix : str
            Prefix to execute bash/other command-line scripts.

        shell : bool
            Determines whether the system commands should be executed in shell or not.

        Raises
        ------
        SamePrefix
            If both `internal_command_prefix` and `system_command_prefix` are same.
        """

        if internal_command_prefix and internal_command_prefix == system_command_prefix:
            # We don't want both internal_command_prefix and system_command_prefix
            # to be the same.
            raise SamePrefix(system_command_prefix)

        self._check_prefix_validity(internal_command_prefix, "internal_command_prefix")
        self._check_prefix_validity(system_command_prefix, "system_command_prefix")

        self.prefix_table: PrefixTable = {
            "Internal": internal_command_prefix,
            "System": system_command_prefix,
        }

        self.shell = shell

        self._internal_commands: InternalCommandDict = {}
        # Directory of Internal Commands.

        self._register_default_internal_commands()

    @property
    def internal_command_prefix(self) -> str | None:
        """
        Prefix to trigger internal commands.

        Returns
        -------
        prefix : str | None
            The prefix for internal commands.

        Raises
        ------
        WrongType
            If the value being assigned is not a str type.

        SamePrefixError
            If the new prefix thats being assigned is the same as the current prefix.
        """
        return self.prefix_table["Internal"]

    @internal_command_prefix.setter
    def internal_command_prefix(self, value: str | None) -> None:
        self._check_prefix_validity(value, "internal_command_prefix")

        if value is not None and value == self.prefix_table["System"]:
            raise SamePrefix(value)

        self.prefix_table["Internal"] = value

    @property
    def system_command_prefix(self) -> str | None:
        """
        Prefix to execute system commands.

        Returns
        -------
        prefix : str | None
            The prefix for system commands.

        Raises
        ------
        WrongType
            If the value being assigned is not a str type.

        SamePrefixError
            If the new prefix thats being assigned is the same as the current prefix.
        """
        return self.prefix_table["System"]

    @system_command_prefix.setter
    def system_command_prefix(self, value: str | None) -> None:
        self._check_prefix_validity(value, "system_command_prefix")

        if value is not None and value == self.prefix_table["Internal"]:
            raise SamePrefix(value)

        self.prefix_table["System"] = value

    def _check_prefix_validity(self, prefix: str | None, var_name: str) -> None:
        """
        Checks the validity of the prefix.

        Parameters
        ----------
        prefix : str | None
            The prefix to be checked.

        var_name : str
            The name of the variable thats been passed to the `prefix` argument.

        Raises
        ------
        WrongType
            If the prefix is not of type `str` or `None`.

        ValueError
            If the prefix is an empty string.
        """

        if prefix is not None:
            if not isinstance(prefix, str):
                raise WrongType(prefix, var_name, "str or None")

            elif prefix.strip() == "":
                raise ValueError("Prefix string cannot be empty")

    def dispatch_system_commands(self, command: str) -> None:
        """
        Execute System commands entered in the REPL. System commands start with the
        :attr:`~click_repl._internal_cmds.InternalCommandSystem.system_command_prefix`
        string in the REPL.

        Parameters
        ----------
        command : str
            A string containing thse System command to be executed.
        """
        try:
            subprocess.run(command, shell=self.shell)

        except Exception as e:
            print_error(f"{type(e).__name__}: {e}")

    def handle_internal_commands(self, command: str) -> None:
        """
        Run REPL-internal commands that start with the
        :attr:`~click_repl._internal_cmds.InternalCommandSystem.internal_command_prefix`
        string in the REPL.

        Parameters
        ----------
        command : str
            String containing the Internal command to be executed.
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
        A decorator used to register a new Internal Command from a
        given function.

        Internal Commands are case-insensitive, and this decorator allows
        for easy registration of command names and aliases.

        Parameters
        ----------
        target : CallableNone | None
            The callback function for the Internal Command.

        names : str | None | Sequence[str]
            A string or a sequence of strings representing the
            command names and aliases.

        description : str | None
            A string displayed in the help text for the Internal Command.

        Returns
        -------
        Callable[[CallableNone], CallableNone] | CallableNone
            The same function object passed into this decorator,
            or a function that takes and returns the same function when called.

        Examples
        --------
        The following examples demonstrate how to register the `kill`
        function as an Internal Command:

        .. code_block python

          @register_command(
              names='kill',
              description='Kills certain process'
          )
          def kill():
              'hi'
              ...

          @register_command
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

    def _group_commands_by_callback_and_description(self) -> InfoTable:
        """
        Groups all the aliases of all the Internal Commands together from
        :attr:`~click_repl._internal_cmds.InternalCommandSystem._internal_commands`.

        Returns
        -------
        InfoTable
            Returns a dictionary that has all the aliases of a command
            under a single key.
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
            A list that contains all the names and aliases of
            each available internal command.
        """
        return list(self._group_commands_by_callback_and_description().values())

    def get_command(self, name: str, default: Any = None) -> CallableNone | Any:
        """
        Retrieves the callback function of the internal command,
        if available. Otherwise, returns the provided sentinel value
        from the default parameter.

        Parameters
        ----------
        name : str
            The name of the desired internal command.

        default : Any
            The sentinel value to be returned if the internal command
            with the given name is not found.

        Returns
        -------
        Callable[[], None] | Any
            The callback function of the Internal Command if found. If not
            found, it returns the value specified in the `default` parameter.
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
        command : str
            The command string to be parsed.

        Returns
        -------
        tuple[str, str | None]
            The first string is a flag that denotes the type of the prefix.
            The next optional string is the prefix that can be found at the
            beginning of the command string.
        """

        for flag, prefix in self.prefix_table.items():
            if prefix and command.startswith(prefix):  # type: ignore[arg-type]
                return flag, prefix  # type: ignore[return-value]

        return "Not Found", None

    def execute(self, command: str) -> None:
        """
        Executes incoming Internal and System commands.

        Parameters
        ----------
        command : str
            The command string that has to be parsed and executed.
        """

        flag, prefix = self.get_prefix(command.strip())

        if prefix is None:
            raise PrefixNotFound(
                "Cannot find Internal Command Prefix in the given query."
            )

        command = command[len(prefix) :].lstrip()

        if not command:
            print_error(f"Enter a proper {flag} Command.")

        elif flag == "Internal":
            self.handle_internal_commands(command)

        elif flag == "System":
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
