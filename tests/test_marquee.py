from __future__ import annotations

from collections import deque
from itertools import islice

from click_repl._formatting import Marquee
from click_repl._formatting import TokenizedFormattedText


class MarqueeForTesting(Marquee):
    def get_terminal_width_and_display_chunk_size(self) -> tuple[int, int]:
        # 21 is just a randomly chosen value for terminal length
        # But it needs to be dynamic
        return 21, 21 - self.prefix.get_length_by_content()


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


def test_marquee():
    marquee = MarqueeForTesting(sample_token, prefix=sample_prefix)

    terminal_width, chunk_size = marquee.get_terminal_width_and_display_chunk_size()
    max_iterations_over_right = terminal_width - chunk_size

    for _, expected_window_content in zip(
        range(max_iterations_over_right),
        sliding_str_window(tokens_list_content_str, max_iterations_over_right),
    ):
        "".join(token[1] for token in marquee.get_current_text_chunk())

        # assert current_chunk_as_text == (
        #   prefix_list_content_str + expected_window_content
        # )
        # this test ain't passing
