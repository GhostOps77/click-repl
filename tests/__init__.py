from __future__ import annotations

import contextlib
import sys
from io import StringIO
from typing import Callable

from click_repl._internal_cmds import InternalCommandSystem


class DummyInternalCommandSystem(InternalCommandSystem):
    def _group_commands_by_callback_and_description(
        self,
    ) -> dict[tuple[Callable[[], None], str], list[str]]:
        return {}

    def get_prefix(self, command: str) -> tuple[str, str | None]:
        return ("", None)


@contextlib.contextmanager
def mock_stdin(text):
    old_stdin = sys.stdin
    try:
        sys.stdin = StringIO(text)
        yield sys.stdin
    finally:
        sys.stdin = old_stdin
