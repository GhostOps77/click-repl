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


class ClickValidator(Validator):
    # __slots__ = (
    #     "cli", "cli_ctx", "parsed_args", "internal_cmd_prefix", "system_cmd_prefix"
    # )

    def __init__(
        self,
        ctx: "Context",
        internal_commands_system: "InternalCommandSystem",
    ) -> None:
        self.cli_ctx: "Final[Context]" = ctx
        self.cli: "Final[MultiCommand]" = ctx.command  # type: ignore[assignment]
        self.internal_commands_system = internal_commands_system

        # self.parsed_args: "List[str]" = []
        # self.parsed_ctx = cli_ctx
        # self.ctx_command = cli

    def _validate(self, document: "Document") -> None:
        # To Detect the changes in the args
        # if self.parsed_args != args:
        #     self.parsed_args = args

        _resolve_state(self.cli_ctx, document.text_before_cursor)

    def validate(self, document: "Document") -> None:
        """Validates input from the prompt by raising the
        :class:~prompt_toolkit.validation.ValidationError

        Keyword arguments:
        ---
        :param:`document` - :class:`~prompt_toolkit.document.Document` object
        containing the incomplete command line string
        """

        if self.internal_commands_system.get_prefix(document.text_before_cursor):
            return

        try:
            self._validate(document)

        except UsageError as e:
            raise ValidationError(0, e.format_message())

        except ClickException as e:
            raise ValidationError(0, f"{type(e).__name__}: {e.format_message()}")

        # except (IndexError, KeyError) as e:
        #     raise e

        except Exception as e:
            raise ValidationError(0, f"{type(e).__name__}: {e}")
