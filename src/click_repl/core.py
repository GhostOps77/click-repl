"""
`click_repl.core`

Core functionality of the click-repl module.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Callable, Dict, Generator

import click
from click import Context
from prompt_toolkit import PromptSession
from typing_extensions import Final, TypeAlias, TypedDict

from . import _repl
from ._globals import ISATTY, _pop_context, _push_context
from ._internal_cmds import InternalCommandSystem
from .bottom_bar import BottomBar
from .parser import ReplParsingState

_PromptSession: TypeAlias = PromptSession[Dict[str, Any]]


class InfoDict(TypedDict):
    group_ctx: Context
    prompt_kwargs: dict[str, Any]
    session: _PromptSession | None
    internal_command_system: InternalCommandSystem
    parent: ReplContext | None
    _history: list[str]
    current_state: ReplParsingState | None
    bottombar: BottomBar | None


__all__ = ["ReplContext", "ReplCli"]


@contextmanager
def handle_lifetime(self_obj: ReplCli) -> Generator[None, None, None]:
    if self_obj.startup is not None:
        self_obj.startup()

    yield

    if self_obj.cleanup is not None:
        self_obj.cleanup()


class ReplContext:
    """
    Context object for the REPL (Read-Eval-Print-Loop).

    This class tracks the depth of nested REPLs, ensuring seamless navigation
    between different levels. It facilitates nested REPL scenarios, allowing
    multiple levels of interactive REPL sessions.

    Each REPL's properties are stored inside this context class, allowing them to
    be accessed and shared with their parent REPL.

    All the settings for each REPL session persist until the session is terminated.

    Parameters
    ----------
    group_ctx : `click.Context`
        The click context object that belong to the CLI/parent Group.

    internal_command_system : `InternalCommandSystem`
        The `InternalCommandSystem` object that holds information about
        the internal commands and their prefixes.

    bottom_bar : `BottomBar`
        The `BottomBar` object that controls the text that should be displayed in the
        bottom toolbar of the `prompt_toolkit.PromptSession` object.

    prompt_kwargs : A dictionary of `str: Any` pairs
        The extra Keyword arguments for `prompt_toolkit.PromptSession` class.

    styles : A dictionary of `str: str` pairs
        A dictionary that denote the style schema of the prompt.
    """

    __slots__ = (
        "group_ctx",
        "prompt_kwargs",
        "bottombar",
        "parent",
        "session",
        "internal_command_system",
        "_history",
        "current_state",
    )

    def __init__(
        self,
        group_ctx: Context,
        internal_command_system: InternalCommandSystem,
        bottombar: BottomBar | None = None,
        prompt_kwargs: dict[str, Any] = {},
        parent: ReplContext | None = None,
    ) -> None:
        session: _PromptSession | None

        if ISATTY:
            session = PromptSession(**prompt_kwargs)
            if bottombar is not None:
                bottombar.current_repl_ctx = self

        else:
            session = None

        self.session = session
        self.bottombar = bottombar

        self._history: list[str] = []
        self.internal_command_system = internal_command_system
        self.group_ctx: Final[Context] = group_ctx
        self.prompt_kwargs = prompt_kwargs
        self.parent: Final[ReplContext | None] = parent
        self.current_state: ReplParsingState | None = None

    def __enter__(self) -> ReplContext:
        _push_context(self)
        return self

    def __exit__(self, *_: Any) -> None:
        _pop_context()

    @property
    def prompt_message(self) -> str | None:
        """
        The message displayed for every prompt input in the REPL.

        Returns
        -------
        str or None
            String if `sys.stdin.isatty()` is `True`, else `None`
        """
        if ISATTY and self.session is not None:
            # assert self.session is not None
            return str(self.session.message)
        return None

    @prompt_message.setter
    def prompt_message(self, value: str) -> None:
        if ISATTY and self.session is not None:
            # assert self.session is not None
            self.session.message = value

    def to_info_dict(self) -> InfoDict:
        """
        Provides the most minimal info about the current REPL

        Returns
        -------
        A dictionary that has the instance variables and its values.
        """

        res: InfoDict = {
            "group_ctx": self.group_ctx,
            "prompt_kwargs": self.prompt_kwargs,
            "internal_command_system": self.internal_command_system,
            "session": self.session,
            "parent": self.parent,
            "_history": self._history,
            "current_state": self.current_state,
            "bottombar": self.bottombar,
        }

        return res

    def session_reset(self) -> None:
        """
        Resets values of `prompt_toolkit.session.PromptSession` to
        the provided `prompt_kwargs`, discarding any changes done to the
        `prompt_toolkit.session.PromptSession` object
        """

        if ISATTY and self.session is not None:
            # assert self.session is not None
            self.session = PromptSession(**self.prompt_kwargs)

    def history(self) -> Iterator[str]:
        """
        Generates the history of past executed commands.

        Yields
        ------
        str
            The executed command string from the history,
            in chronological order from most recent to oldest.
        """

        if ISATTY and self.session is not None:
            # assert self.session is not None
            yield from self.session.history.load_history_strings()

        else:
            yield from reversed(self._history)

    def update_state(self, state: ReplParsingState) -> None:
        self.current_state = state


class ReplCli(click.Group):
    """
    Custom `click.Group` subclass for invoking the REPL.

    This class extends the functionality of the `click.Group`
    class and is designed to be used as a wrapper to
    automatically invoke the `click_repl._repl.repl()`
    function when the group is invoked without any sub-command.

    Parameters
    ----------
    prompt : str, default="> "
        The message that should be displayed for every prompt input.

    startup : A function that takes and returns nothing, optional
        The function that gets called before invoking the REPL.

    cleanup : A function that takes and returns nothing, optional
        The function that gets invoked after exiting out of the REPL.

    repl_kwargs : A dictionary of `str: Any` pairs
        The keyword arguments that needs to be sent to the `repl()` function.

    **attrs : dict, optional
        Extra keyword arguments that need to be passed to the `click.Group` class.
    """

    def __init__(
        self,
        prompt: str = "> ",
        startup: Callable[[], None] | None = None,
        cleanup: Callable[[], None] | None = None,
        repl_kwargs: dict[str, Any] = {},
        **attrs: Any,
    ) -> None:
        attrs["invoke_without_command"] = True
        super().__init__(**attrs)

        self.prompt = prompt
        self.startup = startup
        self.cleanup = cleanup

        repl_kwargs.setdefault("prompt_kwargs", {}).update({"message": prompt})

        self.repl_kwargs = repl_kwargs

    def invoke(self, ctx: Context) -> Any:
        if ctx.invoked_subcommand or ctx.protected_args:
            return super().invoke(ctx)

        with handle_lifetime(self):
            return_val = super().invoke(ctx)
            _repl.repl(ctx, **self.repl_kwargs)
            return return_val
