import sys
import typing as t
from functools import wraps
from prompt_toolkit import PromptSession

from ._globals import get_current_click_repl_context, push_context, pop_context

if t.TYPE_CHECKING:
    from click import Context  # noqa: F401
    from typing import Any, Dict, List, Optional, Callable, Generator, Union  # noqa: F401
    from prompt_toolkit.history import History  # noqa: F401


class ClickReplContext:
    __slots__ = (
        "group_ctx", "isatty", "prompt_kwargs", "session", "_history", "get_command",
    )

    def __init__(self, group_ctx, isatty, prompt_kwargs):
        # type: (Context, bool, Dict[str, Any]) -> None
        self.group_ctx = group_ctx
        self.prompt_kwargs = prompt_kwargs
        self.isatty = isatty

        if isatty:
            self.session = PromptSession(
                **prompt_kwargs
            )  # type: Optional[PromptSession[Dict[str, Any]]]
            self._history = self.session.history  # type: Union[History, List[str]]

            def get_command():
                # type: () -> str
                return self.session.prompt()  # type: ignore[return-value, union-attr]

        else:
            self._history = []

            def get_command():
                # type: () -> str
                inp = sys.stdin.readline()  # type: str
                self._history.append(inp)  # type: ignore[union-attr]
                return inp

            self.session = None

        self.get_command = get_command  # type: Callable[..., str]

    def __enter__(self):
        # type: () -> ClickReplContext
        push_context(self)
        return self

    def __exit__(self, *args):
        # type: (Any) -> None
        pop_context()

    @property
    def prompt_msg(self):
        # type: () -> Optional[str]
        if isinstance(self.session, PromptSession):
            return str(self.session.message)
        return None

    @prompt_msg.setter
    def prompt_msg(self, value):
        # type: (str) -> None
        if isinstance(self.session, PromptSession):
            self.session.message = value

    def to_info_dict(self):
        # type: () -> Dict[str, Any]
        return {
            'group_ctx': self.group_ctx,
            'isatty': self.isatty,
            'prompt_kwargs': self.prompt_kwargs,
        }

    def prompt_reset(self):
        # type: () -> None
        if self.isatty:
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
        return func(get_current_click_repl_context(), *args, **kwargs)

    return decorator
