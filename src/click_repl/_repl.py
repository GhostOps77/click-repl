from __future__ import with_statement

import click
import sys
from prompt_toolkit.history import InMemoryHistory

from ._completer import ClickCompleter
from .exceptions import ClickExit  # type: ignore[attr-defined]
from .exceptions import CommandLineParserError, ExitReplException
from .utils import ClickReplContext, _execute_internal_and_sys_cmds


__all__ = ["bootstrap_prompt", "register_repl", "repl"]

# typing module introduced in Python 3.5
if sys.version_info >= (3, 5):
    import typing as t

    if t.TYPE_CHECKING:
        from click import Context, Group  # noqa: F401
        from typing import Any, Optional  # noqa: F401


def bootstrap_prompt(
    group,  # type: Group
    prompt_kwargs,  # type: dict[str, Any]
    ctx=None,  # type: Optional[Context]
    style=None  # type: Optional[dict[str, Any]]
):
    # type: (...) -> dict[str, Any]
    """
    Bootstrap prompt_toolkit kwargs or use user defined values.

    :param group: click Group
    :param prompt_kwargs: The user specified prompt kwargs.
    """

    defaults = {
        "history": InMemoryHistory(),
        "completer": ClickCompleter(group, ctx=ctx, styles=style),
        "message": u"> "
    }

    defaults.update(prompt_kwargs)
    return defaults


def repl(
    old_ctx,
    prompt_kwargs={},
    allow_system_commands=True,
    allow_internal_commands=True,
    styles=None
):
    # type: (click.Context, dict[str, Any], bool, bool, Optional[dict[str, str]]) -> None

    """
    Start an interactive shell. All subcommands are available in it.

    :param styles: Optional dictionary with 'command', 'argument' and 'option' style names
    :param old_ctx: The current Click context.
    :param prompt_kwargs: Parameters passed to
        :py:func:`prompt_toolkit.PromptSession`.

    If stdin is not a TTY, no prompt will be printed, but only commands read
    from stdin.
    """
    # parent should be available, but we're not going to bother if not
    group_ctx = old_ctx.parent or old_ctx  # type: Context
    # print(f'{vars(old_ctx) = }')
    # print(f'{vars(group_ctx) = }')
    group = group_ctx.command  # type: Group  # type: ignore[assignment]
    isatty = sys.stdin.isatty()

    if styles is None:
        styles = {
            'command': 'ansiblack',
            'option': 'ansiblack',
            'argument': 'ansiblack'
        }

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

    if isatty:
        # session = PromptSession(
        #   **prompt_kwargs
        # )  # type: PromptSession[Mapping[str, Any]]
        prompt_kwargs = bootstrap_prompt(group, prompt_kwargs, group_ctx, styles)

    repl_ctx = ClickReplContext(
        group_ctx, isatty, prompt_kwargs
    )  # type: ClickReplContext
    while True:
        try:
            command = repl_ctx.get_command()
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
            args = _execute_internal_and_sys_cmds(
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
            # print(f'{dict = }')
            # print(f"{args = }")
            with group.make_context(
                None, args, parent=group_ctx, default_map=old_ctx.params
            ) as ctx:
                print(f'{ctx = }')
                print(f'{ctx.params = }')
                # ctx.invoke(
                #     group.get_command(
                #         group_ctx, args[0]
                #     ).callback,
                #     [i for i in args[1:] if not i.startswith("-")]
                # )
                group.invoke(ctx)

                # unprocessed_args = {}
                # processed_args = []
                # i = 0
                # while i <= len(args):
                #     if unprocessed_args[i].startswith("-"):
                #         unprocessed_args[
                #             unprocessed_args[i].replace('--', '').replace('-', '_')
                #         ] = unprocessed_args[i+1]

                #     processed_args.append()

                # group_ctx.invoke(ctx.command, *args, **unprocessed_args)
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
    # type: (Group, str) -> None
    """Register :func:`repl()` as sub-command *name* of *group*."""
    group.command(name=name)(click.pass_context(repl))
