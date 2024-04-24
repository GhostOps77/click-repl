"""
Core utilities for input validation and displaying error messages
raised during auto-completion.
"""

from __future__ import annotations

import logging

from click import Context
from click.exceptions import ClickException, UsageError
from prompt_toolkit.document import Document
from prompt_toolkit.validation import ValidationError, Validator
from typing_extensions import Final

from .globals_ import CLICK_REPL_DEV_ENV
from .internal_commands import InternalCommandSystem
from .parser import _resolve_state

__all__ = ["ClickValidator"]


logger = logging.getLogger(f"click_repl-{__name__}")

if CLICK_REPL_DEV_ENV:
    logger_level = logging.DEBUG

else:
    logger_level = logging.WARNING

logger.setLevel(logger_level)

log_format = "%(levelname)s %(name)s [line %(lineno)d] %(message)s"
formatter = logging.Formatter(log_format)

log_file = ".click-repl-err.log"
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


class ClickValidator(Validator):
    """
    Custom prompt input validation for the REPL.

    Parameters
    ----------
    group_ctx
        The current click context object.

    internal_commands_system
        Holds information about the internal commands and their prefixes.

    display_all_errors
        Determines whether to raise generic python exceptions, and not
        display them in the validator bar, resulting in the full error
        traceback being redirected to a log file in the REPL mode.
    """

    def __init__(
        self,
        group_ctx: Context,
        internal_commands_system: InternalCommandSystem,
        display_all_errors: bool = True,
    ) -> None:
        """
        Initializes a `ClickValidator` object.
        """

        self.group_ctx: Final[Context] = group_ctx
        """The click context object of the main group."""

        self.internal_commands_system = internal_commands_system
        """
        The InternalCommandSystem object of the current REPL session.
        """

        self.display_all_errors = display_all_errors
        """
        Determines whether to raise generic python exceptions, and not display
        them in the validator bar.
        """

    def validate(self, document: Document) -> None:
        """
        Validates the input from the prompt.

        Any errors raised while parsing text in prompt are displayed in the
        validator bar.

        Parameters
        ----------
        document
            The incomplete string from the REPL prompt.

        Raises
        ------
        prompt_toolkit.validation.ValidationError
            If there's any error occurred during input validation, and needs
            to be displayed in the validator bar.

        Exception
            If there's error that needs to be raised normally.
        """

        if self.internal_commands_system.get_prefix(document.text_before_cursor)[1]:
            # If the input text in the prompt starts with a internal or system command
            # prefix, there is no need to validate the input.
            # So we can simply return and ignore it.
            return

        try:
            _resolve_state(self.group_ctx, document.text_before_cursor)

        except UsageError as ue:
            # UsageError's error messages are simple and are raised when there
            # is an improper use of arguments and options. In this case, we can
            # simply display the formatted error message without mentioning the
            # specific error class.
            raise ValidationError(0, ue.format_message())

        except ClickException as ce:
            # Click formats it's error messages to provide more detail. We can use it
            # to display error messages along with the specific error type.
            raise ValidationError(0, f"{type(ce).__name__}: {ce.format_message()}")

        except Exception as e:
            if self.display_all_errors:
                # All other errors raised during input validation are
                # displayed in the validator bar.
                raise ValidationError(0, f"{type(e).__name__}: {e}") from e

            # The generic exception's error messages are logged into a
            # click-repl-err.log file.
            logger.exception("%s: %s", type(e).__name__, e)
