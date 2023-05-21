import sys
import typing as t

import click

# from prompt_toolkit.auto_suggest import (AutoSuggestFromHistory,
#                                          ThreadedAutoSuggest)
from prompt_toolkit.history import InMemoryHistory

from ._globals import ISATTY, get_current_repl_ctx
from ._internal_cmds import _execute_internal_and_sys_cmds
from .completer import ClickCompleter
from .core import ClickReplContext
from .exceptions import (
    ClickExit,
    CommandLineParserError,
    ExitReplException,
    InvalidGroupFormat,
)

if t.TYPE_CHECKING:
    from typing import Any, Dict, List, Optional  # noqa: F401

    from click import Context, Group  # noqa: F401


__all__ = ["register_repl", "repl"]


def bootstrap_prompt(
    group: "Group",
    prompt_kwargs: "Dict[str, Any]",
    group_ctx: "Context",
    validator: "bool",
    internal_cmd_prefix: str,
    system_cmd_prefix: str,
    styles: "Optional[Dict[str, Any]]" = None,
) -> "Dict[str, Any]":
    """Bootstrap prompt_toolkit kwargs or use user defined values.

    Keyword arguments:
    :param:`group` - click Group for CLI
    :param:`prompt_kwargs` - The user specified prompt kwargs.
    :param:`group_ctx` - click Context relative to the CLI Group object
    :param:`cli_args` - command line arguments for the CLI object
    :param:`validator` - Enable Input Validator for the REPL
    :param:`styles` - Dictionary of string to string mapping thats
        used to apply custom coloring to the
        :class:`~prompt_toolkit.completion.Completion` objects
    """
    if not ISATTY:
        return {}

    defaults = {
        "history": InMemoryHistory(),
        "completer": ClickCompleter(
            group,
            group_ctx,
            internal_cmd_prefix,
            system_cmd_prefix,
            styles=styles,
        ),
        "message": "> ",
        # "auto_suggest": ThreadedAutoSuggest(AutoSuggestFromHistory()),
        "complete_in_thread": True,
        "complete_while_typing": True,
        "mouse_support": True,
    }

    if validator and prompt_kwargs.get("validator", None) is None:
        prompt_kwargs["validator"] = None
        prompt_kwargs["validate_while_typing"] = True

    defaults.update(prompt_kwargs)
    return defaults


def repl(
    group_ctx: "Context",
    prompt_kwargs: "Dict[str, Any]" = {},
    allow_system_commands: bool = True,
    allow_internal_commands: bool = True,
    validator: bool = False,
    internal_cmd_prefix: str = ":",
    system_cmd_prefix: str = "!",
    styles: "Optional[Dict[str, str]]" = None,
) -> None:
    """
    Start an interactive shell. All subcommands are available in it.

    If stdin is not a TTY, no prompt will be printed, but only commands read
    from stdin.

    Keyword arguments:
    :param:`old_ctx` - The current click Context.
    :param:`prompt_kwargs` - Parameters passed to :func:`prompt_toolkit.PromptSession`.
    :param:`allow_system_commands` - Allow System Commands to be executed through REPL.
    :param:`allow_internal_commands` - Allow Internal Commands to be executed
        through REPL.
    :param:`validator` - Enable Input Validator for the REPL
    :param:`internal_cmd_prefix` - Prefix for executing available internal commands
    :param:`system_cmd_prefix` - Prefix for executing System/Shell commands
    :param:`styles` - Optional dictionary with 'command', 'argument'
        and 'option' style names.
    """
    # parent should be available, but we're not going to bother if not
    # group_ctx = old_ctx.parent or old_ctx  # type: Context

    if group_ctx.parent is not None and not isinstance(group_ctx.command, click.Group):
        group_ctx = group_ctx.parent

    group: "Group" = group_ctx.command  # type: ignore[assignment]

    for param in group.params:
        if (
            isinstance(param, click.Argument)
            and group_ctx.params[param.name] is None  # type: ignore[index]
            and not param.required
        ):
            raise InvalidGroupFormat(
                f"{type(group).__name__} '{group.name}' requires value for "
                f"an optional argument '{param.name}' in REPL mode"
            )

    if styles is None:
        styles = dict.fromkeys(["command", "option", "argument"], "ansiblack")

    prompt_kwargs = bootstrap_prompt(
        group,
        prompt_kwargs,
        group_ctx,
        validator,
        internal_cmd_prefix,
        system_cmd_prefix,
        styles,
    )

    # To assign the parent repl context for the next repl context
    parent_repl_ctx = get_current_repl_ctx(silent=True)

    repl_ctx = ClickReplContext(group_ctx, prompt_kwargs, parent=parent_repl_ctx)

    if ISATTY:

        def get_command() -> str:
            return repl_ctx.session.prompt()  # type: ignore[return-value, union-attr]

    else:

        def get_command() -> str:
            inp = sys.stdin.readline().strip()
            repl_ctx._history.append(inp)  # type: ignore[union-attr]
            return inp

    with repl_ctx:
        while True:
            try:
                command = get_command()
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
                args = _execute_internal_and_sys_cmds(
                    command, allow_internal_commands, allow_system_commands
                )
                if args is None:
                    continue

                # The group command will dispatch based on args.
                old_protected_args = group_ctx.protected_args
                try:
                    group_ctx.protected_args = args
                    group.invoke(group_ctx)
                finally:
                    group_ctx.protected_args = old_protected_args

            except CommandLineParserError:
                continue

            except click.ClickException as e:
                e.show()

            except (ClickExit, SystemExit):
                pass

            except ExitReplException:
                break


def register_repl(group: "Group", name: str = "repl") -> None:
    """Register :func:`repl()` as sub-command `name` of `group`.

    Keyword arguments:
    :param `group`: Group/CLI object to register repl command
    :param `name`: Name of the repl command in the
        given Group (default='repl')
    """

    group.command(name=name)(click.pass_context(repl))
