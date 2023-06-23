from __future__ import annotations

import sys
import typing as t

import click
from prompt_toolkit.history import InMemoryHistory

from ._globals import get_current_repl_ctx
from ._globals import ISATTY
from ._internal_cmds import InternalCommandSystem
from .bottom_bar import TOOLBAR
from .completer import ClickCompleter
from .core import ReplContext
from .exceptions import ClickExit
from .exceptions import ExitReplException
from .exceptions import InvalidGroupFormat
from .parser import split_arg_string
from .validator import ClickValidator

# from prompt_toolkit.auto_suggest import (AutoSuggestFromHistory,
#                                          ThreadedAutoSuggest)

if t.TYPE_CHECKING:
    from typing import Any, Callable

    from click import Context, MultiCommand


__all__ = ["Repl", "register_repl", "repl"]


class Repl:
    # __slots__ = (
    #     "group_ctx",
    #     "group",
    #     "get_command",
    #     "repl_ctx",
    #     "internal_cmd_prefix",
    #     "system_cmd_prefix",
    #     "internal_cmds_system",
    # )

    def __init__(
        self,
        prompt_kwargs: dict[str, Any] = {},
        internal_command_prefix: str | None = ":",
        system_command_prefix: str | None = "!",
        styles: dict[str, str] | None = None,
    ):
        self.prompt_kwargs = prompt_kwargs
        self.styles = styles
        self.internal_command_prefix = internal_command_prefix
        self.system_command_prefix = system_command_prefix

        # Internal Command System setup
        self.internal_commands_system = InternalCommandSystem(
            internal_command_prefix, system_command_prefix
        )

        self.get_command: Callable[[], str] = self.get_command_func()

    def bootstrap_prompt(
        self,
        prompt_kwargs: dict[str, Any],
        internal_command_prefix: str | None,
        system_command_prefix: str | None,
        styles: dict[str, str] | None,
    ) -> dict[str, Any]:
        """Bootstrap prompt_toolkit kwargs or use user defined values.

        Keyword arguments:
        :param:`group_ctx` - :class:`~click.Context` relative to the CLI Group object
        :param:`prompt_kwargs` - The user specified prompt kwargs.
        :param:`styles` - Dictionary of string to string mapping thats
            used to apply custom coloring to the
            :class:`~prompt_toolkit.completion.Completion` objects
        """
        if not ISATTY:
            return {}

        defaults = {
            "history": InMemoryHistory(),
            "completer": ClickCompleter(
                self.group_ctx,
                internal_command_prefix,
                system_command_prefix,
                styles=styles,
            ),
            "message": "> ",
            "validator": ClickValidator(
                self.group_ctx, internal_command_prefix, system_command_prefix
            ),
            # "auto_suggest": ThreadedAutoSuggest(AutoSuggestFromHistory()),
            "complete_in_thread": True,
            "complete_while_typing": True,
            "validate_while_typing": True,
            "mouse_support": True,
            "bottom_toolbar": TOOLBAR.get_formatted_text,
        }

        defaults.update(prompt_kwargs)
        return defaults

    def get_command_func(self) -> Callable[[], str]:
        if ISATTY:

            def get_command() -> str:
                return self.repl_ctx.session.prompt()  # type: ignore[no-any-return, return-value, union-attr]  # noqa: E501

        else:

            def get_command() -> str:
                inp = sys.stdin.readline().strip()
                self.repl_ctx._history.append(inp)  # type: ignore[union-attr]
                return inp

        return get_command

    def repl_check(self) -> None:
        """
        An Optional click.Argument in the CLI Group, that has no value
        will consume the first word from the REPL input, causing issues in
        executing the command
        So, if there's an empty Optional Argument, this function
        raises `InvalidGroupFormat` error
        """
        for param in self.group.params:
            if (
                isinstance(param, click.Argument)
                and self.group_ctx.params[param.name] is None  # type: ignore[index]
                and not param.required
            ):
                raise InvalidGroupFormat(
                    f"{type(self.group).__name__} '{self.group.name}' requires "
                    f"value for an optional argument '{param.name}' in REPL mode"
                )

    def execute_command(self, command: str) -> None:
        if self.repl_ctx.internal_command_system.execute(command.lower()) == 1:
            self.execute_click_cmds(command)

    def execute_click_cmds(self, command: str) -> None:
        # Split command text
        args = split_arg_string(command)

        # The group command will dispatch based on args.
        # The context object can parse args from the
        # protected_args attribute.
        old_protected_args = self.group_ctx.protected_args
        try:
            self.group_ctx.protected_args = args
            self.group.invoke(self.group_ctx)
        finally:
            self.group_ctx.protected_args = old_protected_args

    def start_setup(self, group_ctx: Context) -> None:
        """Main setup before firing up the REPL"""

        self.group_ctx: Context = group_ctx

        # parent should be available, but we're not going to bother if not
        if self.group_ctx.parent is not None and not isinstance(
            self.group_ctx.command, click.MultiCommand
        ):
            self.group_ctx = self.group_ctx.parent

        self.group: MultiCommand = self.group_ctx.command  # type: ignore[assignment]

        # Generating prompt kwargs (changing in here, also changes in the ReplContext obj)
        self.prompt_kwargs = self.bootstrap_prompt(
            self.prompt_kwargs,
            self.internal_command_prefix,
            self.system_command_prefix,
            self.styles,
        )

        # To assign the parent repl context for the next repl context
        self.repl_ctx = ReplContext(
            self.group_ctx,
            self.internal_commands_system,
            self.prompt_kwargs,
            parent=get_current_repl_ctx(silent=True),
        )

    def loop(self, group_ctx: Context) -> None:
        self.start_setup(group_ctx)
        self.repl_check()

        with self.repl_ctx:
            while True:
                try:
                    TOOLBAR.state_reset()
                    command = self.get_command()
                except KeyboardInterrupt:
                    continue
                except EOFError:
                    break

                if not command:
                    if ISATTY:
                        continue
                    else:
                        break

                try:
                    self.execute_command(command)
                except (ClickExit, SystemExit):
                    continue

                except click.ClickException as e:
                    e.show()

                # except (ClickExit, SystemExit):
                #     pass

                except ExitReplException:
                    break


def repl(
    group_ctx: Context,
    prompt_kwargs: dict[str, Any] = {},
    cls: type[Repl] | None = None,
    internal_command_prefix: str | None = ":",
    system_command_prefix: str | None = "!",
    styles: dict[str, str] | None = None,
) -> None:
    """
    Start an interactive shell. All subcommands are available in it.

    If stdin is not a TTY, no prompt will be printed, but only commands read
    from stdin.

    Keyword arguments:
    :param:`group_ctx` - The current click Context.
    :param:`prompt_kwargs` - Parameters passed to :func:`prompt_toolkit.PromptSession`.
    :param:`cls` - Repl class to use for the app.
    :param:`internal_cmd_prefix` - Prefix for executing available internal commands
    :param:`system_cmd_prefix` - Prefix for executing System/Shell commands
    :param:`styles` - Optional dictionary with 'command', 'argument'
        and 'option' style names.
    """
    ReplCls = Repl
    if cls is not None:
        ReplCls = cls

    ReplCls(prompt_kwargs, internal_command_prefix, system_command_prefix, styles).loop(
        group_ctx
    )


def register_repl(group: MultiCommand, name: str = "repl") -> None:
    """Register :func:`repl()` as sub-command `name` of `group`.

    Keyword arguments:
    :param `group`: Group/CLI object to register repl command
    :param `name`: Name of the repl command in the
        given Group (default="repl")
    """

    command = click.command(name=name)(click.pass_context(repl))
    if isinstance(group, click.Group):
        group.add_command(command, name=name)

    elif isinstance(group, click.CommandCollection):
        group.add_source(command)  # type: ignore[arg-type]

    elif not isinstance(group, click.MultiCommand):
        raise TypeError(
            f"group must be a type of MultiCommand, but got {type(group).__name__}"
        )
