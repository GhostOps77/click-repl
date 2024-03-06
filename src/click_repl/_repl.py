"""
`click_repl._repl`

Core functionality of the REPL.
"""
from __future__ import annotations

import sys
import traceback
import typing as t
from typing import Any
from typing import cast
from typing import Sequence

import click
from click import Context
from click import MultiCommand

from ._globals import get_current_repl_ctx
from ._globals import ISATTY
from ._internal_cmds import InternalCommandSystem
from .core import ReplContext
from .exceptions import ClickExit
from .exceptions import ExitReplException
from .exceptions import InternalCommandException
from .exceptions import PrefixNotFound
from .parser import split_arg_string
from .utils import _generate_next_click_ctx
from .utils import _get_group_ctx
from .utils import print_error


if t.TYPE_CHECKING or ISATTY:
    from prompt_toolkit.styles import Style, merge_styles
    from prompt_toolkit.completion import Completer
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.validation import Validator

    from ._globals import DEFAULT_PROMPTSESSION_STYLE_CONFIG
    from .bottom_bar import BottomBar
    from .completer import ClickCompleter
    from .validator import ClickValidator


__all__ = ["Repl", "repl"]


class Repl:
    """
    Responsible for executing and maintaining the REPL
    in a click_repl app.

    Parameters
    ----------
    ctx : `click.Context`
        The click context object of the root/parent/CLI group.

    prompt_kwargs : Dictionary of `str: Any` pairs
        Keyword arguments to be passed to the `prompt_toolkit.PromptSession` class.
        Do note that you don't have to pass the Completer and Validator class
        via this dictionary.

    completer_cls : `prompt_toolkit.completion.Completer` type class, optional
        `Completer` class to generate `prompt_toolkit.completion.Completion`
        objects for auto-completion. `ClickCompleter` class is used by default.

    validator_cls : `prompt_toolkit.validation.Validator` type class, optional
        `Validator` class to display error messages in the bottom bar
        during auto-completion. `ClickValidator` class is used by default.

    completer_kwargs : Dictionary of `str: Any` pairs
        Keyword arguments thats sent to the `completer_cls` class constructor.

    validator_kwargs : Dictionary of `str: Any` pairs
        Keyword arguments thats sent to the `validator_cls` class constructor.

    internal_command_prefix : str or None
        Prefix that triggers internal commands within the click_repl app.

    system_command_prefix : str or None
        Prefix that triggers system commands within the click_repl app.
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
        self.group_ctx = _get_group_ctx(ctx)
        self.group = cast(MultiCommand, self.group_ctx.command)

        self.internal_commands_system = InternalCommandSystem(
            internal_command_prefix, system_command_prefix
        )

        if ISATTY:
            self.bottom_bar: BottomBar | None = prompt_kwargs.get(
                "bottom_toolbar", BottomBar()
            )

            if self.bottom_bar is not None:
                self.bottom_bar.show_hidden_params = completer_kwargs.get(
                    "show_hidden_params", False
                )

            self.completer_kwargs = self._bootstrap_completer_kwargs(
                completer_cls, completer_kwargs
            )

            self.validator_kwargs = self._bootstrap_validator_kwargs(
                validator_cls, validator_kwargs
            )

        else:
            self.bottom_bar = None

        self.prompt_kwargs = self._bootstrap_prompt_kwargs(
            completer_cls, validator_cls, prompt_kwargs
        )

        self.repl_ctx = ReplContext(
            self.group_ctx,
            self.internal_commands_system,
            bottombar=self.bottom_bar,
            prompt_kwargs=self.prompt_kwargs,
            parent=get_current_repl_ctx(silent=True),
        )

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

    def _bootstrap_completer_kwargs(
        self, completer_cls: type[Completer] | None, completer_kwargs: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Generates bootstrap keyword arguments for initializing a
        `prompt_toolkit.completer.Completer` object, either using
        default values or user-defined values, if available.

        Parameters
        ----------
        completer_cls : a type of `Completer`
            A `prompt_toolkit.completion.Completer` type class.

        completer_kwargs : Dictionary of `str: Any` pairs
            A dictionary that contains values for keyword arguments supplied by the
            user, that to be passed to the `prompt_toolkit.completer.Completer` class.

        Returns
        -------
        Dictionary of `str: Any` pairs
            A dictionary that contains all the keyword arguments to be passed
            to the `prompt_toolkit.completer.Completer` class.
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
        `prompt_toolkit.validation.Validator` object, either
        using default values or user-defined values, if available.

        Parameters
        ----------
        validator_cls : A type of `Validator`
            A `prompt_toolkit.validation.Validator` type class

        validator_kwargs : Dictionary of `str: Any` pairs
            A dictionary that contains values for keyword arguments supplied by the
            user, that to be passed to the `prompt_toolkit.validation.Validator` class.

        Returns
        -------
        Dictionary of `str: Any` pairs
            A dictionary that contains all the keyword arguments to be passed
            to the `prompt_toolkit.validation.Validator` class.
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
        validator_cls: type[Validator] | None,
        prompt_kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generates bootstrap keyword arguments for initializing a
        `prompt_toolkit.PromptSession` object, either
        using default values or user-defined values, if available.

        Parameters
        ----------
        prompt_kwargs : Dictionary of `str: Any` pairs
            A dictionary that contains values for keyword arguments supplied by the
            user, that to be passed to the `prompt_toolkit.PromptSession` class.

        Returns
        -------
        Dictionary of `str: Any` pairs
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
            "complete_in_thread": True,
            "complete_while_typing": True,
            "validate_while_typing": True,
            "mouse_support": True,
            "refresh_interval": 0.15,
        }

        if self.bottom_bar:
            default_prompt_kwargs.update(bottom_toolbar=self.bottom_bar)

        if completer_cls is not None:
            default_prompt_kwargs.update(completer=completer_cls(**self.completer_kwargs))

        if validator_cls is not None:
            default_prompt_kwargs.update(validator=validator_cls(**self.validator_kwargs))

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
    group_ctx : `click.Context`
        The current click context object.

    prompt_kwargs : Dictionary of `str: Any` pairs
        Parameters passed to `prompt_toolkit.PromptSession`.
        These parameters configure the prompt appearance and behavior,
        such as prompt message, history, completion, etc.

    cls : `Repl` type class, default=`Repl`
        Repl class to use for the click_repl app. if `None`, the
        `click_repl._repl.Repl` class is used by default. This allows
        customization of the REPL behavior by providing a custom Repl subclass.

    **attrs : dict, optional
        Extra keyword arguments to be passed to the Repl class. These additional
        arguments can be used to further customize the behavior of the Repl class.

    Notes
    -----
    - You don't have to pass the `Completer` and `Validator` class, and their
    arguments via the `prompt_kwargs` dictionary. Pass them separately in the
    `completer_cls` and `validator_cls` arguments respectively.

    - Provide a text, a function, or a `click_repl.bottombar.BottomBar` object to
    determine the content that will be displayed in the bottom toolbar via the
    `bottom_toolbar` key in the `prompt_kwargs` dictionary. To disable the bottom
    toolbar, pass `None` as the value for this key.
    """

    cls(group_ctx, prompt_kwargs=prompt_kwargs, **attrs).loop()
