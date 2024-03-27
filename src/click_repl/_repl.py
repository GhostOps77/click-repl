"""
`click_repl._repl`

Core functionality of the REPL.
"""

from __future__ import annotations

import sys
import traceback
from typing import Any, Sequence, cast

import click
from click import Context, MultiCommand
from prompt_toolkit.completion import Completer
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style, merge_styles
from prompt_toolkit.validation import Validator

from ._globals import DEFAULT_PROMPTSESSION_STYLE_CONFIG, ISATTY, get_current_repl_ctx
from ._internal_cmds import InternalCommandSystem
from .bottom_bar import BottomBar
from .completer import ClickCompleter
from .core import ReplContext
from .exceptions import (
    ClickExit,
    ExitReplException,
    InternalCommandException,
    PrefixNotFound,
)
from .parser import split_arg_string
from .utils import _generate_next_click_ctx, _get_group_ctx, print_error
from .validator import ClickValidator

__all__ = ["Repl", "repl"]


class Repl:
    """
    Responsible for executing and maintaining the REPL
    in a click_repl app.
    """

    def __init__(
        self,
        ctx: Context,
        prompt_kwargs: dict[str, Any] = {},
        completer_cls: type[Completer] | None = ClickCompleter,
        validator_cls: type[Validator] | None = ClickValidator,
        completer_kwargs: dict[str, Any] = {},
        validator_kwargs: dict[str, Any] = {},
        internal_command_prefix: str | None = ":",
        system_command_prefix: str | None = "!",
    ) -> None:
        """
        Initializes the `Repl` class.

        Parameters
        ----------
        ctx : click.Context
            The click context object of the root/parent/CLI group.

        prompt_kwargs : dict[str, Any]
            Keyword arguments to be passed to the :class:`~prompt_toolkit.PromptSession`
            class. Do note that you don't have to pass the `Completer` and `Validator`
            class via this dictionary.

        completer_cls : type[prompt_toolkit.completion.Completer], optional
            :class:`~prompt_toolkit.completion.Completer` class to generate
            :class:`~prompt_toolkit.completion.Completion` objects for auto-completion.
            :class:`~click_repl.completer.ClickCompleter` class is used by default.

        validator_cls : type[prompt_toolkit.validation.Validator] | None
            :class:`~prompt_toolkit.validation.Validator` class to display error messages
            in the bottom bar during auto-completion.
            :class:`~click_repl.validator.ClickValidator` class is used by default.

        completer_kwargs : dict[str, Any]
            Keyword arguments thats sent to the `completer_cls` class constructor.

        validator_kwargs : dict[str, Any]
            Keyword arguments thats sent to the `validator_cls` class constructor.

        internal_command_prefix : str | None
            Prefix that triggers internal commands within the click-repl app.

        system_command_prefix : str | None
            Prefix that triggers system commands within the click-repl app.
        """

        self.group_ctx = _get_group_ctx(ctx)
        """Parent group for the repl to retrieve subcommands from."""

        self.group = cast(MultiCommand, self.group_ctx.command)
        """Group used in the `group_ctx`"""

        self.internal_commands_system = InternalCommandSystem(
            internal_command_prefix, system_command_prefix
        )
        """Handles and executes internal commands that are invoked in repl."""

        if ISATTY:
            self.bottom_bar: BottomBar | None = prompt_kwargs.get(
                "bottom_toolbar", BottomBar()
            )
            """To change the command description that's dispplayed in the bottom bar
            accordingly based on the current parsing state."""

            if self.bottom_bar is not None:
                self.bottom_bar.show_hidden_params = completer_kwargs.get(
                    "show_hidden_params", False
                )

        else:
            self.bottom_bar = None

        prompt_kwargs = self._bootstrap_prompt_kwargs(
            completer_cls,
            completer_kwargs,
            validator_cls,
            validator_kwargs,
            prompt_kwargs,
        )

        self.repl_ctx = ReplContext(
            self.group_ctx,
            self.internal_commands_system,
            bottombar=self.bottom_bar,
            prompt_kwargs=prompt_kwargs,
            parent=get_current_repl_ctx(silent=True),
        )
        """Context object for the current Repl session."""

        if ISATTY:
            # If stdin is a TTY, prompt the user for input using PromptSession.
            def _get_command() -> str:
                return self.repl_ctx.session.prompt()  # type: ignore

        else:
            # If stdin is not a TTY, read input from stdin directly.
            def _get_command() -> str:
                inp = sys.stdin.readline().strip()
                self.repl_ctx._history.append(inp)
                return inp

        def get_command() -> str:
            # "split_arg_string" is called here to strip out shell comments.
            return " ".join(split_arg_string(_get_command()))

        self.get_command = get_command
        """Retrieves input for the repl."""

    def _bootstrap_completer_kwargs(
        self, completer_cls: type[Completer] | None, completer_kwargs: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Generates bootstrap keyword arguments for initializing a
        :class:`~prompt_toolkit.completer.Completer` object, either using
        default values or user-defined values, if available.

        Parameters
        ----------
        completer_cls : type[Completer]
            A :class:`~prompt_toolkit.completion.Completer` type class.

        completer_kwargs : dict[str, Any]
            Contains keyword arguments that to be passed to the
            :class:`~prompt_toolkit.completer.Completer` class.

        Returns
        -------
        dict[str, Any]
            Contains keyword arguments that to be passed to the
            :class:`~prompt_toolkit.completer.Completer` class.
        """

        if not ISATTY or completer_cls is None:
            return {}

        default_completer_kwargs = {
            "ctx": self.group_ctx,
            "internal_commands_system": self.internal_commands_system,
            "bottom_bar": self.bottom_bar,
        }

        default_completer_kwargs.update(completer_kwargs)
        return default_completer_kwargs

    def _bootstrap_validator_kwargs(
        self, validator_cls: type[Validator] | None, validator_kwargs: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Generates bootstrap keyword arguments for initializing a
        :class:`~prompt_toolkit.validation.Validator` object, either
        using default values or user-defined values, if available.

        Parameters
        ----------
        validator_cls : type[Validator]
            A :class:`~prompt_toolkit.validation.Validator` type class

        validator_kwargs : dict[str, Any]
            Contains keyword arguments that has to be passed to the
            :class:`~prompt_toolkit.validation.Validator` class.

        Returns
        -------
        dict[str, Any]
            Contains keyword arguments that has to be passed to the
            :class:`~prompt_toolkit.validation.Validator` class.
        """

        if not ISATTY or validator_cls is None:
            # If the standard input is not a TTY device, there is no need
            # to generate any keyword arguments for rendering. In this case,
            # an empty dictionary is returned.
            return {}

        if validator_cls is not None:
            default_validator_kwargs = {
                "ctx": self.group_ctx,
                "internal_commands_system": self.internal_commands_system,
            }

            default_validator_kwargs.update(validator_kwargs)
            return default_validator_kwargs

    def _bootstrap_prompt_kwargs(
        self,
        completer_cls: type[Completer] | None,
        completer_kwargs: dict[str, Any],
        validator_cls: type[Validator] | None,
        validator_kwargs: dict[str, Any],
        prompt_kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generates bootstrap keyword arguments for initializing a
        :class:`~prompt_toolkit.PromptSession` object, either
        using default values or user-defined values, if available.

        Parameters
        ----------
        completer_cls : type[Completer]
            A :class:`~prompt_toolkit.completion.Completer` type class.

        completer_kwargs : dict[str, Any]
            Contains keyword arguments that to be passed to the
            :class:`~prompt_toolkit.completer.Completer` class.

        validator_cls : type[Validator]
            A :class:`~prompt_toolkit.validation.Validator` type class

        validator_kwargs : dict[str, Any]
            Contains keyword arguments that has to be passed to the
            :class:`~prompt_toolkit.validation.Validator` class.

        Returns
        -------
        dict[str, Any]
            Contains keyword arguments that has to be passed to the
            :class:`~prompt_toolkit.PromptSession` class.
        """

        if not ISATTY:
            return {}

        default_prompt_kwargs = {
            "history": InMemoryHistory(),
            "message": "> ",
            "complete_in_thread": True,
            "complete_while_typing": True,
            "validate_while_typing": True,
            "mouse_support": True,
            "refresh_interval": 0.15,
        }

        if self.bottom_bar:
            default_prompt_kwargs.update(bottom_toolbar=self.bottom_bar)

        if completer_cls is not None:
            default_prompt_kwargs.update(
                completer=completer_cls(
                    **self._bootstrap_completer_kwargs(completer_cls, completer_kwargs)
                )
            )

        if validator_cls is not None:
            default_prompt_kwargs.update(
                validator=validator_cls(
                    **self._bootstrap_validator_kwargs(validator_cls, validator_kwargs)
                )
            )

        styles = Style.from_dict(DEFAULT_PROMPTSESSION_STYLE_CONFIG)

        if "style" in prompt_kwargs:
            _style = prompt_kwargs.pop("style")

            if isinstance(_style, dict):
                _style = Style.from_dict(_style)

            elif isinstance(_style, list):
                _style = Style(_style)

            styles = merge_styles([styles, _style])  # type:ignore[assignment]

        default_prompt_kwargs["style"] = styles
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

        try:
            self.repl_ctx.internal_command_system.execute(command.lower())

        except PrefixNotFound:
            self.execute_click_command(command)

    def execute_click_command(self, command: str | Sequence[str]) -> None:
        """
        Executes click commands by parsing the given command string.

        Parameters
        ----------
        command : str
            The command string that needs to be parsed and executed.
        """

        if isinstance(command, str):
            command = split_arg_string(command)

        ctx, _ = _generate_next_click_ctx(self.group, self.group_ctx, tuple(command))
        ctx.command.invoke(ctx)

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

                    command = self.get_command().strip()

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
                    self.execute_command(command)

                except (ClickExit, SystemExit):
                    continue

                except click.UsageError as e:
                    command_name = ""
                    if e.ctx is not None and e.ctx.command.name is not None:
                        command_name = f"{e.ctx.command.name}: "

                    print_error(f"{command_name}{e.format_message()}")

                except click.ClickException as e:
                    e.show()

                except ExitReplException:
                    break

                except InternalCommandException as e:
                    print_error(f"{type(e).__name__}: {e}")

                except Exception:
                    traceback.print_exc()


def repl(
    group_ctx: Context,
    prompt_kwargs: dict[str, Any] = {},
    cls: type[Repl] = Repl,
    **attrs: Any,
) -> None:
    """
    Start an Interactive Shell. All subcommands are available in it.

    If stdin is not a TTY, No prompt will be printed, but only subcommands
    can be read from stdin.

    Parameters
    ----------
    group_ctx : click.Context
        The current click context object.

    prompt_kwargs : dict[str, Any]
        Parameters passed to `prompt_toolkit.PromptSession`.
        These parameters configure the prompt appearance and behavior,
        such as prompt message, history, completion, etc.

    cls : type[Repl], default=Repl
        Repl class to use for the click_repl app. if `None`, the
        `click_repl._repl.Repl` class is used by default. This allows
        customization of the REPL behavior by providing a custom Repl subclass.

    **attrs : Any, optional
        Extra keyword arguments to be passed to the Repl class. These additional
        arguments can be used to further customize the behavior of the Repl class.

    Notes
    -----
    - You don't have to pass the `Completer` and `Validator` class, and their
    arguments via the `prompt_kwargs` dictionary. Pass them separately in the
    `completer_cls` and `validator_cls` arguments respectively.

    - Provide a text, a function, or a :class:`~click_repl.bottombar.BottomBar` object
    to determine the content that will be displayed in the bottom toolbar via the
    `bottom_toolbar` key in the `prompt_kwargs` dictionary. To disable the bottom
    toolbar, pass `None` as the value for this key.
    """

    cls(group_ctx, prompt_kwargs=prompt_kwargs, **attrs).loop()
