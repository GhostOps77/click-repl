"""
`click_repl._internal_cmds`

Utilities to manage the REPL's internal commands.
"""
import subprocess
import typing as t
from collections import defaultdict
from collections.abc import Sequence

import click

from ._globals import get_current_repl_ctx
from .exceptions import ExitReplException
from .exceptions import SamePrefixError
from .exceptions import WrongType
from .utils import _print_err

if t.TYPE_CHECKING:
    from typing import Callable, Optional, Union, List, Tuple, Dict

    CallableNone: t.TypeAlias = "Callable[[], None]"
    InternalCommandDict: t.TypeAlias = "Dict[str, Tuple[CallableNone, str]]"
    InfoTable: t.TypeAlias = "Dict[Tuple[CallableNone, str], List[str]]"

    class PrefixTable(t.TypedDict):
        Internal: "Optional[str]"
        System: "Optional[str]"


__all__ = ["repl_exit", "InternalCommandSystem"]


def _exit_internal() -> "t.NoReturn":
    raise ExitReplException()


def repl_exit() -> "t.NoReturn":
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
    A utility for managing and executing Internal/System commands
    from the REPL. Commands are triggered by their respective prefix.

    Parameters
    ----------
    internal_command_prefix : str
        Prefix to trigger Internal Commands.

    system_command_prefix : str
        Prefix to execute Bash/Other Command-line scripts.

    shell : bool, default: True
        Whether the System commands should be executed in Shell or not.

    Notes
    -----
    The prefixes determine how the commands are recognized and distinguished
    within the REPL. And both the internal_command_prefix and system_command_prefix
    should not be same.
    """

    def __init__(
        self,
        internal_command_prefix: "Optional[str]" = ":",
        system_command_prefix: "Optional[str]" = "!",
        shell: bool = True,
    ) -> None:
        if (
            internal_command_prefix and system_command_prefix
        ) and internal_command_prefix == system_command_prefix:
            # We don't want both internal_command_prefix and system_command_prefix
            # to be same. So, we raise SamePrefixError Exception if that happens.
            raise SamePrefixError(system_command_prefix)

        self._check_prefix_validity(internal_command_prefix, "internal_command_prefix")
        self._check_prefix_validity(system_command_prefix, "system_command_prefix")

        self.prefix_table: "PrefixTable" = {
            "Internal": internal_command_prefix,
            "System": system_command_prefix,
        }

        self.shell = shell
        self._internal_commands: "InternalCommandDict" = {}

        self._register_default_internal_commands()

    @property
    def internal_command_prefix(self) -> "Optional[str]":
        """
        Prefix used to trigger internal commands.

        Returns
        -------
        prefix: str or None
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
    def internal_command_prefix(self, value: "Optional[str]") -> None:
        self._check_prefix_validity(value, "internal_command_prefix")

        if value is not None and value == self.prefix_table["System"]:
            raise SamePrefixError(value)

        self.prefix_table["Internal"] = value

    @property
    def system_command_prefix(self) -> "Optional[str]":
        """
        Prefix used to execute system commands.

        Returns
        -------
        prefix : str or None
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
    def system_command_prefix(self, value: "Optional[str]") -> None:
        self._check_prefix_validity(value, "system_command_prefix")

        if value is not None and value == self.prefix_table["Internal"]:
            raise SamePrefixError(value)

        self.prefix_table["System"] = value

    def _check_prefix_validity(self, prefix: "Optional[str]", var_name: str) -> None:
        """
        Check the validity of the prefix.

        This function checks whether the provided prefix is of type `str` or `None`,
        and ensures that the prefix string is not empty. If the prefix is not in the
        expected type or if it is an empty string, it raises appropriate exceptions.

        Parameters
        ----------
        prefix : str or None
            The prefix to be checked.

        var_name : str
            The name of the variable thats been passed to the `prefix` argument.
            This is used to display the variable that holds the value of wrong type,
            in the error message.

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
        Execute System commands entered in the REPL.
        System commands start with the `self.system_command_prefix`
        string in the REPL.

        Parameters
        ----------
        command : str
            A string containing thse System command to be executed.
        """
        try:
            subprocess.run(command, shell=self.shell)

        except Exception as e:
            _print_err(f"{type(e).__name__}: {e}")

    def handle_internal_commands(self, command: str) -> None:
        """
        Run REPL-internal commands. REPL-internal commands start
        with the `self.internal_command_prefix` string in the REPL.

        Parameters
        ----------
        command : str
            String containing the Internal command to be executed.
        """

        target = self.get_command(command, default=None)
        if target is None:
            _print_err(f"{command!r}, command not found")

        else:
            target()

    def register_command(
        self,
        target: "Optional[CallableNone]" = None,
        *,
        names: "Union[str, Sequence[str], None]" = None,
        description: "Optional[str]" = None,
    ) -> "Union[Callable[[CallableNone], CallableNone], CallableNone]":
        """
        A decorator used to register a new Internal Command from a
        given function.

        Internal Commands are case-insensitive, and this decorator allows
        for easy registration of command names and aliases.

        The callback function for the Internal Command should not have
        any parameters or return values.

        Parameters
        ----------
        target : None, or a function that takes no arguments and returns None.
            The callback function for the Internal Command.

        names : It's a string, or a sequence of strings.
            A string or a sequence of strings representing the
            command names and aliases.

        description : str or None.
            A string displayed in the help text for the Internal Command.

        Returns
        -------
        The same function object passed into this decorator,
        or a function that takes and returns the same function when called.

        Examples
        --------
        The following examples demonstrate how to register the `kill`
        function as an Internal Command:

        ```py
        @register_command(
            names='kill',
            description='Kills certain process'
        )
        def kill():
            ...

        @register_command
        def kill():
            '''Kills certain process'''
            ...
        ```
        """

        def decorator(func: "CallableNone") -> "CallableNone":
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

            elif not isinstance(names, (t.Sequence, t.Generator)):
                raise WrongType(names, "names", "string, or a Sequence of strings")

            for name in names:
                self._internal_commands[name.lower()] = (target, description)

            return func

        if target is None:
            return decorator
        return decorator(target)

    def _group_commands_by_callback_and_description(self) -> "InfoTable":
        info_table = defaultdict(list)

        for mnemonic, target_info in self._internal_commands.items():
            info_table[target_info].append(mnemonic)

        return info_table

    def list_commands(self) -> "List[List[str]]":
        """
        List of internal commands that are available.

        Returns
        -------
        A list that contains all the names and aliases of
        each available internal command.
        """
        return list(self._group_commands_by_callback_and_description().values())

    def get_command(
        self, name: str, default: "t.Any" = None
    ) -> "Union[CallableNone, t.Any]":
        """
        Retrieves the callback function of the internal command,
        if available. Otherwise, returns the provided sentinel value
        from the default parameter.

        Parameters
        ----------
        name : str
            The name of the desired Internal Command.

        default : Any
            The sentinel value to be returned if the internal command
            with the given name is not found.

        Returns
        -------
        The callback function of the Internal Command if found. If not
        found, it returns the value specified in the `default` parameter.
        """
        target_info = self._internal_commands.get(name, None)

        if target_info:
            return target_info[0]

        return default

    def get_prefix(self, command: str) -> "t.Tuple[str, Optional[str]]":
        """
        Extracts the prefix from the beginning of a command string.

        Parameters
        ----------
        command : str
            The command string to be parsed.

        Returns
        -------
        A Tuple containing the following elements:

        - str or None
            The prefix found at the beginning of the command string,
            if present. If no prefix is found, it returns `None`.

        - str
            A flag to denote the type of the prefix.
        """

        for flag, prefix in self.prefix_table.items():
            if prefix and command.startswith(prefix):  # type: ignore[arg-type]
                return flag, prefix  # type: ignore[return-value]

        return "Not Found", None

    def execute(self, command: str) -> bool:
        """
        Executes incoming Internal and System commands.

        Parameters
        ----------
        command : str
            The command string to be parsed and executed.

        Returns
        -------
        bool
            Returns True if the given command string has the required prefix,
            the given command is available and executed successfully. False
            otherwise.
        """

        flag, prefix = self.get_prefix(command.strip())

        if prefix is None:
            return False

        command = command[len(prefix) :].lstrip()

        if not command:
            _print_err(f"Enter a proper {flag} Command.")

        elif flag == "Internal":
            self.handle_internal_commands(command)

        elif flag == "System":
            self.dispatch_system_commands(command)

        return True

    def _register_default_internal_commands(self) -> None:
        """
        Registers new Internal commands at the startup.

        This method is executed at the `__init__` method
        to add all the default Internal Commands to the REPL.
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
