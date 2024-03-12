from __future__ import annotations

import os
from collections import deque
from collections import namedtuple
from itertools import islice

from click_repl._formatting import Marquee
from click_repl._formatting import TokenizedFormattedText

terminal_size = namedtuple("terminal_size", ["columns", "lines"])


def sliding_str_window(iterable, n, reverse=False):
    if reverse:
        it = reversed(iterable)
    else:
        it = iter(iterable)

    window = deque(islice(it, n), maxlen=n)

    if len(window) == n:
        yield "".join(window)

    for x in it:
        if reverse:
            window.appendleft(x)
        else:
            window.append(x)

        yield "".join(window)


tokens_list = [
    ("sample.token.1", "["),
    ("sample.token.2", "Sample"),
    ("sample.token.space", " "),
    ("sample.token.3", "Token"),
    ("sample.token.space", " "),
    ("sample.token.4", "Demo"),
    ("sample.token.5", "]"),
    ("sample.token.space", " "),
    ("sample.token.6", "hi"),
    ("sample.token.space", " "),
    ("sample.token.7", "how"),
    ("sample.token.space", " "),
    ("sample.token.8", "are"),
    ("sample.token.space", " "),
    ("sample.token.9", "you"),
    ("sample.token.space", " "),
    ("sample.token.10", "?"),
]

sample_token = TokenizedFormattedText(tokens_list, "sample-class-name")
tokens_list_content_str = "".join(token[1] for token in tokens_list)

prefix_list = [
    ("sample.prefix.1", "Prefix"),
    ("sample.prefix.symbol", ":"),
    ("sample.prefix.space", " "),
]

sample_prefix = TokenizedFormattedText(prefix_list, "sample-prefix")
prefix_list_content_str = "".join(token[1] for token in prefix_list)


def _get_terminal_size_func(value=21):
    def _get_terminal_size():
        return terminal_size(21, 1)

    return _get_terminal_size


def test_marquee(monkeypatch):
    monkeypatch.setattr(os, "get_terminal_size", _get_terminal_size_func())

    marquee = Marquee(sample_token, prefix=sample_prefix)

    _terminal_size, chunk_size = marquee.get_terminal_width_and_display_window_size()
    max_iterations_over_right = _terminal_size - chunk_size

    window_iter_obj = iter(
        sliding_str_window(tokens_list_content_str, marquee.pointer_position + chunk_size)
    )

    first_yield = next(window_iter_obj)

    # Waits for the first 5 iterations
    for _ in range(6):
        current_chunk_as_text = "".join(
            token[1] for token in marquee.get_current_text_chunk()
        )

        assert current_chunk_as_text == (prefix_list_content_str + first_yield)

    # Then it starts to iterate over the list
    for _, expected_window_content in zip(
        range(max_iterations_over_right),
        window_iter_obj,
    ):
        current_chunk_as_text = "".join(
            token[1] for token in marquee.get_current_text_chunk()
        )

        assert current_chunk_as_text == (
            prefix_list_content_str + expected_window_content
        )
