""""
Core utilities for input validation and displaying error messages
raised during auto-completion.
"""

from __future__ import annotations

import logging

from click import Context, Group
from click.exceptions import ClickException, UsageError
from prompt_toolkit.document import Document
from prompt_toolkit.validation import ValidationError, Validator
from typing_extensions import Final

from ._globals import CLICK_REPL_DEV_ENV, ISATTY, get_current_repl_ctx
from ._internal_cmds import InternalCommandSystem
from .parser import _resolve_state

__all__ = ["ClickValidator"]


logger = logging.getLogger(f"click_repl-{__name__}")

if CLICK_REPL_DEV_ENV:
    logger_level = logging.DEBUG

    # log_format = "%(levelname)s %(name)s [line %(lineno)d] %(message)s"
    # formatter = logging.Formatter(log_format)

    # log_file = ".click-repl-err.log"
    # file_handler = logging.FileHandler(log_file)
    # file_handler.setFormatter(formatter)
    # logger.addHandler(file_handler)


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
        The current :class:`~click.Context` object.

    display_all_errors
        Flag that determines whether to raise generic Python Exceptions, and not to
        display them in the :class:`~prompt_toolkit.validation.Validator` bar,
        resulting in the full error traceback being redirected to a log file
        in the REPL mode.
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
        self.group: Final[Group] = self.group_ctx.command  # type: ignore[assignment]

        self.internal_commands_system = internal_commands_system
        self.display_all_errors = display_all_errors

    def validate(self, document: Document) -> None:
        """
        Validates the input from the prompt by raising a
        :exc:`~prompt_toolkit.validation.ValidationError` if it is invalid.

        Any raised errors are displayed in the
        :class:`~prompt_toolkit.validation.Validator` bar.

        Parameters
        ----------
        document
            Contains the incomplete string from the REPL prompt.

        Raises
        ------
        prompt_toolkit.validation.ValidationError
            If there's any error occurred during argument parsing, and it needs
            to be displayed in the validation bar.

        Exception
            If the error just needs to be raised normally.
        """

        if self.internal_commands_system.get_prefix(document.text_before_cursor)[1]:
            # If the input text in the prompt starts with a prefix indicating an internal
            # or system command, it is considered as such. In this case, there is no need
            # to validate the input, so we can simply return and ignore it.
            return

        try:
            _, state, _ = _resolve_state(self.group_ctx, document.text_before_cursor)

            if ISATTY:
                bottombar = get_current_repl_ctx().bottombar  # type:ignore[union-attr]

                if bottombar is not None:
                    bottombar.update_state(state)

        except UsageError as ue:
            # UsageError's error messages are simple and are raised when there
            # is an improper use of arguments and options. In this case, we can
            # simply display the error message without mentioning the specific
            # error class.
            raise ValidationError(0, ue.format_message())

        except ClickException as ce:
            # Click formats its error messages to provide more detail. Therefore,
            # we can use it to display error messages along with the specific error
            # type.
            raise ValidationError(0, f"{type(ce).__name__}: {ce.format_message()}")

        except Exception as e:
            if self.display_all_errors:
                # All other errors raised during input validation are
                # displayed in the Validator bar, but only if
                # self.catch_all_errors is set to True.
                raise ValidationError(0, f"{type(e).__name__}: {e}") from e

            # if CLICK_REPL_DEV_ENV:
            # Error tracebacks are displayed during the REPL loop if
            # self.catch_all_errors is set to False. The short error
            # messages are also logged into a click-repl-err.log file.
            logger.exception("%s: %s", type(e).__name__, e)
