from __future__ import annotations

import sys
from typing import Any, Callable, Optional  # noqa: F401

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory

from ._completer import ClickCompleter
from .exceptions import (ClickExit,  # type: ignore[attr-defined]
                         CommandLineParserError, ExitReplException)
from .utils import _execute_command

__all__ = ["bootstrap_prompt", "register_repl", "repl"]


def bootstrap_prompt(group, prompt_kwargs, ctx=None):
    # type: (click.Command, dict[str, Any], Optional[click.Context]) -> dict[str, Any]

    """
    Bootstrap prompt_toolkit kwargs or use user defined values.

    :param prompt_kwargs: The user specified prompt kwargs.
    """

    defaults = {
        "history": InMemoryHistory(),
        "completer": ClickCompleter(group, ctx=ctx),
        "message": "> ",
    }

    defaults.update(prompt_kwargs)
    return defaults


def repl(
    old_ctx,
    prompt_kwargs={},
    allow_system_commands=True,
    allow_internal_commands=True,
):
    # type: (click.Context, dict[str, Any], bool, bool) -> None

    """
    Start an interactive shell. All subcommands are available in it.

    :param old_ctx: The current Click context.
    :param prompt_kwargs: Parameters passed to
        :py:func:`prompt_toolkit.PromptSession`.

    If stdin is not a TTY, no prompt will be printed, but only commands read
    from stdin.
    """
    # parent should be available, but we're not going to bother if not
    group_ctx = old_ctx.parent or old_ctx  # type: click.Context
    group = group_ctx.command  # type: click.Command
    isatty = sys.stdin.isatty()

    # Delete the REPL command from those available, as we don't want to allow
    # nesting REPLs (note: pass `None` to `pop` as we don't want to error if
    # REPL command already not present for some reason).
    repl_command_name = old_ctx.command.name
    if isinstance(group_ctx.command, click.CommandCollection):
        available_commands = {
            cmd_name: cmd_obj
            for source in group_ctx.command.sources
            for cmd_name, cmd_obj in source.commands.items()  # type: ignore[attr-defined]
        }
    else:
        available_commands = group_ctx.command.commands  # type: ignore[attr-defined]

    original_command = available_commands.pop(repl_command_name, None)
    prompt_kwargs = bootstrap_prompt(group, prompt_kwargs, group_ctx)

    if isatty:
        # session = PromptSession(
        #   **prompt_kwargs
        # )  # type: PromptSession[Mapping[str, Any]]

        def prompt_input():
            # type: () -> str
            return PromptSession(**prompt_kwargs).prompt()

        get_command = prompt_input  # type: Callable[[], str]
    else:
        get_command = sys.stdin.readline

    while True:
        try:
            command = get_command()
        except KeyboardInterrupt:
            continue
        except EOFError:
            break

        if not command:
            if isatty:
                continue
            else:
                break

        try:
            args = _execute_command(
                command, allow_internal_commands, allow_system_commands
            )
            if args is None:
                continue

        except CommandLineParserError:
            continue

        except ExitReplException:
            break

        try:
            # default_map passes the top-level params to the new group to
            # support top-level required params that would reject the
            # invocation if missing.
            with group.make_context(
                None, args, parent=group_ctx, default_map=old_ctx.params
            ) as ctx:
                group.invoke(ctx)
                ctx.exit()

        except click.ClickException as e:
            e.show()
        except (ClickExit, SystemExit):
            pass

        except ExitReplException:
            break

    if original_command is not None:
        available_commands[repl_command_name] = original_command


def register_repl(group, name="repl"):
    # type: (click.Group, str) -> None

    """Register :func:`repl()` as sub-command *name* of *group*."""
    group.command(name=name)(click.pass_context(repl))
