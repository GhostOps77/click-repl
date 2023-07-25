"""
`click_repl._repl`

Core functionality of the REPL.
"""
import sys
import traceback
import typing as t

import click
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style

from ._globals import get_current_repl_ctx
from ._globals import ISATTY
from ._internal_cmds import InternalCommandSystem
from .bottom_bar import BottomBar
from .completer import ClickCompleter
from .core import ReplContext
from .exceptions import ClickExit
from .exceptions import ExitReplException
from .exceptions import InternalCommandException
from .exceptions import InvalidGroupFormat
from .parser import split_arg_string
from .utils import _get_group_ctx
from .utils import _print_err
from .validator import ClickValidator

if t.TYPE_CHECKING:
    from typing import Any, Dict, Optional, Type

    from click import Context, Group
    from prompt_toolkit.completion import Completer
    from prompt_toolkit.validation import Validator


__all__ = ["Repl", "repl"]


class Repl:
    """
    Responsible for executing and maintaining the REPL
    in the click_repl app.

    Parameters
    ----------
    prompt_kwargs : Dictionary of str: Any pairs.
        Keyword arguments to be passed to the `prompt_toolkit.PromptSession` class.
        Do note that you don't have to pass the Completer and Validator class
        via this dictionary.

    completer_cls : prompt_toolkit.completion.Completer type class or None.
        `prompt_toolkit.completion.Completer` class to generate
        `prompt_toolkit.completion.Completion` objects for
        auto-completion. `click_repl.completer.ClickCompleter` class
        is used by default.

    validator_cls : prompt_toolkit.validation.Validator type class or None.
        `prompt_toolkit.validation.Validator` class to display error
        messages in the bottom bar during auto-completion.
        `click_repl.validator.ClickValidator` class is used by default.

    completer_kwargs : Dictionary of str: Any pairs.
        Keyword arguments thats sent to the `completer_cls` class constructor.

    validator_kwargs : Dictionary of str: Any pairs.
        Keyword arguments thats sent to the `validator_cls` class constructor.

    internal_command_prefix : str or None.
        Prefix that triggers internal commands within the click_repl app.

    system_command_prefix : str or None.
        Prefix that triggers system commands within the click_repl app.

    Raises
    ------
    InvalidGroupFormat
        If there is an empty optional argument in the CLI Group.
    """

    __slots__ = (
        "prompt_kwargs",
        "completer_cls",
        "completer_kwargs",
        "validator_cls",
        "validator_kwargs",
        "internal_commands_system",
        "bottom_bar",
        "group_ctx",
        "group",
        "repl_ctx",
        "get_command",
    )

    def __init__(
        self,
        ctx: "Context",
        prompt_kwargs: "Dict[str, Any]" = {},
        completer_cls: "Type[Completer]" = ClickCompleter,
        validator_cls: "Optional[Type[Validator]]" = ClickValidator,
        completer_kwargs: "Dict[str, Any]" = {},
        validator_kwargs: "Dict[str, Any]" = {},
        internal_command_prefix: "Optional[str]" = ":",
        system_command_prefix: "Optional[str]" = "!",
    ):
        self.group_ctx = _get_group_ctx(ctx)
        self.group: "Group" = self.group_ctx.command  # type: ignore[assignment]

        for param in self.group.params:
            if (
                isinstance(param, click.Argument)
                and not param.required
                and self.group_ctx.params[param.name] is None  # type: ignore[index]
            ):
                # When a click.Argument(required=False) parameter in the CLI Group
                # does not have a value, it will consume the first few words from
                # the REPL input. This can cause issues in parsing and
                # executing the command.
                raise InvalidGroupFormat(self.group, param)

        self.internal_commands_system = InternalCommandSystem(
            internal_command_prefix, system_command_prefix
        )

        if ISATTY:
            self.bottom_bar: "Optional[BottomBar]" = prompt_kwargs.get(
                "bottom_toolbar", BottomBar()
            )

            if self.bottom_bar is not None:
                self.bottom_bar.show_hidden_params = completer_kwargs.get(
                    "show_hidden_params", False
                )

        else:
            self.bottom_bar = None

        self.completer_cls = completer_cls
        self.completer_kwargs = self._bootstrap_completer_kwargs(completer_kwargs)

        self.validator_cls = validator_cls
        self.validator_kwargs = self._bootstrap_validator_kwargs(validator_kwargs)

        self.prompt_kwargs = self._bootstrap_prompt_kwargs(prompt_kwargs)

        self.repl_ctx = ReplContext(
            self.group_ctx,
            self.internal_commands_system,
            prompt_kwargs=self.prompt_kwargs,
            parent=get_current_repl_ctx(silent=True),
        )

        if ISATTY:
            # If stdin is a TTY, prompt the user for input using PromptSession.
            def get_command() -> str:
                return self.repl_ctx.session.prompt()  # type: ignore

        else:
            # If stdin is not a TTY, read input from stdin directly.
            def get_command() -> str:
                inp = sys.stdin.readline().strip()
                self.repl_ctx._history.append(inp)  # type: ignore[union-attr]
                return inp

        self.get_command = get_command

    def _bootstrap_completer_kwargs(
        self, completer_kwargs: "Dict[str, Any]"
    ) -> "Dict[str, Any]":
        """
        Generates bootstrap keyword arguments for initializing a
        `prompt_toolkit.completer.Completer` object, either using
        default values or user-defined values, if available.

        Parameters
        ----------
        completer_kwargs: Dictionary of str: Any pairs.
            A dictionary that contains values for keyword arguments supplied by the
            user, that to be passed to the `prompt_toolkit.completer.Completer` class.

        Returns
        -------
        Dictionary of str: Any pairs.
            A dictionary that contains all the keyword arguments to be passed
            to the `prompt_toolkit.completer.Completer` class.
        """

        default_completer_kwargs = {
            "ctx": self.group_ctx,
            "internal_commands_system": self.internal_commands_system,
            "bottom_bar": self.bottom_bar,
        }

        default_completer_kwargs.update(completer_kwargs)
        return default_completer_kwargs

    def _bootstrap_validator_kwargs(
        self, validator_kwargs: "Dict[str, Any]"
    ) -> "Dict[str, Any]":
        """
        Generates bootstrap keyword arguments for initializing a
        `prompt_toolkit.validation.Validator` object, either
        using default values or user-defined values, if available.

        Parameters
        ----------
        validator_kwargs: Dictionary of str: Any pairs.
            A dictionary that contains values for keyword arguments supplied by the
            user, that to be passed to the `prompt_toolkit.validation.Validator` class.

        Returns
        -------
        Dictionary of str: Any pairs.
            A dictionary that contains all the keyword arguments to be passed
            to the `prompt_toolkit.validation.Validator` class.
        """

        if not ISATTY:
            # If the standard input is not a TTY device, there is no need
            # to generate any keyword arguments for rendering. In this case,
            # an empty dictionary is returned.
            return {}

        if self.validator_cls is not None:
            default_validator_kwargs = {
                "ctx": self.group_ctx,
                "internal_commands_system": self.internal_commands_system,
            }

            default_validator_kwargs.update(validator_kwargs)

            return default_validator_kwargs

        return {}

    def _bootstrap_prompt_kwargs(
        self, prompt_kwargs: "Dict[str, Any]"
    ) -> "Dict[str, Any]":
        """
        Generates bootstrap keyword arguments for initializing a
        `prompt_toolkit.PromptSession`object, either
        using default values or user-defined values, if available.

        Parameters
        ----------
        prompt_kwargs: Dictionary of str: Any pairs.
            A dictionary that contains values for keyword arguments supplied by the
            user, that to be passed to the `prompt_toolkit.PromptSession` class.

        Returns
        -------
        Dictionary of str: Any pairs.
            A dictionary that contains all the keyword arguments to be passed
            to the `prompt_toolkit.PromptSession` class.
        """

        if not ISATTY:
            # If the standard input is not a TTY device, there is no need
            # to generate any keyword arguments for rendering. In this case,
            # an empty dictionary is returned.
            return {}

        default_prompt_kwargs = {
            "history": InMemoryHistory(),
            # "message": HTML("<red>> </red>"),
            "message": "> ",
            "completer": self.completer_cls(
                **self.completer_kwargs  # type: ignore[arg-type]
            ),
            "complete_in_thread": True,
            "complete_while_typing": True,
            "validate_while_typing": True,
            "mouse_support": True,
        }

        if self.bottom_bar:
            default_prompt_kwargs.update(
                bottom_toolbar=self.bottom_bar.get_formatted_text,
                style=Style.from_dict(
                    {"bottom-toolbar": "fg:lightblue bg:default noreverse"}
                ),
            )

        if self.validator_cls is not None:
            default_prompt_kwargs.update(
                validator=self.validator_cls(
                    **self.validator_kwargs  # type: ignore[arg-type]
                )
            )

        default_prompt_kwargs.update(prompt_kwargs)

        return default_prompt_kwargs

    def execute_command(self, command: str) -> None:
        """
        Executes commands from the given command string received from the REPL.

        Parameters
        ----------
        command : str
            The command string that needs to be parsed and executed.
        """

        if not command:
            return

        if not self.repl_ctx.internal_command_system.execute(command.lower()):
            # If the `InternalCommandSystem.execute()` method cannot find any
            # prefix to invoke the internal commands, the command string is
            # executed as a click command.
            self.execute_click_command(command)

    def execute_click_command(self, command: str) -> None:
        """
        Executes click commands by parsing the given command string.

        Parameters
        ----------
        command : str
            The command string that needs to be parsed and executed.
        """

        args = split_arg_string(command)

        # The group command will dispatch based on args.
        # The context object can parse args from the
        # protected_args attribute.
        # To ensure correct parsing, we temporarily store the
        # previously available protected_args in a separate variable.
        old_protected_args = self.group_ctx.protected_args

        try:
            self.group_ctx.protected_args = args
            self.group.invoke(self.group_ctx)

        finally:
            # After the command invocation, we restore the
            # protected_args back to the group_ctx.
            self.group_ctx.protected_args = old_protected_args

    def loop(self) -> None:
        """Runs the main REPL loop."""

        with self.repl_ctx:
            while True:
                try:
                    if ISATTY and self.bottom_bar is not None:
                        # Resetting the toolbar to clear its text content,
                        # ensuring that it doesn't display command info from
                        # the previously executed command.
                        self.bottom_bar.reset_state()

                    command = self.get_command()

                except KeyboardInterrupt:
                    continue

                except EOFError:
                    break

                if not command:
                    if not ISATTY:
                        # If ISATTY is False, the input must be from stdin directly,
                        # rather than via REPL prompt. If the command
                        # string is empty, it indicates that the stdin
                        # stream has reached the end-of-file, so we
                        # break the loop.
                        break

                    # else, then it means we can still get
                    # input manually from the user in
                    # interactive mode, so we continue the loop.
                    continue

                try:
                    self.execute_command(command.strip())

                except (ClickExit, SystemExit):
                    continue

                except click.ClickException as e:
                    e.show()

                except ExitReplException:
                    break

                except InternalCommandException as e:
                    _print_err(f"{type(e).__name__}: {e}")

                except Exception:
                    traceback.print_exc()


def repl(
    group_ctx: "Context",
    prompt_kwargs: "Dict[str, Any]" = {},
    repl_cls: "Type[Repl]" = Repl,
    **attrs: "Any",
) -> None:
    """
    Start an Interactive Shell. All subcommands are available in it.

    If stdin is not a TTY, No prompt will be printed, but only subcommands
    can be read from stdin.

    Parameters
    ----------
    group_ctx : click.Context
        The current click context object.

    prompt_kwargs : Dictionary of str: Any pairs.
        Parameters passed to `prompt_toolkit.PromptSession`.
        These parameters configure the prompt appearance and behavior,
        such as prompt message, history, completion, etc.

    repl_cls : click_repl._repl.Repl type class.
        Repl class to use for the click_repl app. if `None`, the
        `click_repl._repl.Repl` class is used by default. This allows
        customization of the REPL behavior by providing a custom Repl subclass.

    **attrs : dict, optional
        Extra keyword arguments to be passed to the Repl class. These additional
        arguments can be used to further customize the behavior of the Repl class.

    Notes
    -----
    - You don't have to pass the `Completer` and `Validator` class,
    and their arguments via this dictionary.

    - Provide a text or a function to determine the content that will be displayed
    in the bottom toolbar via the `bottom_toolbar` key in the `prompt_kwargs` dictionary.
    To disable the bottom toolbar, pass `None` as the value for this key.
    """

    repl_cls(group_ctx, prompt_kwargs=prompt_kwargs, **attrs).loop()
