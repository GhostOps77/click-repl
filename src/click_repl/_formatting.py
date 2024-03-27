from __future__ import annotations

import os
from typing import Self

from prompt_toolkit.formatted_text import FormattedText

from ._globals import ISATTY, StyleAndTextTuples

__all__ = ["TokenizedFormattedText", "Marquee"]


class TokenizedFormattedText(FormattedText):
    """
    Sub-class of :class:`~prompt_toolkit.formatted_text.FormattedText`,
    but has custom slicing method, based on it's display text.
    """

    __slots__ = ("parent_token_class",)

    def __init__(self, tokens_list: StyleAndTextTuples, parent_token_class: str) -> None:
        """
        Initializes the `TokenizedFormattedText` class.

        Parameters
        ----------
        tokens_list: StyleAndTextTuples
            List of tokens.

        parent_token_class: str
            Parent class name for the tokens in the given `tokens_list`.
        """

        is_not_formatted_text = not isinstance(
            tokens_list, (TokenizedFormattedText, FormattedText)
        )

        if is_not_formatted_text and parent_token_class:
            for index, token_tuple in enumerate(tokens_list):
                class_names = token_tuple[0]

                if class_names and not class_names.startswith("class:"):
                    class_names = "class:" + ",".join(
                        f"{parent_token_class}.{class_name}"
                        for class_name in class_names.split(",")
                    )

                tokens_list[index] = (class_names, *token_tuple[1:])

        super().__init__(tokens_list)

        self.parent_token_class = parent_token_class
        """Parent class name for the tokens in the given
        :attr:`~click_repl._formatting.TokenizedFormattedText.tokens_list`."""

    def get_text(self) -> str:
        """
        Returns the entire display text from each token in a single string.

        Returns
        -------
        str
            Display text altogether from all the tokens.
        """
        return "".join(token[1] for token in self)

    def get_length_by_content(self) -> int:
        """
        Returns the length of the FormattedText based on the length
        of the display text in each token.

        Returns
        -------
        int
            Length of the content in the tokens list.
        """
        return sum(len(token[1]) for token in self)

    def slice_by_text_content(self, start: int, stop: int) -> Self:
        """
        Slices the tokens based on the display text in them.

        Parameters
        ----------
        start : int
            Starting position to slice tokens.

        stop : int
            Last position to stop slicing tokens.

        Returns
        -------
        TokenizedFormattedText
            Returns a new sliced `TokenizedFormattedText` object that contains
            the text content within that slice range.
        """
        if start >= stop:
            return []  # type:ignore[return-value]

        result: StyleAndTextTuples = []

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
    """

    __slots__ = (
        "text",
        "prefix",
        "pointer_position",
        "is_pointer_direction_left",
        "hit_boundary",
        "waited_for_in_iterations",
        "max_wait_in_iterations",
        "_is_text_length_le_window_size",
        "_recent_text",
    )

    def __init__(
        self,
        text: TokenizedFormattedText,
        prefix: TokenizedFormattedText = [],  # type:ignore[assignment]
    ) -> None:
        """
        Initialize the `Marquee` class.

        Parameters
        ----------
        text : TokenizedFormattedText
            The text tokens that'll be displayed in the marquee style.

        prefix : TokenizedFormattedText, default=[]
            This text will be displayed as a prefix before `text`, and
            it will not be moved in the terminal display as a marquee.
        """

        self.text = text
        """The text tokens that'll be displayed in the marquee style."""

        self.prefix = prefix
        """This text will be displayed as a prefix before
        :attr:`~click_repl._formatting.Marquee.text`."""

        self.pointer_position = 0
        """Keeps track of the next starting position to slice the
        :attr:`~click_repl._formatting.Marquee.text` from."""

        self.is_pointer_direction_left = True
        """Flag that keeps track on the current direction on pointer's movement."""

        self.hit_boundary = True
        """Flag that tells if the pointer has hit either the left or right-most end."""

        self.max_wait_in_iterations = 5
        """Maximum number of iterations the pointer can stay idle once it has hit either of the ends."""

        self.waited_for_in_iterations = self.max_wait_in_iterations
        """The pointer stays at the very end once it has touched the boundary, for next
        :attr:`~click_repl._formatting.Marquee.waited_for_in_iterations` iterations"""

        self._is_text_length_le_window_size = False
        """Flag that tells whether the window size to display the
        :attr:`~click_repl._formatting.Marquee.text`'s content is greater than `text`'s length"""

        self._recent_text: StyleAndTextTuples = []
        """Used to cache recently generated string."""

    def get_terminal_width_and_window_size(self) -> tuple[int, int]:
        """
        Gets current terminal's width, and appropriate window size to display it's
        content as marquee.

        Returns
        -------
        tuple[int, int]
            This tuple has the current terminal width, and the new window
            size to display :attr:`~click_repl._formatting.Marquee.text`
        """
        terminal_width = os.get_terminal_size().columns
        window_size = terminal_width - self.prefix.get_length_by_content()

        return terminal_width, window_size

    def adjust_pointer_position(self) -> None:
        """
        Updates the pointer position for the next iteration.
        """
        # Last position of the pointer that would ever reach in the
        # given string object, in right side of it.

        terminal_width, window_size = self.get_terminal_width_and_window_size()

        if self.text.get_length_by_content() <= window_size:
            if not self._is_text_length_le_window_size:
                self._is_text_length_le_window_size = True

            if self.pointer_position != 0:
                self.pointer_position = 0
                self.hit_boundary = True
                self.waited_for_in_iterations = 0
                self.is_pointer_direction_left = True

            return

        elif self._is_text_length_le_window_size:
            self._is_text_length_le_window_size = False

        pointer_max_pos_in_right = (
            self.text.get_length_by_content()
            - terminal_width
            + self.prefix.get_length_by_content()
            + ISATTY
        )

        # Reset the waiting counter when the pointer hits
        # either of the ends of the text.

        pointer_at_right_end = self.pointer_position == pointer_max_pos_in_right
        pointer_at_left_end = self.pointer_position == 0

        if pointer_at_left_end or pointer_at_right_end:
            self.hit_boundary = True
            self.waited_for_in_iterations = 0
            self.is_pointer_direction_left = (
                not pointer_at_right_end or pointer_at_left_end
            )

        if self.is_pointer_direction_left:
            self.pointer_position += 1
        else:
            self.pointer_position -= 1

    def get_full_formatted_text(self) -> TokenizedFormattedText:
        """
        Gets the whole text along with the prefix, without being sliced.

        Returns
        -------
        TokenizedFormattedText
            Contains the entire content of both
            :attr:`~click_repl._formatting.Marquee.prefix`
            and the :attr:`~click_repl._formatting.Marquee.text`
        """
        return TokenizedFormattedText(self.prefix + self.text, "bottom-bar")

    def get_current_text_chunk(self) -> StyleAndTextTuples:
        """
        Returns the updated text chunk, along with the prefix,
        that currently should be displayed in the bottom bar.

        Returns
        -------
        StyleAndTextTuples
            The entire :attr:`~click_repl._formatting.Marquee.text` with the
            :attr:`~click_repl._formatting.Marquee.prefix` if the terminal window length
            is sufficient. Otherwise, returns a sliced portion of the `text` that fits
            the current window size.
        """

        _, window_size = self.get_terminal_width_and_window_size()

        if self.text.get_length_by_content() <= window_size:
            if not self._is_text_length_le_window_size:
                self._recent_text = self.get_full_formatted_text()
                self.adjust_pointer_position()

            return self._recent_text

        if self.hit_boundary:
            # The string cached in self._recent_text is used only here again
            # without slicing it from the original string, to avoid re-evaluation
            # for the next 5 iterations.

            if self.waited_for_in_iterations < self.max_wait_in_iterations:
                # Wait for the next 5 iterations if you've hit boundary.
                self.waited_for_in_iterations += 1
                return self._recent_text

            self.hit_boundary = False

        chunk_end_pos = self.pointer_position + window_size
        text = self.text.slice_by_text_content(self.pointer_position, chunk_end_pos)
        self.adjust_pointer_position()

        # Storing/Caching the recently generated string.
        self._recent_text = TokenizedFormattedText(self.prefix + text, "bottom-bar")

        return self._recent_text
