import contextlib
import sys
from io import StringIO
from click_repl._globals import HAS_CLICK6
from prompt_toolkit.document import Document


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
    if HAS_CLICK6:
        cmd = text.split(" ", maxsplit=1)
        if not cmd:
            return text

        cmd_text = cmd[0].replace("-", "_")

        if len(cmd) == 1:
            return cmd_text

        text = f"{cmd_text} {cmd[1]}"
    return text


class TestDocument(Document):
    __test__ = False

    def __init__(self, text: str = "") -> None:
        super().__init__(_to_click6_text(text))
