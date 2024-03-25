from __future__ import annotations

import os
from collections import namedtuple

import pytest

from click_repl._formatting import Marquee
from click_repl._formatting import TokenizedFormattedText
from click_repl.bottom_bar import BottomBar

terminal_size = namedtuple("terminal_size", ["columns", "lines"])


def sliding_str_window(string, n):
    if n >= len(string):
        while True:
            yield string
        # return

    i = 0

    while i + n <= len(string):
        yield string[i : i + n]
        i += 1


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


def _get_terminal_size_func(value):
    def _get_terminal_size(arg=1):
        return terminal_size(value, 1)

    return _get_terminal_size


def _test_marquee():
    marquee = Marquee(sample_token, prefix=sample_prefix)
    bottombar = BottomBar()
    bottombar._recent_formatted_text = marquee

    _terminal_size, chunk_size = marquee.get_terminal_width_and_window_size()

    window_iter_obj = iter(
        sliding_str_window(tokens_list_content_str, marquee.pointer_position + chunk_size)
    )

    first_yield = next(window_iter_obj)

    # Waits for the first 5 iterations
    for _ in range(6):
        current_chunk_as_text = "".join(
            token[1] for token in bottombar.get_formatted_text()
        )

        assert current_chunk_as_text == (prefix_list_content_str + first_yield)

    # Then it starts to iterate over the list
    max_iterations_to_right = (
        sample_token.get_length_by_content()
        - _terminal_size
        + sample_prefix.get_length_by_content()
    )

    for _, expected_window_content in zip(
        range(max_iterations_to_right),
        window_iter_obj,
    ):
        current_chunk_as_text = "".join(
            token[1] for token in bottombar.get_formatted_text()
        )

        assert current_chunk_as_text == (
            prefix_list_content_str + expected_window_content
        )

    # Also waits for 5 more iterations after hitting the end.
    for _ in range(5):
        current_chunk_as_text = "".join(
            token[1] for token in bottombar.get_formatted_text()
        )

        assert current_chunk_as_text == (
            prefix_list_content_str + expected_window_content
        )


@pytest.mark.parametrize("terminal_size", [21, len(prefix_list_content_str) + 20])
def test_marquee_overflowing_content(monkeypatch, terminal_size):
    monkeypatch.setattr(os, "get_terminal_size", _get_terminal_size_func(terminal_size))
    _test_marquee()


def test_marquee_inline_content(monkeypatch):
    monkeypatch.setattr(
        os,
        "get_terminal_size",
        _get_terminal_size_func(
            len(prefix_list_content_str) + len(tokens_list_content_str) + 20
        ),
    )

    bottombar = BottomBar()
    bottombar._recent_formatted_text = Marquee(sample_token, prefix=sample_prefix)

    for _ in range(len(prefix_list_content_str)):
        assert bottombar.get_formatted_text().get_text() == (
            prefix_list_content_str + tokens_list_content_str
        )


# def test_dynamic_change_in_terminal_width(monkeypatch):
#     monkeypatch.setattr(
#         os,
#         "get_terminal_size",
#         _get_terminal_size_func(
#             len(prefix_list_content_str) + len(tokens_list_content_str) + 20
#         ),
#     )
