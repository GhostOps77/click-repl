"""
Core functionality of the REPL.
"""

from __future__ import annotations

import sys
import traceback
import warnings
from contextlib import contextmanager
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Generator, Sequence

import click
from click import Group

from ._compat import split_arg_string
from .click_custom.shell_completion import _expand_args, _generate_next_click_ctx
from .core import ReplContext
from .exceptions import ExitReplException, InternalCommandException, PrefixNotFound
from .globals_ import ISATTY, get_current_repl_ctx
from .internal_commands import InternalCommandSystem
from .utils import print_error

if TYPE_CHECKING:
    from click import Context
    from prompt_toolkit.completion import Completer
    from prompt_toolkit.formatted_text import AnyFormattedText
    from prompt_toolkit.validation import Validator


if ISATTY:
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.styles import Style, merge_styles

    from .bottom_bar import BottomBar
    from .completer import ClickCompleter
    from .styles import DEFAULT_PROMPTSESSION_STYLE_CONFIG
    from .validator import ClickValidator


__all__ = ["Repl", "repl", "ReplGroup", "register_repl"]


_MISSING = object()


class Repl:
    """
    Executes the REPL with proper necessary arrangements.

    Parameters
    ----------
    ctx
        The root/parent/CLI group's context  object.

    prompt_kwargs
        Keyword arguments passed to the :class:`~prompt_toolkit.shortcuts.PromptSession` class.

    completer_cls
        Completer type class to generate :class:`~prompt_toolkit.completion.Completion
        objects for auto-completion.
        :class:`~click_repl.completer.ClickCompleter` class is used by default.

    validator_cls
        Validator class to display error messages in the validator bar
        during input validation.
        :class:`~click_repl.validator.ClickValidator` class is used by default.

    completer_kwargs
        Keyword arguments passed to the constructor of ``completer_cls`` class.

    validator_kwargs
        Keyword arguments passed to the constructor of ``validator_cls`` class.

    internal_command_prefix
        Prefix that triggers internal commands within the REPL.

    system_command_prefix
        Prefix that triggers system commands within the REPL.

    Note
    ----
    You don't have to pass the :class:`~prompt_toolkit.completion.Completer` and
    :class:`~prompt_toolkit.validation.Validator` objects via ``prompt_kwargs``.
    But if its still done, then the REPL uses the completer and validator from it.
    """

    def __init__(
        self,
        ctx: Context,
        prompt_kwargs: dict[str, Any] = {},
        completer_cls: type[Completer] = _MISSING,  # type:ignore[assignment]
        validator_cls: type[Validator] | None = _MISSING,  # type:ignore[assignment]
        completer_kwargs: dict[str, Any] = {},
        validator_kwargs: dict[str, Any] = {},
        internal_command_prefix: str | None = ":",
        system_command_prefix: str | None = "!",
    ) -> None:
        """
        Initializes the `Repl` class.
        """

        # Check if there's a parent command, if its there, then use it.
        if ctx.parent is not None and not isinstance(ctx.command, Group):
            ctx = ctx.parent

        ctx.protected_args = []

        self.group_ctx: Context = ctx
        """click context of the parent/CLI group the to retrieve its subcommands."""

        self.internal_commands_system: InternalCommandSystem = InternalCommandSystem(
            internal_command_prefix, system_command_prefix
        )
        """Handles and executes internal commands that are invoked in repl."""

        self.bottom_bar: AnyFormattedText | BottomBar = None
        """
        Text or callable returning text, that should be displayed in the
        bottom toolbar of the :class:`~prompt_toolkit.shortcuts.PromptSession` object.

        Alternatively, it can be a :class:`~.bottom_bar.BottomBar` object
        to dynamically adjust the command description displayed in the
        bottom bar based on the user's current input state.
        """

        if ISATTY:
            bottom_bar: AnyFormattedText | BottomBar = prompt_kwargs.get(
                "bottom_toolbar", BottomBar()
            )

            if isinstance(bottom_bar, BottomBar):
                bottom_bar.show_hidden_params = completer_kwargs.get(
                    "show_hidden_params", False
                )

            elif bottom_bar is not None:
                raise TypeError(
                    "Expected bottom_bar to be a type of AnyFormattedText, or BottomBar, "
                    f"but got {type(bottom_bar).__name__}"
                )

            self.bottom_bar = bottom_bar

        prompt_kwargs = self.get_default_prompt_kwargs(
            completer_cls,
            completer_kwargs,
            validator_cls,
            validator_kwargs,
            prompt_kwargs,
        )

        self.repl_ctx: ReplContext = ReplContext(
            self.group_ctx,
            self.internal_commands_system,
            bottombar=self.bottom_bar,
            prompt_kwargs=prompt_kwargs,
            parent=get_current_repl_ctx(silent=True),
        )
        """Context object for the current REPL session."""

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

        self._get_command: Callable[[], str] = _get_command

    def get_command(self) -> str:
        """
        Retrieves input for the REPL.

        Returns
        -------
        str
            Input text from REPL prompt.
        """
        # "split_arg_string" is called here to strip out shell comments.
        return " ".join(split_arg_string(self._get_command()))

    def get_default_completer_kwargs(
        self, completer_cls: type[Completer] | None, completer_kwargs: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Generates default keyword arguments for initializing a
        :class:`~prompt_toolkit.completion.Completer` object, either
        using default values or user-defined values, if available.

        Parameters
        ----------
        completer_cls
            A completer class.

        completer_kwargs
            Keyword arguments passed to the ``completer_cls`` class.

        Returns
        -------
        dict[str,Any]
            Keyword arguments that should be passed to the
            :class:`~prompt_toolkit.completion.Completer` class.
        """

        if not ISATTY:
            return {}

        default_completer_kwargs = {
            "group_ctx": self.group_ctx,
            "internal_commands_system": self.internal_commands_system,
            "bottom_bar": self.bottom_bar,
        }

        default_completer_kwargs.update(completer_kwargs)
        return default_completer_kwargs

    def get_default_validator_kwargs(
        self, validator_cls: type[Validator] | None, validator_kwargs: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Generates default keyword arguments for initializing a
        :class:`~prompt_toolkit.validation.Validator` object, either
        using default values or user-defined values, if available.

        Parameters
        ----------
        validator_cls
            A validator class.

        validator_kwargs
            Keyword arguments passed to the ``validator_cls`` class.

        Returns
        -------
        dict[str,Any]
            Keyword arguments that should be passed to the ``validator_cls`` class.
        """

        if not ISATTY or validator_cls is None:
            # If the standard input is not a TTY device, there is no need
            # to generate any keyword arguments for rendering. In this case,
            # an empty dictionary is returned.
            return {}

        if validator_cls is not None:
            default_validator_kwargs = {
                "group_ctx": self.group_ctx,
                "internal_commands_system": self.internal_commands_system,
            }

            default_validator_kwargs.update(validator_kwargs)
            return default_validator_kwargs

    def get_default_prompt_kwargs(
        self,
        completer_cls: type[Completer],
        completer_kwargs: dict[str, Any],
        validator_cls: type[Validator] | None,
        validator_kwargs: dict[str, Any],
        prompt_kwargs: dict[str, Any],
        style_config_dict: dict[str, str] = {},
    ) -> dict[str, Any]:
        """
        Generates default keyword arguments for initializing a
        :class:`~prompt_toolkit.shortcuts.PromptSession` object, either
        using default values or user-defined values, if available.

        Parameters
        ----------
        completer_cls
            A completer class.

        completer_kwargs
            Keyword arguments passed to the ``completer_cls`` class.

        validator_cls
            A validator class.

        validator_kwargs
            Keyword arguments passed to the ``validator_cls`` class.

        prompt_kwargs
            Keyword arguments passed to the
            :class:`~prompt_toolkit.shortcuts.PromptSession` class.

        style_config_dict
            Style configuration for the REPL.

        Returns
        -------
        dict[str,Any]
            Keyword arguments that should be passed to the
            :class:`~prompt_toolkit.shortcuts.PromptSession` class.
        """

        if not ISATTY:
            return {}

        if completer_cls is None:
            raise ValueError("'completer_cls' cannot be None.")

        elif completer_cls == _MISSING:
            completer_cls = ClickCompleter

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

        prompt_kwargs.setdefault(
            "completer",
            completer_cls(
                **self.get_default_completer_kwargs(completer_cls, completer_kwargs)
            ),
        )

        if validator_cls == _MISSING:
            validator_cls = ClickValidator

        if validator_cls is not None:
            prompt_kwargs.setdefault(
                "validator",
                validator_cls(
                    **self.get_default_validator_kwargs(validator_cls, validator_kwargs)
                ),
            )

        style_dict = DEFAULT_PROMPTSESSION_STYLE_CONFIG.copy()
        style_dict.update(style_config_dict)

        styles = Style.from_dict(style_dict)

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
        Executes commands received from the REPL.

        Parameters
        ----------
        command
            The command string to be parsed and executed.
        """

        if not command:
            return

        try:
            self.repl_ctx.internal_command_system.execute(command.lower())

        except PrefixNotFound:
            self.execute_click_command(command)

    def execute_click_command(self, command: str | Sequence[str]) -> None:
        """
        Executes click command received from the REPL.

        Parameters
        ----------
        command
            The command string to be parsed and executed.
        """

        if isinstance(command, str):
            command = split_arg_string(command)

        command = _expand_args(command)
        ctx, _ = _generate_next_click_ctx(self.group_ctx, tuple(command))
        ctx.command.invoke(ctx)

    def loop(self) -> None:
        """Starts the REPL."""

        with self.repl_ctx:
            while True:
                try:
                    if ISATTY and isinstance(self.bottom_bar, BottomBar):
                        # Resetting the toolbar to clear its text content,
                        # ensuring that it doesn't display command info from
                        # the previously executed command.
                        self.bottom_bar.reset_state()

                    command = self._get_command().strip()

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

                except (click.exceptions.Exit, SystemExit):
                    continue

                except click.UsageError as e:
                    command_name = ""
                    if e.ctx is not None and e.ctx.command.name is not None:
                        command_name = f"{e.ctx.command.name}: "

                    print_error(command_name + e.format_message())

                except click.ClickException as e:
                    e.show()

                except ExitReplException:
                    break

                except InternalCommandException as e:
                    print_error(f"{type(e).__name__}: {e}")

                except Exception:
                    traceback.print_exc()


class ReplGroup(click.Group):
    """
    Custom :class:`~click.Group` subclass for initialing the REPL.

    This class extends the functionality of the :class:`~click.Group`
    class and is designed to be used as a wrapper to automatically
    invoke the :func:`~.repl` function when the group is invoked
    without any sub-command.

    Parameters
    ----------
    prompt
        The prompt text for the REPL.

    startup
        The callback function that gets called before invoking the REPL.

    cleanup
        The callback function that gets invoked after exiting the REPL.

    repl_kwargs
        The keyword arguments that needs to be sent to the :func:`~.repl` function.

    **attrs
        Extra keyword arguments to be passed to the :class:`click.Group` class.
    """

    def __init__(
        self,
        prompt: str = "> ",
        startup: Callable[[], None] | None = None,
        cleanup: Callable[[], None] | None = None,
        repl_kwargs: dict[str, Any] = {},
        **attrs: Any,
    ) -> None:
        """
        Initializes the `ReplGroup` class.
        """

        attrs["invoke_without_command"] = True
        super().__init__(**attrs)

        self.prompt = prompt
        """The prompt text for the REPL."""

        self.startup = startup
        """The callback function that gets called before invoking the REPL."""

        self.cleanup = cleanup
        """The callback function that gets invoked after exiting the REPL."""

        repl_kwargs.setdefault("prompt_kwargs", {}).update({"message": prompt})

        self.repl_kwargs = repl_kwargs
        """
        The keyword arguments that needs to be sent to the :func:`~.repl` function.
        """

    @contextmanager
    def _handle_lifetime(self) -> Generator[None, None, None]:
        if self.startup is not None:
            self.startup()

        yield

        if self.cleanup is not None:
            self.cleanup()

    def invoke(self, ctx: Context) -> Any:
        if ctx.invoked_subcommand or ctx.protected_args:
            return super().invoke(ctx)

        with self._handle_lifetime():
            return_val = super().invoke(ctx)
            repl(ctx, **self.repl_kwargs)
            return return_val


def repl(
    group_ctx: Context,
    prompt_kwargs: dict[str, Any] = {},
    cls: type[Repl] = Repl,
    **attrs: Any,
) -> None:
    """
    Starts an Interactive Shell where all subcommands are available.

    If stdin is not a TTY, no prompt will be printed, but only subcommands
    can be read from stdin.

    Parameters
    ----------
    group_ctx
        The current click context object.

    prompt_kwargs
        Parameters that should be passed to :class:`~prompt_toolkit.shortcuts.PromptSession`.
        These parameters configure the prompt appearance and behavior,
        such as prompt message, history, completion, etc.

    cls
        Repl class to use for the click_repl app. if :obj:`None`, the
        :class:`~.Repl` class is used by default. This allows customization
        of the REPL behavior by providing a custom Repl subclass.

    **attrs
        Extra keyword arguments to be passed to the Repl class. These additional
        arguments can be used to further customize the behavior of the Repl class.

    Notes
    -----
    * You don't have to pass the :class:`~prompt_toolkit.completion.Completer` and
      :class:`~prompt_toolkit.validation.Validator` class, and their arguments via the
      ``prompt_kwargs`` dictionary. Pass them separately in the ``completer_cls`` and
      ``validator_cls`` arguments respectively.

    * Provide a text, a function, or a :class:`~click_repl.bottom_bar.BottomBar` object
      to determine the content that will be displayed in the bottom toolbar via the
      ``bottom_toolbar`` key in the ``prompt_kwargs`` dictionary. To disable the bottom
      toolbar, pass :obj:`None` as the value for this key.
    """

    if not attrs.pop("allow_internal_commands", True):
        warnings.warn(
            "'allow_internal_commands=False' in repl() is deprecated. "
            "Use 'internal_command_prefix=None' instead."
        )
        attrs["internal_command_prefix"] = None

    if not attrs.pop("allow_system_commands", True):
        warnings.warn(
            "'allow_internal_commands=False' in repl() is deprecated. "
            "Use 'internal_command_prefix=None' instead."
        )
        attrs["system_command_prefix"] = None

    cls(group_ctx, prompt_kwargs=prompt_kwargs, **attrs).loop()


def register_repl(
    group: Group | None = None,
    *,
    name: str = "repl",
    remove_command_before_repl: bool = False,
) -> Callable[[Group], Group] | Group:
    """
    Decorator that registers :func:`~click_repl._repl.repl` as a sub-command
    named ``name`` within the ``group``.

    Parameters
    ----------
    group
        The parent click group object to which the REPL command
        will be registered.

    name
        The name of the repl command to be in the given ``group``.

    remove_command_before_repl
        Determines whether to remove the REPL command from the group,
        before its execution or not.

    Returns
    -------
    Callable[[Group],Group] | Group
        The same ``group`` or a callback that returns the same group with
        the REPL command registered to it.

    Raises
    ------
    TypeError
        If the given ``group`` is not an instance of :class:`~click.Group`.
    """

    def decorator(_group: Group) -> Group:
        nonlocal group

        if group is not None:
            _group = group

        if not isinstance(_group, Group):
            raise TypeError(
                "Expected 'group' to be a type of click.Group, "
                f"but got {type(_group).__name__}"
            )

        if name in _group.commands:
            raise ValueError(f"Command {name!r} already exists in Group {_group.name!r}")

        @wraps(repl)
        def _repl(ctx: click.Context, *args: Any, **kwargs: Any) -> None:
            if remove_command_before_repl:
                _group.commands.pop(name)

            repl(ctx, *args, **kwargs)
            _group.command(name=name)(click.pass_context(_repl))

        _group.command(name=name)(click.pass_context(_repl))

        return _group

    if group is None:
        return decorator
    return decorator(group)
