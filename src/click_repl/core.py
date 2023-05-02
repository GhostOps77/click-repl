import sys
import typing as t
from prompt_toolkit import PromptSession

from ._globals import ISATTY, pop_context, push_context

if t.TYPE_CHECKING:
    from typing import List  # noqa: F401
    from typing import Any, Callable, Dict, Generator, Optional, Union

    from click import Context  # noqa: F401
    from prompt_toolkit.history import History  # noqa: F401

    # InfoDict = t.TypedDict(
    #     "InfoDict",
    #     {
    #         "prompt_kwargs": Dict[str, Any],
    #         "group_ctx": Context,
    #         "parent": ClickReplContext,
    #         "cli_args": List[str],
    #     },
    # )


class ClickReplContext:
    """Context object for REPL

    Keyword arguments:
    ---
    :param:`group_ctx` - Click Context object that belong to a Group
    :param:`validator` - Adds a Validator to the PromptSession
    :param:`prompt_kwargs` - Kwargs for PromptToolkit's `PromptSession` class
    :param:`styles` - Dictionary that denote the style schema of the prompt
    """

    __slots__ = (
        "group_ctx",
        "prompt_kwargs",
        "cli_args",
        "parent",
        "session",
        "_history",
        "get_command",
    )

    def __init__(
        self,
        group_ctx: "Context",
        prompt_kwargs: "Dict[str, Any]",
        cli_args: "List[str]",
        parent: "Optional[ClickReplContext]" = None,
    ) -> None:

        if ISATTY:
            self.session: "Optional[PromptSession[Dict[str, Any]]]" = PromptSession(
                **prompt_kwargs
            )
            self._history: "Union[History, List[str]]" = self.session.history

            def get_command() -> str:
                return self.session.prompt()  # type: ignore[no-any-return, return-value, union-attr]  # noqa: E501

        else:
            self._history = []

            def get_command() -> str:
                inp = sys.stdin.readline().strip()
                self._history.append(inp)  # type: ignore[union-attr]
                return inp

            self.session = None

        self.get_command: "Callable[[], str]" = get_command
        self.group_ctx = group_ctx
        self.prompt_kwargs = prompt_kwargs
        self.cli_args = cli_args
        self.parent = parent

    def __enter__(self) -> "ClickReplContext":
        push_context(self)
        return self

    def __exit__(self, *_: "Any") -> None:
        pop_context()

    @property
    def prompt_message(self) -> "Optional[str]":
        if isinstance(self.session, PromptSession):
            return str(self.session.message)
        return None

    @prompt_message.setter
    def prompt_message(self, value: str) -> None:
        if isinstance(self.session, PromptSession):
            self.session.message = value

    # def to_info_dict(self) -> "InfoDict":
    #     """Provides the most minimal info about the current REPL
    #     Return: Dictionary that has some instance variables and its values
    #     """

    #     return {
    #         "prompt_kwargs": self.prompt_kwargs,
    #         "group_ctx": self.group_ctx,
    #         "parent": self.parent,
    #         "cli_args": self.cli_args,
    #     }

    def prompt_reset(self) -> None:
        """Resets values of :class:`prompt_toolkit.session.PromptSession` to
        the provided `prompt_kwargs`, discarding any changes done to the
        :class:`prompt_toolkit.session.PromptSession` object"""

        if self.session is not None:
            self.session = PromptSession(**self.prompt_kwargs)

    def history(self) -> "Generator[str, None, None]":
        """Provides history of the past executed commands

        Yield: Executed command string from the history
        """

        if self.session is not None:
            _history = self._history.load_history_strings()  # type: ignore[union-attr]
        else:
            _history = reversed(self._history)  # type: ignore[arg-type]

        yield from _history
