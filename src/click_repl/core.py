"""
Core functionalities for managing context of the click_repl app.
"""

from __future__ import annotations

from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Final,
    Generator,
    TypedDict,
    TypeVar,
)

from click import Context
from prompt_toolkit import PromptSession
from typing_extensions import Concatenate, ParamSpec, TypeAlias

from ._ctx_stack import _pop_context, _push_context
from .bottom_bar import BottomBar
from .globals_ import ISATTY, get_current_repl_ctx
from .internal_commands import InternalCommandSystem
from .parser import ReplInputState

if TYPE_CHECKING:
    from prompt_toolkit.formatted_text import AnyFormattedText


P = ParamSpec("P")
R = TypeVar("R")
F = TypeVar("F", bound=Callable[..., Any])


__all__ = ["ReplContext", "pass_context"]


_PromptSession: TypeAlias = PromptSession[Dict[str, Any]]


class ReplContextInfoDict(TypedDict):
    group_ctx: Context
    prompt_kwargs: dict[str, Any]
    session: _PromptSession | None
    internal_command_system: InternalCommandSystem
    parent: ReplContext | None
    _history: list[str]
    current_state: ReplInputState | None
    bottombar: AnyFormattedText | BottomBar


class ReplContext:
    """
    Context object for the REPL sessions.

    This class tracks the depth of nested REPLs, ensuring seamless navigation
    between different levels. It facilitates nested REPL scenarios, allowing
    multiple levels of interactive REPL sessions.

    Each REPL's properties are stored inside this context class, allowing them to
    be accessed and shared with their parent REPL.

    All the settings for each REPL session persist until the session is terminated.

    Parameters
    ----------
    group_ctx
        The click context object that belong to the CLI/parent Group.

    internal_command_system
        Holds information about the internal commands and their prefixes.

    bottom_bar
        Text or callable returning text, that should be displayed in the
        bottom toolbar of the :class:`~prompt_toolkit.shortcuts.PromptSession` object.

        Alternatively, it can be a :class:`~.bottom_bar.BottomBar` object
        to dynamically adjust the command description displayed in the
        bottom bar based on the user's current input state.

    prompt_kwargs
        Extra keyword arguments for :class:`~prompt_toolkit.shortcuts.PromptSession` class.

    parent
        REPL Context object of the parent REPL session, if exists. Otherwise, :obj:`None`.
    """

    __slots__ = (
        "group_ctx",
        "prompt_kwargs",
        "bottom_bar",
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
        bottombar: AnyFormattedText | BottomBar = None,
        prompt_kwargs: dict[str, Any] = {},
        parent: ReplContext | None = None,
    ) -> None:
        """
        Initializes the `ReplContext` class.
        """
        session: _PromptSession | None

        if ISATTY:
            session = PromptSession(**prompt_kwargs)

        else:
            session = None

        self.group_ctx: Final[Context] = group_ctx
        """The click context object that belong to the CLI/parent Group."""

        self.session = session
        """Object that's responsible for managing and executing the REPL."""

        self.bottom_bar = bottombar
        """
        Text or callable returning text, that should be displayed in the
        bottom toolbar of the :class:`~prompt_toolkit.shortcuts.PromptSession` object.

        Alternatively, it can be a :class:`~.bottom_bar.BottomBar` object
        to dynamically adjust the command description displayed in the
        bottom bar based on the user's current input state.
        """

        self.internal_command_system = internal_command_system
        """Holds information about the internal commands and their prefixes."""

        self._history: list[str] = []
        """
        History of past executed commands.

        Used only when :func:`~sys.stdin.isatty` is :obj:`False`.
        """

        self.prompt_kwargs = prompt_kwargs
        """
        Extra keyword arguments for
        :class:`~prompt_toolkit.shortcuts.PromptSession` class.
        """

        self.parent: Final[ReplContext | None] = parent
        """
        REPL Context object of the parent REPL session, if exists.
        Otherwise, :obj:`None`.
        """

        self.current_state: ReplInputState | None = None
        """Current input state of the commands and their parameters in the REPL."""

    def __enter__(self) -> ReplContext:
        _push_context(self)
        return self

    def __exit__(self, *_: Any) -> None:
        _pop_context()

    @property
    def prompt(self) -> AnyFormattedText:
        """
        The prompt text of the REPL field.

        Returns
        -------
        prompt_toolkit.formatted_text.AnyFormattedText
            The prompt object if :func:`~sys.stdin.isatty` is :obj:`True`,
            else :obj:`None`.
        """
        if ISATTY and self.session is not None:
            return self.session.message
        return None

    @prompt.setter
    def prompt(self, value: AnyFormattedText) -> None:
        if ISATTY and self.session is not None:
            self.session.message = value

    def to_info_dict(self) -> ReplContextInfoDict:
        """
        Provides a dictionary with minimal info about the current REPL.

        Returns
        -------
        ReplContextInfoDict
            A dictionary that has the instance variables and their values.
        """

        res: ReplContextInfoDict = {
            "group_ctx": self.group_ctx,
            "prompt_kwargs": self.prompt_kwargs,
            "internal_command_system": self.internal_command_system,
            "session": self.session,
            "parent": self.parent,
            "_history": self._history,
            "current_state": self.current_state,
            "bottombar": self.bottom_bar,
        }

        return res

    def session_reset(self) -> None:
        """
        Resets values of :class:`~prompt_toolkit.session.PromptSession` to
        the provided :attr:`~.prompt_kwargs`, discarding any changes done to the
        :class:`~prompt_toolkit.session.PromptSession` object.
        """

        if ISATTY and self.session is not None:
            self.session = PromptSession(**self.prompt_kwargs)

    def update_state(self, state: ReplInputState) -> None:
        """
        Updates the current input state of the REPL in itself,
        and in :attr:`~.ReplContext.bottom_bar`.

        Parameters
        ----------
        state
            A ReplInputState object that keeps track of the current input state.
        """

        if self.current_state == state:
            return

        self.current_state = state

        if ISATTY and isinstance(self.bottom_bar, BottomBar):
            self.bottom_bar.update_state(state)

    def history(self) -> Generator[str, None, None]:
        """
        Generates the history of past executed commands.

        Yields
        ------
        str
            The executed command string from the history,
            in chronological order from most recent to oldest.
        """

        if ISATTY and self.session is not None:
            yield from self.session.history.load_history_strings()

        else:
            yield from reversed(self._history)


def pass_context(
    func: Callable[Concatenate[ReplContext, P], R],
) -> Callable[P, R]:
    """
    Decorator that marks a callback function to receive the current
    REPL context object as its first argument.

    Parameters
    ----------
    func
        The callback function to pass context as its first parameter.

    Returns
    -------
    Callable[P,R]
        The decorated callback function that receives the current REPL
        context object as its first argument.
    """

    @wraps(func)
    def decorator(*args: P.args, **kwargs: P.kwargs) -> R:
        return func(get_current_repl_ctx(), *args, **kwargs)

    return decorator
