import contextlib
import sys
from io import StringIO

from prompt_toolkit.document import Document

from click_repl._globals import HAS_CLICK6


@contextlib.contextmanager
def mock_stdin(text):
    text = _to_click6_text(text)

    old_stdin = sys.stdin
    try:
        sys.stdin = StringIO(text)
        yield sys.stdin
    finally:
        sys.stdin = old_stdin


def _to_click6_text(text: str) -> str:
    if not HAS_CLICK6:
        return text

    cmd = text.split(" ", maxsplit=1)
    if not cmd:
        return text

    cmd_text = cmd[0].replace("-", "_")

    if len(cmd) == 1:
        return cmd_text

    return f"{cmd_text} {cmd[1]}"


class TestDocument(Document):
    __test__ = False

    def __init__(self, text: str = "") -> None:
        super().__init__(_to_click6_text(text))
