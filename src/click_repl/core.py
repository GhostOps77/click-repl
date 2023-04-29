import sys
import typing as t
from functools import wraps
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import ThreadedAutoSuggest

from ._completer import ClickCompleter
from ._globals import get_current_repl_ctx, push_context, pop_context

if t.TYPE_CHECKING:
    from click import Context  # noqa: F401
    from typing import Any, Dict, List, Optional, Callable, Generator, Union  # noqa: F401
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
        "group_ctx", "prompt_kwargs", "session", "_history", "get_command",
    )

    def __init__(self, group_ctx, prompt_kwargs=None, styles=None):
        # type: (Context, Optional[Dict[str, Any]], Optional[Dict[str, str]]) -> None

        group = group_ctx.command
        default_kwargs = {
            "history": InMemoryHistory(),
            "completer": ClickCompleter(group, group_ctx, styles=styles),
            "message": "> ",
            # "auto_suggest": ThreadedAutoSuggest(AutoSuggestFromHistory()),
            "complete_in_thread": True,
            "complete_while_typing": True,
            "mouse_support": True,
        }

        if isinstance(prompt_kwargs, dict):
            default_kwargs.update(prompt_kwargs)

        if sys.stdin.isatty():
            self.session = PromptSession(
                **default_kwargs
            )  # type: Optional[PromptSession[Dict[str, Any]]]
            self._history = self.session.history  # type: Union[History, List[str]]

            def get_command() -> str:
                return self.session.prompt()  # type: ignore[return-value, union-attr]

        else:
            self._history = []

            def get_command() -> str:
                inp = sys.stdin.readline()  # type: str
                self._history.append(inp)  # type: ignore[union-attr]
                return inp

            self.session = None

        self.get_command = get_command  # type: Callable[..., str]

        self.group_ctx = group_ctx
        self.prompt_kwargs = default_kwargs

    def __enter__(self):
        # type: () -> ClickReplContext
        push_context(self)
        return self

    def __exit__(self, *args):
        # type: (Any) -> None
        pop_context()

    @property
    def prompt_message(self) -> 'Optional[str]':
        if isinstance(self.session, PromptSession):
            return str(self.session.message)
        return None

    @prompt_message.setter
    def prompt_message(self, value):
        # type: (str) -> None
        if isinstance(self.session, PromptSession):
            self.session.message = value

    def to_info_dict(self):
        # type: () -> Dict[str, Any]
        return {
            'prompt_kwargs': self.prompt_kwargs,
            'group_ctx': self.group_ctx
        }

    def prompt_reset(self):
        # type: () -> None
        if self.session is not None:
            self.session = PromptSession(**self.prompt_kwargs)

    def history(self):
        # type: () -> Generator[str, None, None]
        if self.session is not None:
            _history = self._history.load_history_strings()  # type: ignore[union-attr]
        else:
            _history = reversed(self._history)  # type: ignore[arg-type]

        for i in _history:
            yield i


def pass_context(func):
    # type: (Callable[..., Any]) -> Callable[..., Any]
    @wraps(func)
    def decorator(*args, **kwargs):
        # type: (List[Any], Dict[str, Any]) -> Any
        return func(get_current_repl_ctx(), *args, **kwargs)

    return decorator
