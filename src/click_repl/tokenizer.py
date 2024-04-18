from __future__ import annotations

import os
from typing import Iterable, Literal

import click
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.formatted_text import StyleAndTextTuples as ListOfTokens

from .globals_ import ISATTY

__all__ = ["TokenizedFormattedText", "Marquee"]


TokenClassForClickObjectTypes = Literal[
    "internal-command", "command", "group", "argument", "option", "parameter"
]
# Parent token class names for click classes.


def append_classname_to_all_tokens(
    tokens_list: ListOfTokens, classes: Iterable[str] = []
) -> ListOfTokens:
    """
    Appends the given list of token `classes` to all the classes string in every
    token in `tokens_list`

    Parameters
    ----------
    tokens_list
        List of tokens to which each of their token's classes needs to be updated.

    classes
        List of class names to append to the pre-existing classes.

    Returns
    -------
    ListOfTokens
        Updated `tokens_list` with `classes` appended to each token's classes string.
    """

    if not classes:
        return tokens_list

    res: ListOfTokens = []

    for token, *_ in tokens_list:
        res.append((f"{token},{','.join(classes)}", *_))  # type:ignore[arg-type]

    return res


def option_flag_tokens_joiner(
    contents: Iterable[str],
    content_token_class: str,
    sep_token_class: str,
    sep: str = " ",
) -> ListOfTokens:
    """
    Joins the given `contentss` of strings into a token string with the given
    `content_token_class`, `sep` string and it's token's class `sep_token_class`.

    Parameters
    ----------
    contents
        List of strings that should be as tokens

    content_token_class
        Token class name(s) for strings in `contents`

    sep_token_class
        Token class name(s) for `sep`

    sep
        String that separates `contents` when displayed together

    Returns
    -------
    ListOfTokens
        Given `contents` separated by `sep`, as tokens list with given classes string.
    """
    if not contents:
        return []

    sep_elem = (sep_token_class, sep)
    iterator = iter(contents)
    res: ListOfTokens = [(content_token_class, next(iterator))]

    for item in iterator:
        res.append(sep_elem)
        res.append((content_token_class, item))

    return res


def get_token_class_for_click_obj_type(
    obj: click.Command | click.Parameter,
) -> TokenClassForClickObjectTypes:
    """
    Retrieve the token class name suitable for the provided object `obj`
    from a class within the click module.

    Parameters
    ----------
    obj
        The object for which the token class name is to be determined

    Returns
    -------
        The token class name corresponding to the provided object
    """
    if isinstance(obj, click.Parameter):
        if isinstance(obj, click.Argument):
            return "argument"

        elif isinstance(obj, click.Option):
            return "option"

        else:
            return "parameter"

    elif isinstance(obj, click.Group):
        return "group"

    return "command"


class TokenizedFormattedText(FormattedText):
    """
    Sub-class of :class:`~prompt_toolkit.formatted_text.FormattedText`,
    but has custom slicing method, based on it's display text.

    Parameters
    ----------
    tokens_list
        List of Token tuples.

    parent_token_class
        Parent class name for the tokens in the given ``tokens_list``.
    """

    __slots__ = ("parent_token_class",)

    def __init__(self, tokens_list: ListOfTokens, parent_token_class: str = "") -> None:
        """
        Initializes the `TokenizedFormattedText` class.
        """

        is_not_formatted_text = not isinstance(tokens_list, (type(self), FormattedText))

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

        self.parent_token_class: str = parent_token_class
        """Parent class name for the tokens in the given ``tokens_list``."""

    def get_text(self) -> str:
        """
        Returns the entire display text from each token in a single string.

        Returns
        -------
        str
            Display text altogether from all the tokens.
        """
        return "".join(token[1] for token in self)

    def content_length(self) -> int:
        """
        Returns the length of the :class:`~prompt_toolkit.formatted_text.FormattedText`
        based on the length of the display text in each token.

        Returns
        -------
        int
            Length of the content altogether in the tokens list.
        """
        return sum(len(token[1]) for token in self)

    def slice_by_textual_content(self, start: int, stop: int) -> TokenizedFormattedText:
        """
        Slices the tokens based on the display text in them.

        Parameters
        ----------
        start
            Starting position to slice tokens.

        stop
            Last position to stop slicing tokens.

        Returns
        -------
        TokenizedFormattedText
            Returns a new slice that contains the text content within that slice range.
        """
        if start >= stop:
            return []  # type:ignore[return-value]

        result: ListOfTokens = []

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
    text
        The text tokens that will be displayed in the marquee style.

    prefix
        This text will be displayed as a prefix before :attr:`.text`, and
        it will not be moved in the terminal display as a marquee.
    """

    __slots__ = (
        "text",
        "prefix",
        "pointer_position",
        "is_pointer_direction_left",
        "hit_boundary",
        "no_of_iterations_waited_for",
        "max_wait_in_iterations",
        "_is_text_length_le_window_size",
        "_recent_text",
    )

    def __init__(
        self,
        text: ListOfTokens,
        prefix: ListOfTokens = [],
    ) -> None:
        """
        Initialize the `Marquee` class.
        """

        if not isinstance(text, TokenizedFormattedText):
            text = TokenizedFormattedText(text)

        self.text: TokenizedFormattedText = text
        """The text tokens that'll be displayed in the marquee style."""

        if not isinstance(prefix, TokenizedFormattedText):
            prefix = TokenizedFormattedText(prefix)

        self.prefix: TokenizedFormattedText = prefix
        """This text will be displayed as a prefix before :attr:`.text`."""

        self.pointer_position: int = 0
        """Keeps track of the next starting position to slice the :attr:`.text` from."""

        self.is_pointer_direction_left: bool = True
        """To keep track on the current direction on pointer's movement."""

        self.hit_boundary: bool = True
        """Flag that tells if the pointer has hit either the left or right-most end."""

        self.max_wait_in_iterations: int = 5
        """Maximum number of iterations the pointer can stay
            idle once it has hit either of the ends."""

        self.no_of_iterations_waited_for: int = self.max_wait_in_iterations
        """The pointer stays at the very end once it has touched the boundary, for next
            :attr:`.no_of_iterations_waited_for` iterations."""

        self._is_text_length_le_window_size: bool = False
        # Flag that tells whether the window size that displays the
        # text's content is greater than the length of the text.

        self._recent_text: TokenizedFormattedText = []  # type:ignore[assignment]
        # Used to cache recently generated string.

    def get_window_size(self) -> int:
        """
        Returns the appropriate window size to display it's content as marquee.

        Returns
        -------
        int
            New window size to display a chunk of :attr:`.text`
        """
        return os.get_terminal_size().columns - self.prefix.content_length()

    def adjust_pointer_position(self) -> None:
        """
        Updates the :attr:`.pointer_position` for the next iteration for updating the text.
        """
        # Last position of the pointer that would ever reach in the
        # given string object, in right side of it.

        terminal_width = os.get_terminal_size().columns
        window_size = self.get_window_size()

        if self.text.content_length() <= window_size:
            if not self._is_text_length_le_window_size:
                self._is_text_length_le_window_size = True

            if self.pointer_position != 0:
                self.pointer_position = 0
                self.hit_boundary = True
                self.no_of_iterations_waited_for = 0
                self.is_pointer_direction_left = True

            return

        elif self._is_text_length_le_window_size:
            self._is_text_length_le_window_size = False

        pointer_max_pos_in_right = (
            self.text.content_length()
            - terminal_width
            + self.prefix.content_length()
            + ISATTY
        )

        # Reset the waiting counter when the pointer hits
        # either of the ends of the text.

        pointer_at_right_end = self.pointer_position == pointer_max_pos_in_right
        pointer_at_left_end = self.pointer_position == 0

        if pointer_at_left_end or pointer_at_right_end:
            self.hit_boundary = True
            self.no_of_iterations_waited_for = 0
            self.is_pointer_direction_left = (
                not pointer_at_right_end or pointer_at_left_end
            )

        if self.is_pointer_direction_left:
            self.pointer_position += 1

        else:
            self.pointer_position -= 1

    def get_full_formatted_text(self) -> TokenizedFormattedText:
        """
        Returns the whole text along with the :attr:`.prefix`, without being sliced.

        Returns
        -------
        TokenizedFormattedText
            Contains the entire content of both :attr:`.prefix` and the :attr:`.text`
        """
        return TokenizedFormattedText(self.prefix + self.text, "bottom-bar")

    def get_current_text_chunk(self) -> TokenizedFormattedText:
        """
        Returns the updated text chunk, along with the :attr:`.prefix`, that currently
        should be displayed in the bottom bar.

        Returns
        -------
        TokenizedFormattedText
            The entire :attr:`.text` with the :attr:`.prefix` if the terminal window
            length is sufficient. Otherwise, returns a sliced portion of the
            :attr:`.text` that fits the current window size.
        """

        window_size = self.get_window_size()

        if self.text.content_length() <= window_size:
            if not self._is_text_length_le_window_size:
                self._recent_text = self.get_full_formatted_text()
                self.adjust_pointer_position()

            return self._recent_text

        if self.hit_boundary:
            # The string cached in self._recent_text is used only here again
            # without slicing it from the original string, to avoid re-evaluation
            # for the next 5 iterations.

            if self.no_of_iterations_waited_for < self.max_wait_in_iterations:
                # Wait for the next 5 iterations if you've hit boundary.
                self.no_of_iterations_waited_for += 1
                return self._recent_text

            self.hit_boundary = False

        chunk_end_pos = self.pointer_position + window_size
        text = self.text.slice_by_textual_content(self.pointer_position, chunk_end_pos)
        self.adjust_pointer_position()

        # Storing/Caching the recently generated string.
        self._recent_text = TokenizedFormattedText(self.prefix + text, "bottom-bar")

        return self._recent_text
