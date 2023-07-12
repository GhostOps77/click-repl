"""
`click_repl._internal_cmds`

Core Utilities thats used to manage the Internal Commands in the REPL.
"""
import enum
import subprocess
import typing as t
from collections import defaultdict
from collections.abc import Sequence

import click

from ._globals import get_current_repl_ctx
from .exceptions import ExitReplException
from .exceptions import SamePrefixError
from .exceptions import WrongType

if t.TYPE_CHECKING:
    from typing import Callable, Literal, Optional, Union

    CallableNone: t.TypeAlias = "t.Callable[[], None]"
    InternalCommandDict: t.TypeAlias = "t.Dict[str, t.Tuple[CallableNone, Optional[str]]]"

    class PrefixTable(t.TypedDict):
        INTERNAL: "Optional[str]"
        SYSTEM: "Optional[str]"


__all__ = ["repl_exit", "InternalCommandSystem"]


class ErrorCodes(enum.Enum):
    """An Enumeration representing Error codes.

    The ErrorCodes enum provides the following values:
    - `SUCCESS` : Indicates a successful operation.
    - `NOT_FOUND` : Indicates that a requested item,
      or command was not found.

    These error codes can be used to indicate the result or
    status of various operations within the program.
    """

    SUCCESS = enum.auto()
    NOT_FOUND = enum.auto()


def _exit_internal() -> "t.NoReturn":
    """
    Exits the REPL.

    Raises
    ------
    click_repl.exceptions.ExitReplException
        To exit out of the REPL.

    See Also
    --------
    click_repl.exceptions.ExitReplException: Exception class used to exit out of the REPL.
    """
    raise ExitReplException()


def repl_exit() -> "t.NoReturn":
    """Exits the REPL."""
    _exit_internal()


def help_internal_cmd() -> None:
    """Displays general help information."""

    formatter = click.HelpFormatter()
    formatter.write_heading("REPL help")
    formatter.indent()

    # The ReplContext object has a reference to an InternalCommandSystem
    # object, which we can use it to process its help message.
    current_repl_ctx = get_current_repl_ctx(silent=True)
    if current_repl_ctx is None:
        return

    # InternalCommandSystem object from current ReplContext object.
    ICS_obj = current_repl_ctx.internal_command_system

    # If both internal_command_prefix and system_command_prefix are not available.
    if not (ICS_obj.system_command_prefix or ICS_obj.internal_command_prefix):
        formatter.write_text("No Internal commands are registered with this REPL.")

    if ICS_obj.system_command_prefix:
        # Help message for System Prefixed Commands.

        with formatter.section("External/System Commands"):
            formatter.write_text(
                f'Prefix External/System commands with "{ICS_obj.system_command_prefix}".'
            )

    if ICS_obj.internal_command_prefix:
        # Help message for Internal Commands.

        with formatter.section("Internal Commands"):
            formatter.write_text(
                f'Prefix Internal commands with "{ICS_obj.internal_command_prefix}".'
            )

            info_table = defaultdict(list)
            for mnemonic, target_info in ICS_obj._internal_commands.items():
                info_table[target_info[1]].append(mnemonic)

            # To display the help text of each Internal Command.
            formatter.write_dl(
                (  # type: ignore[arg-type]
                    ", ".join([f":{i}" for i in sorted(mnemonics)]),
                    description,
                )
                for description, mnemonics in info_table.items()
            )

    click.echo(formatter.getvalue())


class InternalCommandSystem:
    """
    A utility for managing and executing Internal/System commands
    from the REPL. Commands are triggered by their respective prefix.
    """

    def __init__(
        self,
        internal_command_prefix: "Optional[str]" = ":",
        system_command_prefix: "Optional[str]" = "!",
        shell: bool = True,
    ) -> None:
        """
        Initialize the `InternalCommandSystem` class with the specified prefixes.

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
        within the REPL.
        """

        # If both internal_command_prefix and system_command_prefix are not None.
        if internal_command_prefix and system_command_prefix:
            # We don't want both internal_command_prefix and system_command_prefix
            # to be same. So, we raise SamePrefixError Exception if that happens.
            if internal_command_prefix == system_command_prefix:
                raise SamePrefixError(system_command_prefix)  # type: ignore[arg-type]

            if not isinstance(internal_command_prefix, str):
                raise WrongType(
                    internal_command_prefix, "internal_command_prefix", "str or None"
                )

            if not isinstance(system_command_prefix, str):
                raise WrongType(
                    system_command_prefix, "system_command_prefix", "str or None"
                )

        self.prefix_table: "PrefixTable" = {
            "INTERNAL": internal_command_prefix,
            "SYSTEM": system_command_prefix,
        }

        self.shell = shell
        self._internal_commands: "InternalCommandDict" = {}

        self.register_default_internal_commands()

    @property
    def internal_command_prefix(self) -> "Optional[str]":
        """
        Get the prefix used to trigger internal commands.

        Returns
        -------
        prefix: str or None
            The prefix for internal commands.
        """

        return self.prefix_table["INTERNAL"]

    @internal_command_prefix.setter
    def internal_command_prefix(self, value: "Optional[str]") -> None:
        """
        Set the prefix used to trigger internal commands.

        Parameters
        ----------
        value : str or None
            The new prefix for internal commands.

        Raises
        ------
        WrongType
            If the value being assigned is not a str type.

        SamePrefixError
            If the new prefix is the same as the current prefix.
        """

        if not isinstance(value, str):
            raise WrongType(value, "internal_command_prefix", "str or None")

        if value is not None and value == self.prefix_table["SYSTEM"]:
            raise SamePrefixError(value)

        self.prefix_table["INTERNAL"] = value

    @property
    def system_command_prefix(self) -> "Optional[str]":
        """
        Get the prefix used to execute system commands.

        Returns
        -------
        prefix : str or None
            The prefix for system commands.
        """
        return self.prefix_table["SYSTEM"]

    @system_command_prefix.setter
    def system_command_prefix(self, value: "Optional[str]") -> None:
        """
        Set the prefix used to execute system commands.

        Parameters
        ----------
        value : str or None
            The new prefix for system commands.

        Raises
        ------
        WrongType
            If the value being assigned is not a str type.

        SamePrefixError
            If the new prefix is the same as the current prefix.
        """

        if not isinstance(value, str):
            raise WrongType(value, "system_command_prefix", "str or None")

        if value is not None and value == self.prefix_table["INTERNAL"]:
            raise SamePrefixError(value)

        self.prefix_table["SYSTEM"] = value

    def dispatch_system_commands(self, command: str) -> "Literal[ErrorCodes.SUCCESS]":
        """ "Execute System commands entered in the REPL.
        System commands start with the `self.system_command_prefix`
        string in the REPL.

        Parameters
        ----------
        command : str
            String containing thse System command to be executed.
        """
        subprocess.run(command, shell=self.shell)

        # Since error messages can be automatically displayed by the shell,
        # there is no need to catch those errors. Therefore, the code can
        # simply return a SUCCESS code.
        return ErrorCodes.SUCCESS

    def handle_internal_commands(self, command: str) -> "Literal[ErrorCodes.SUCCESS]":
        """
        Run REPL-internal commands. REPL-internal commands start
        with the `self.internal_command_prefix` string in the REPL.

        Parameters
        ----------
        command : str
            String containing the Internal command to be executed.

        Returns
        -------
        ErrorCodes.SUCCESS
            if the Internal command is available and executed successfully.

        ErrorCodes.NOT_FOUND
            if the Internal command is not found.
        """

        target = self.get_command(command, default=None)
        if target is None:
            # If no Internal Command was found under the given command string,
            # then we still return SUCCESS code.
            click.echo(f"{command}, command not found")

        else:
            target()

        # Similarly, if the prefix is successfully found, the function can
        # return a SUCCESS code to prevent the REPL from processing the
        # command string as a click command.
        return ErrorCodes.SUCCESS

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

        names : Its a string, or a sequence of strings.
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
                raise WrongType(target, "target", "Callable")

            if names is None:
                # If the `names`` parameter is not provided,
                # the command name is extracted from the function name.
                names = [target.__name__]

            if description is None:
                # If the description parameter is not provided, the command help
                # description is extracted from the function documentation.
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

        else:
            return decorator(target)

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
        target_info = self._internal_commands.get(name)

        if target_info:
            return target_info[0]

        return default

    def get_prefix(self, command: str) -> "t.Tuple[Optional[str], str]":
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
                return prefix, flag  # type: ignore[return-value]

        return None, "NOT FOUND"

    def execute(
        self, command: str
    ) -> "Literal[ErrorCodes.NOT_FOUND, ErrorCodes.SUCCESS]":
        """
        Executes incoming Internal and System commands.

        Parameters
        ----------
        command : str
            The command string to be parsed and executed.

        Returns
        -------
        ErrorCodes.SUCCESS
            If the command is executed successfully,
            or not found (for System Commands only).

        ErrorCodes.NOT_FOUND
            If the given Internal Command is not found, or the command string is empty.
        """

        prefix, flag = self.get_prefix(command)

        if prefix is None:
            # No Prefix is found in the command string.
            return ErrorCodes.NOT_FOUND

        # Slicing the string to retain only the necessary
        # information by removing the prefix.
        command = command[len(prefix) :]

        if not command:
            # If the command string originally consists only the prefix,
            # and nothing else, we display the error message in red text.
            click.secho(
                f"Enter a proper {flag.title()} Command.", fg="red", color=True, err=True
            )

            # Even if the prefix is successfully found, the function can
            # still return the SUCCESS code to prevent the REPL from further
            # processing the command string as a click command.
            return ErrorCodes.SUCCESS

        if flag == "INTERNAL":
            return self.handle_internal_commands(command)

        elif flag == "SYSTEM":
            return self.dispatch_system_commands(command)

        return ErrorCodes.SUCCESS

    def register_default_internal_commands(self) -> None:
        """
        Registers new Internal commands at the startup.

        This method is executed at the `__init__` method
        to add all the default Internal Commands to the REPL.
        """

        # Loading clear command
        self.register_command(
            target=click.clear,
            names=("cls", "clear"),
            description="Clears screen.",
        )

        # Loading exit command
        self.register_command(target=repl_exit, names=("q", "quit", "exit"))

        # Loading help command
        self.register_command(
            target=help_internal_cmd,
            names=("?", "h", "help"),
        )
