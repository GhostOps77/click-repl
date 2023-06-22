import os
import click
import typing as t
from collections import defaultdict
from collections.abc import Sequence

from .exceptions import ExitReplException

if t.TYPE_CHECKING:
    from typing import Any, Optional, NoReturn, Union, Callable, Tuple, Dict, TypeAlias
    InternalCommandDict: TypeAlias = Dict[str, Tuple[Callable[[], Any], Optional[str]]]


__all__ = ['exit', 'InternalCommandSystem']


def _exit_internal() -> "NoReturn":
    raise ExitReplException()

def exit() -> "NoReturn":
    """Exits the REPL"""
    _exit_internal()


class InternalCommandSystem:
    def __init__(self, internal_cmd_prefix, sys_cmd_prefix) -> None:
        if internal_cmd_prefix == sys_cmd_prefix and sys_cmd_prefix:
            raise ValueError("internal_cmd_prefix and sys_cmd_prefix can't be same")

        self.internal_cmd_prefix: str = internal_cmd_prefix
        self.sys_cmd_prefix: str = sys_cmd_prefix
        self._internal_commands: "InternalCommandDict" = {}

        self.register_default_interal_cmds()

    def get_command_prefix(self, command) -> "Optional[str]":
        if self.internal_cmd_prefix and command.startswith(self.internal_cmd_prefix):
            return self.internal_cmd_prefix

        elif self.sys_cmd_prefix and command.startswith(self.sys_cmd_prefix):
            return self.sys_cmd_prefix

    def dispatch_repl_commands(self, command: str) -> None:
        """
        Execute system commands entered in the REPL.

        System commands are all commands starting with
        the given :param:`system_cmd_prefix`.
        """
        os.system(command[len(self.sys_cmd_prefix) :])

    def handle_internal_commands(self, command: str) -> "Any":
        """
        Run REPL-internal commands.

        REPL-internal commands are all commands starting with
        the given `internal_cmd_prefix`.
        """
        target = self._get_registered_target(
            command[len(self.internal_cmd_prefix) :], default=None
        )
        if target:
            return target()

    def _register_internal_command(
        self,
        target: "Optional[Callable[[], None]]",
        names: "Union[str, Sequence[str], None]" = None,
        description: "Optional[str]" = None,
    ) -> None:
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
                'names must be a string, or a Sequence object, '
                f'but got {type(names).__name__}'
            )

        for name in names:
            self._internal_commands[name] = (target, description)

    def _get_registered_target(
        self, name: str, default: "Optional[Any]" = None
    ) -> "Union[Callable[[], Any], Any]":
        target_info = self._internal_commands.get(name)

        if target_info:
            return target_info[0]

        return default

    def execute(self, command: str) -> int:
        """
        Executes internal, system, and all the other registered click commands from the input
        """
        prefix = self.get_command_prefix(command)
        if prefix == self.sys_cmd_prefix:
            self.dispatch_repl_commands(command)
            return 0

        elif prefix == self.internal_cmd_prefix:
            self.handle_internal_commands(command)
            return 0

        else:
            return 1

    def register_default_interal_cmds(self) -> None:
        def _help_internal() -> None:
            """Displays general help information"""

            formatter = click.HelpFormatter()
            # formatter.write_heading("REPL help")
            # formatter.indent()
            with formatter.section("REPL help"):
              if self.sys_cmd_prefix:
                  with formatter.section("External/System Commands"):
                      formatter.write_text(
                          f'prefix external commands with "{self.sys_cmd_prefix}"'
                      )

              if self.internal_cmd_prefix:
                  with formatter.section("Internal Commands"):
                      formatter.write_text(
                          f'prefix internal commands with "{self.internal_cmd_prefix}"'
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

        self._register_internal_command(
            target=exit, names=("q", "quit", "exit")
        )

        self._register_internal_command(
            target=lambda: click.clear(), names=("cls", "clear"),
            description="Clears screen"
        )

        self._register_internal_command(
            target=_help_internal,
            names=("?", "h", "help"),
        )
