""""
click_repl.validator

Core utilities for input validation and displaying error messages
raised during auto-completion.
"""
import logging
import typing as t

from click.exceptions import ClickException
from click.exceptions import UsageError
from prompt_toolkit.validation import ValidationError
from prompt_toolkit.validation import Validator

from ._internal_cmds import InternalCommandSystem
from .utils import _resolve_state

if t.TYPE_CHECKING:
    from typing import Final

    from click import Context, MultiCommand
    from prompt_toolkit.document import Document


__all__ = ["ClickValidator"]

log_format = "%(levelname)s | %(message)s"

logging.basicConfig(format=log_format, level=logging.ERROR)

logger = logging.getLogger("click-repl-err")

log_file = "click-repl-err.log"
formatter = logging.Formatter(log_format)

file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)
# logging.StreamHandler(stream=None)


class ClickValidator(Validator):
    """
    Custom prompt input validation for the click_repl app.

    Parameters
    ----------
    ctx : `click.Context`
        The current `click.Context` object.

    internal_commands_system : `InternalCommandSystem`
        The `InternalCommandSystem` object
        that holds information about the internal commands and their prefixes.

    display_all_errors : bool
        If `False`, all generic Python Exceptions that are raised, will not be
        displayed in the Validator bar, resulting in the full error traceback
        being displayed in the REPL mode.
    """

    def __init__(
        self,
        ctx: "Context",
        internal_commands_system: "InternalCommandSystem",
        display_all_errors: bool = True,
    ) -> None:
        self.cli_ctx: "Final[Context]" = ctx
        self.cli: "Final[MultiCommand]" = self.cli_ctx.command  # type: ignore[assignment]

        self.internal_commands_system = internal_commands_system

        self.display_all_errors = display_all_errors

    def _validate(self, document_text: str) -> None:
        """
        Parses the input from the REPL prompt and raises errors
        if validation fails.

        Parameters
        ----------
        document_text : str
            The input string currently in the REPL prompt.
        """

        _resolve_state(self.cli_ctx, document_text)

    def validate(self, document: "Document") -> None:
        """
        Validates the input from the prompt by raising a
        `prompt_toolkit.validation.ValidationError` if it is invalid.
        Any raised errors are displayed in the Validator bar.

        Parameters
        ----------
        document : `prompt_toolkit.document.Document`
            A `prompt_toolkit.document.Document` object
            containing the incomplete string from the REPL.

        Raises
        ------
        `prompt_toolkit.validation.ValidationError`
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
            self._validate(document.text_before_cursor)

        except UsageError as e:
            # UsageError's error messages are simple and are raised when there
            # is an improper use of arguments and options. In this case, we can
            # simply display the error message without mentioning the specific
            # error class.
            raise ValidationError(0, e.format_message())

        except ClickException as e:
            # Click formats its error messages to provide more detail. Therefore,
            # we can use it to display error messages along with the specific error
            # type.
            raise ValidationError(0, f"{type(e).__name__}: {e.format_message()}")

        except Exception as e:
            if self.display_all_errors:
                # All other errors raised during input validation are
                # displayed in the Validator bar, but only if
                # self.catch_all_errors is set to True.
                raise ValidationError(0, f"{type(e).__name__}: {e}")

            # Error tracebacks are displayed during the REPL loop if
            # self.catch_all_errors is set to False. The short error
            # messages are also logged into a click-repl-err.log file.
            logger.error(f"{type(e).__name__}: {str(e)}")
            raise e
