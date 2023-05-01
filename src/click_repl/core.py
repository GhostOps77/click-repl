import sys
import typing as t
from functools import wraps

from prompt_toolkit import PromptSession

from ._globals import get_current_repl_ctx, pop_context, push_context

if t.TYPE_CHECKING:
    from typing import (
        Any,
        Callable,
        Dict,
        Generator,
        List,  # noqa: F401
        Optional,
        Union,
    )

    from click import Context  # noqa: F401
    from prompt_toolkit.history import History  # noqa: F401


class ClickReplContext:
    """Context object for REPL

    Keyword arguments:
    group_ctx -- Click Context object that belong to a Group
    enable_validator -- Adds a Validator to the PromptSession
    prompt_kwargs -- Kwargs for PromptToolkit's `PromptSession` class
    styles -- Dictionary that denote the style schema of the prompt
    Return: None
    """

    __slots__ = (
        "group_ctx",
        "prompt_kwargs",
        "session",
        "_history",
        "get_command",
    )

    def __init__(self, group_ctx: "Context", prompt_kwargs: "Dict[str, Any]") -> None:

        self.group_ctx = group_ctx
        self.prompt_kwargs = prompt_kwargs

        if sys.stdin.isatty():
            self.session: "Optional[PromptSession[Dict[str, Any]]]" = PromptSession(
                **prompt_kwargs
            )
            self._history: "Union[History, List[str]]" = self.session.history

            def get_command() -> str:
                return self.session.prompt()  # type: ignore[return-value, union-attr]

        else:
            self._history = []

            def get_command() -> str:
                inp = sys.stdin.readline()
                self._history.append(inp)  # type: ignore[union-attr]
                return inp

            self.session = None

        self.get_command: "Callable[..., str]" = get_command

    def __enter__(self) -> "ClickReplContext":
        push_context(self)
        return self

    def __exit__(self, *args: "Any") -> None:
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

    def to_info_dict(self) -> "Dict[str, Any]":
        return {"prompt_kwargs": self.prompt_kwargs, "group_ctx": self.group_ctx}

    def prompt_reset(self) -> None:
        if self.session is not None:
            self.session = PromptSession(**self.prompt_kwargs)

    def history(self) -> "Generator[str, None, None]":
        if self.session is not None:
            _history = self._history.load_history_strings()  # type: ignore[union-attr]
        else:
            _history = reversed(self._history)  # type: ignore[arg-type]

        yield from _history


def pass_context(func: "Callable[..., Any]") -> "Callable[..., Any]":
    @wraps(func)
    def decorator(*args, **kwargs):
        # type: (List[Any], Dict[str, Any]) -> Any
        return func(get_current_repl_ctx(), *args, **kwargs)

    return decorator
