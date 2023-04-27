from __future__ import with_statement

import click
import sys
from prompt_toolkit.auto_suggest import ThreadedAutoSuggest, AutoSuggestFromHistory
from prompt_toolkit.history import InMemoryHistory

from ._completer import ClickCompleter
from .exceptions import ClickExit
from .exceptions import CommandLineParserError, ExitReplException, InvalidGroupFormatError
from .utils import _execute_internal_and_sys_cmds
from .core import ClickReplContext


__all__ = ["bootstrap_prompt", "register_repl", "repl"]

# typing module introduced in Python 3.5
if sys.version_info >= (3, 5):
    import typing as t

    if t.TYPE_CHECKING:
        from click import Context, Group, Command  # noqa: F401
        from typing import Any, Optional, Dict  # noqa: F401


def bootstrap_prompt(
    group,  # type: Group
    prompt_kwargs,  # type: Dict[str, Any]
    ctx,  # type: Context
    style=None,  # type: Optional[Dict[str, Any]]
):
    # type: (...) -> Dict[str, Any]
    """
    Bootstrap prompt_toolkit kwargs or use user defined values.

    :param group: click Group
    :param prompt_kwargs: The user specified prompt kwargs.
    """

    defaults = {
        "history": InMemoryHistory(),
        "completer": ClickCompleter(group, ctx, styles=style),
        # fmt: off
        "message": u"> ",
        # fmt: on
        "auto_suggest": ThreadedAutoSuggest(AutoSuggestFromHistory()),
        "complete_in_thread": True,
        "complete_while_typing": True,
        "mouse_support": True,
    }

    defaults.update(prompt_kwargs)
    return defaults


def repl(
    old_ctx,
    prompt_kwargs={},
    allow_system_commands=True,
    allow_internal_commands=True,
    styles=None,
):
    # type: (click.Context, Dict[str, Any], bool, bool, Optional[Dict[str, str]]) -> None
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
    group = group_ctx.command  # type: Group  # type: ignore[assignment]
    isatty = sys.stdin.isatty()

    if styles is None:
        styles = {
            "command": "ansiblack",
            "option": "ansiblack",
            "argument": "ansiblack",
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

    with ClickReplContext(group_ctx, isatty, prompt_kwargs) as repl_ctx:
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
                # with group.make_context(
                #     None, args, parent=group_ctx, default_map=old_ctx.params
                # ) as ctx:
                #     group.invoke(ctx)
                #     ctx.exit()

                # The group command will dispatch based on args.
                old_protected_args = group_ctx.protected_args
                try:
                    group_ctx.protected_args = args
                    group.invoke(group_ctx)
                finally:
                    group_ctx.protected_args = old_protected_args

            except click.ClickException as e:
                e.show()

            except (ClickExit, SystemExit):
                pass

            except ExitReplException:
                break

        if original_command is not None:
            available_commands[repl_command_name] = original_command


def register_repl(group, name="repl", pass_group_args_via_repl=False):
    # type: (Group, str, bool) -> Command
    """Register :func:`repl()` as sub-command *name* of *group*."""

    if pass_group_args_via_repl:
        for param in group.params:
            if param.nargs == -1:
                raise InvalidGroupFormatError('A Group arg cannot have nargs=-1')

            # elif isinstance(param, click.Argument):
            #     raise InvalidGroupFormatError(
            #         "A repl CLI group cannot have Argument type options"
            #     )

    return group.command(name=name)(click.pass_context(repl))
