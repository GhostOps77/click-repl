import os
import typing as t
from collections import defaultdict
from collections.abc import Sequence

import click

from .exceptions import ExitReplException

if t.TYPE_CHECKING:
    from typing import Any, Callable, Dict, NoReturn, Optional, Tuple, TypeAlias, Union

    InternalCommandCallback: TypeAlias = "Callable[[], None]"
    InternalCommandDict: TypeAlias = (
        "Dict[str, Tuple[InternalCommandCallback, Optional[str]]]"
    )


__all__ = ["exit", "InternalCommandSystem"]


def _exit_internal() -> "NoReturn":
    raise ExitReplException()


def exit() -> "NoReturn":
    """Exits the REPL"""
    _exit_internal()


class InternalCommandSystem:
    def __init__(
        self,
        internal_command_prefix: "Optional[str]",
        system_command_prefix: "Optional[str]",
    ) -> None:
        if internal_command_prefix == system_command_prefix and system_command_prefix:
            raise ValueError(
                "internal_cmd_prefix and system_command_prefix can't be same"
            )

        self.internal_command_prefix = internal_command_prefix
        self.system_command_prefix = system_command_prefix
        self._internal_commands: "InternalCommandDict" = {}

        self.register_default_internal_commands()

    def dispatch_repl_commands(self, command: str) -> None:
        """
        Execute system commands entered in the REPL.

        System commands are all commands starting with
        the given :param:`system_cmd_prefix`.
        """
        os.system(command[len(self.system_command_prefix) :])  # type: ignore[arg-type]

    def handle_internal_commands(self, command: str) -> "Optional[int]":
        """
        Run REPL-internal commands.

        REPL-internal commands are all commands starting with
        the given `internal_cmd_prefix`.
        """
        target = self.get_command(
            command[len(self.internal_command_prefix) :],  # type: ignore[arg-type]
            default=None,
        )
        if target is None:
            return -1

        return target()

    def register_command(
        self,
        target: "InternalCommandCallback",
        names: "Union[str, Sequence[str], None]" = None,
        description: "Optional[str]" = None,
    ) -> None:
        """Registers a new Internal Command"""

        if names is None:
            names = target.__name__

        if description is None:
            description = target.__doc__ or ""

        if not callable(target):
            raise ValueError("Internal command must be a callable")

        if isinstance(names, str):
            names = [names]

        elif not isinstance(names, Sequence):
            raise ValueError(
                "names must be a string, or a Sequence object, "
                f"but got {type(names).__name__}"
            )

        for name in names:
            self._internal_commands[name.lower()] = (target, description)

    def get_command(
        self, name: str, default: "Any" = None
    ) -> "Union[InternalCommandCallback, Any]":
        target_info = self._internal_commands.get(name)

        if target_info:
            return target_info[0]

        return default

    def execute(self, command: str) -> int:
        """
        Executes internal commands and system commands
        """
        if self.internal_command_prefix and command.startswith(
            self.internal_command_prefix
        ):
            result_code = self.handle_internal_commands(command)
            if result_code == -1:
                click.echo(f"{command}, command not found")
            return 0

        elif self.system_command_prefix and command.startswith(
            self.system_command_prefix
        ):
            self.dispatch_repl_commands(command)
            return 0

        return 1

    def register_default_internal_commands(self) -> None:
        def help_internal_cmd() -> None:
            """Displays general help information"""

            formatter = click.HelpFormatter()
            formatter.write_heading("REPL help")
            formatter.indent()

            if not (self.system_command_prefix or self.internal_command_prefix):
                formatter.write_text("No Internal commands are registered with this REPL")

            if self.system_command_prefix:
                with formatter.section("External/System Commands"):
                    formatter.write_text(
                        f'Prefix External commands with "{self.system_command_prefix}"'
                    )

            if self.internal_command_prefix:
                with formatter.section("Internal Commands"):
                    formatter.write_text(
                        f'Prefix Internal commands with "{self.internal_command_prefix}"'
                    )

                    info_table = defaultdict(list)
                    for mnemonic, target_info in self._internal_commands.items():
                        info_table[target_info[1]].append(mnemonic)

                    formatter.write_dl(
                        (  # type: ignore[arg-type]
                            ", ".join(f":{i}" for i in sorted(mnemonics)),
                            description,
                        )
                        for description, mnemonics in info_table.items()
                    )

            click.echo(formatter.getvalue())

        self.register_command(target=exit, names=("q", "quit", "exit"))

        self.register_command(
            target=lambda: click.clear(),
            names=("cls", "clear"),
            description="Clears screen",
        )

        self.register_command(
            target=help_internal_cmd,
            names=("?", "h", "help"),
        )
