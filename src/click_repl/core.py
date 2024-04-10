"""
Core functionality of the module.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generator

from click import Context
from prompt_toolkit import PromptSession
from typing_extensions import Final

from ._globals import ISATTY, _pop_context, _push_context
from ._internal_command import InternalCommandSystem
from .bottom_bar import BottomBar
from .parser import ReplParsingState

if TYPE_CHECKING:
    from ._types import ReplContextInfoDict, _PromptSession

__all__ = ["ReplContext"]


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
        The extra keyword arguments for :class:`~prompt_toolkit.PromptSession` class.

    styles
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
        """
        Initialize the `ReplContext` class.
        """
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
        :class:`str` | None
            Prompt string if :func:`~sys.stdin.isatty` is ``True``, else ``None``
        """
        if ISATTY and self.session is not None:
            return str(self.session.message)
        return None

    @prompt_message.setter
    def prompt_message(self, value: str) -> None:
        if ISATTY and self.session is not None:
            self.session.message = value

    def to_info_dict(self) -> ReplContextInfoDict:
        """
        Provides the most minimal info about the current REPL.

        Returns
        -------
        ReplContextInfoDict
            A dictionary that has the instance variables and its values.
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

    def update_state(self, state: ReplParsingState) -> None:
        self.current_state = state
