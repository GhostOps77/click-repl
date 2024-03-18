from __future__ import annotations

import os

from prompt_toolkit.formatted_text import FormattedText

from ._globals import ISATTY
from ._globals import StyleAndTextTuples

__all__ = ["TokenizedFormattedText", "Marquee"]


class TokenizedFormattedText(FormattedText):
    __slots__ = ("parent_token_class",)

    def __init__(self, tokens_list: StyleAndTextTuples, parent_token_class: str) -> None:
        is_not_formatted_text = not isinstance(
            tokens_list, (TokenizedFormattedText, FormattedText)
        )

        if is_not_formatted_text and parent_token_class:
            for index, token_tuple in enumerate(tokens_list):
                class_names_str = token_tuple[0]

                if class_names_str and not class_names_str.startswith("class:"):
                    class_names_str = "class:" + ",".join(
                        f"{parent_token_class}.{class_name}"
                        for class_name in class_names_str.split(",")
                    )

                tokens_list[index] = (class_names_str, token_tuple[1])

        super().__init__(tokens_list)
        self.parent_token_class = parent_token_class

    def get_text(self) -> str:
        res = ""

        for _, value, *_ in self:
            res += value

        return res

    def get_length_by_content(self) -> int:
        length = 0

        for _, value, *_ in self:
            length += len(value)

        # return sum(len(value) for _, value, *_ in self)
        return length

    def slice_by_text_content(self, start: int, stop: int) -> TokenizedFormattedText:
        if start >= stop:
            return []  # type:ignore[return-value]

        result = []

        for token, value, *_ in self:
            if stop <= 0:
                break

            length = len(value)

            if start < length:
                string = value[start:stop]

                if string:
                    result.append((token, string, *_))

            start = max(0, start - length)
            stop = stop - length

        return TokenizedFormattedText(result, self.parent_token_class)


class Marquee:
    """
    Displays the given text in the form of Marquee in terminal.

    Parameters
    ----------
    text : TokenizedFormattedText
        The text that should be displayed in the marquee style.

    prefix : StyleAndTextTuples, default=`[]`
        The text that should be displayed before the given text.
    """

    __slots__ = (
        "text",
        "prefix",
        "pointer_position",
        # "terminal_width",
        "is_pointer_direction_left",
        "hit_boundary",
        "waited_for_in_iterations",
        "is_window_size_le_terminal_size",
        "_recent_text",
    )

    def __init__(
        self,
        text: TokenizedFormattedText,
        prefix: TokenizedFormattedText = [],  # type:ignore[assignment]
    ) -> None:
        self.text = text
        self.prefix = prefix
        self.pointer_position = 0
        # self.terminal_width = 0
        self.is_pointer_direction_left = True
        self.hit_boundary = True
        self.waited_for_in_iterations = 5
        self.is_window_size_le_terminal_size = False

        # This attribute is used to cache recently generated string.
        self._recent_text: StyleAndTextTuples = []

    def get_terminal_width_and_window_size(self) -> tuple[int, int]:
        # os.get_terminal_size() is called for every iteration to handle
        # the change in terminal size.
        terminal_width = os.get_terminal_size().columns
        chunk_size = terminal_width - self.prefix.get_length_by_content()

        return terminal_width, chunk_size

    def adjust_pointer_position(self) -> None:
        """
        Updates the pointer position for the next iteration.
        """
        # Last position of the pointer that would ever reach in the
        # given string object, in right side of it.

        terminal_width, window_size = self.get_terminal_width_and_window_size()

        pointer_max_pos_in_right = (
            self.text.get_length_by_content()
            - terminal_width
            + self.prefix.get_length_by_content()
            + ISATTY
        )

        # Reset the waiting counter when the pointer hits
        # either of the ends of the text.

        if self.pointer_position == pointer_max_pos_in_right:
            # If the pointer has reached it's right most end...
            self.is_pointer_direction_left = False
            self.hit_boundary = True
            self.waited_for_in_iterations = 0

        elif self.pointer_position == 0:
            # If the pointer has reached it's left most end or starting point...
            self.is_pointer_direction_left = True
            self.hit_boundary = True
            self.waited_for_in_iterations = 0

        if self.text.get_length_by_content() <= window_size:
            if not self.is_window_size_le_terminal_size:
                self.is_window_size_le_terminal_size = True

            if self.pointer_position != 0:
                self.pointer_position = 0
                self.hit_boundary = True
                self.waited_for_in_iterations = 0
                self.is_pointer_direction_left = True

            return

        else:
            self.is_window_size_le_terminal_size = False

        if self.is_pointer_direction_left:
            self.pointer_position += 1
        else:
            self.pointer_position -= 1

    def get_full_formatted_text(self) -> TokenizedFormattedText:
        """
        Get the whole text along with the prefix, without being sliced.
        """
        return TokenizedFormattedText(self.prefix + self.text, "bottom-bar")

    def get_current_text_chunk(self) -> StyleAndTextTuples:
        """
        Returns the updated text chunk, along with the prefix,
        that currently should be displayed in the bottom bar.

        Returns the whole text with the prefix, if the length of the
        terminal window is greater than or equal to the length of
        text and prefix objects altogether.
        """

        _, chunk_size = self.get_terminal_width_and_window_size()

        if self.text.get_length_by_content() <= chunk_size:
            if self.is_window_size_le_terminal_size:
                return self._recent_text

            self._recent_text = self.get_full_formatted_text()

        if self.hit_boundary:
            # The string stored/cached in self._recent_text is used only here again
            # without slicing it from the original string, to avoid re-evaluation
            # for the next 5 iterations.
            if self.is_window_size_le_terminal_size:
                return self._recent_text

            if self.waited_for_in_iterations < 5:
                # Wait for the next 5 iterations if you've hit boundary.
                self.waited_for_in_iterations += 1
                return self._recent_text

            self.hit_boundary = False

        chunk_end_pos = self.pointer_position + chunk_size
        text = self.text.slice_by_text_content(self.pointer_position, chunk_end_pos)
        self.adjust_pointer_position()

        # Storing/caching the recently generated string.
        self._recent_text = TokenizedFormattedText(self.prefix + text, "bottom-bar")

        return self._recent_text
