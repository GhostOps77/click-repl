"""
Core functionalities for managing context of the click_repl app.
"""

from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Dict, Generator, TypeVar

from click import Context
from prompt_toolkit import PromptSession
from typing_extensions import Concatenate, Final, ParamSpec, TypeAlias, TypedDict

from .bottom_bar import BottomBar
from .globals_ import ISATTY, _pop_context, _push_context, get_current_repl_ctx
from .internal_commands import InternalCommandSystem
from .parser import ReplInputState

if TYPE_CHECKING:
    from prompt_toolkit.formatted_text import AnyFormattedText


P = ParamSpec("P")
R = TypeVar("R")
F = TypeVar("F", bound=Callable[..., Any])


__all__ = ["ReplContext"]


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
    Context object for the REPL.

    This class tracks the depth of nested REPLs, ensuring seamless navigation
    between different levels. It facilitates nested REPL scenarios, allowing
    multiple levels of interactive REPL sessions.

    Each REPL's properties are stored inside this context class, allowing them to
    be accessed and shared with their parent REPL.

    All the settings for each REPL session persist until the session is terminated.

    Parameters
    ----------
    group_ctx
        The :class:`~click.Context` object that belong to the CLI/parent Group.

    internal_command_system
        The :class:`~click_repl._internal_commands.InternalCommandSystem` object that
        holds information about the internal commands and their prefixes.

    bottom_bar
        The :class:`~click_repl.bottom_bar.BottomBar` object that controls the text
        that should be displayed in the bottom toolbar of the
        :class:`~prompt_toolkit.PromptSession` object.

    prompt_kwargs
        Extra keyword arguments for :class:`~prompt_toolkit.PromptSession` class.

    parent
        Parent :class:`~click_repl.core.ReplContext` object of the parent REPL session.
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
        bottombar: AnyFormattedText | BottomBar = None,
        prompt_kwargs: dict[str, Any] = {},
        parent: ReplContext | None = None,
    ) -> None:
        """
        Initialize the `ReplContext` class.
        """
        session: _PromptSession | None

        if ISATTY:
            session = PromptSession(**prompt_kwargs)

        else:
            session = None

        self.session = session
        self.bottombar = bottombar

        self._history: list[str] = []
        self.internal_command_system = internal_command_system
        self.group_ctx: Final[Context] = group_ctx
        self.prompt_kwargs = prompt_kwargs
        self.parent: Final[ReplContext | None] = parent
        self.current_state: ReplInputState | None = None

    def __enter__(self) -> ReplContext:
        _push_context(self)
        return self

    def __exit__(self, *_: Any) -> None:
        _pop_context()

    @property
    def prompt(self) -> AnyFormattedText:
        """
        The message displayed for every prompt input in the REPL.

        Returns
        -------
        :obj:`~prompt_toolkit.formatted_text.AnyFormattedText`
            Returns prompt object if :func:`~sys.stdin.isatty` is ``True``, else ``None``
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
        Provides the most minimal info about the current REPL.

        Returns
        -------
        ReplContextInfoDict
            A dictionary that has the instance variables and it's values.
        """

        res: ReplContextInfoDict = {
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
        Resets values of :class:`~prompt_toolkit.session.PromptSession` to
        the provided ``prompt_kwargs``, discarding any changes done to the
        :class:`~prompt_toolkit.session.PromptSession` object.
        """

        if ISATTY and self.session is not None:
            self.session = PromptSession(**self.prompt_kwargs)

    def update_state(self, state: ReplInputState) -> None:
        """
        Updates the current input state of the repl.

        Parameters
        ----------
        state
            :class:`~click_repl.parser.ReplInputState` object that keeps track
            of the current input state.
        """
        self.current_state = state

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
    func: Callable[Concatenate[ReplContext | None, P], R],
) -> Callable[P, R]:
    """
    Decorator that marks a callback function to receive the current
    REPL context object as it's first argument.

    Parameters
    ----------
    func
        The callback function to pass context as it's first parameter.

    Returns
    -------
    Callable[P,R]
        The decorated callback function that receives the current REPL
        context object as it's first argument.
    """

    @wraps(func)
    def decorator(*args: P.args, **kwargs: P.kwargs) -> R:
        return func(get_current_repl_ctx(), *args, **kwargs)

    return decorator
