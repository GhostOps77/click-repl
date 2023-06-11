from prompt_toolkit.validation import Validator, ValidationError

from click.exceptions import ClickException
from .utils import get_parsed_ctx_and_state
from .parser import get_args_and_incomplete_from_args
import typing as t

if t.TYPE_CHECKING:
    from click import MultiCommand, Context
    from prompt_toolkit.document import Document
    from typing import List, Final


__all__ = ["ReplValidator"]


class ReplValidator(Validator):
    __slots__ = ("cli_ctx", "parsed_args", "internal_cmd_prefix", "system_cmd_prefix")

    def __init__(
        self, ctx: "Context", internal_cmd_prefix: str, system_cmd_prefix: str
    ) -> None:
        self.cli_ctx: "Final[Context]" = ctx
        self.cli: "Final[MultiCommand]" = ctx.command  # type: ignore[assignment]

        self.internal_cmd_prefix = (internal_cmd_prefix,)
        self.system_cmd_prefix = (system_cmd_prefix,)

        self.parsed_args: "List[str]" = []
        # self.parsed_ctx = cli_ctx
        # self.ctx_command = cli

    def _validate(self, document: "Document") -> None:
        args, _ = get_args_and_incomplete_from_args(document.text_before_cursor)

        # To Detect the changes in the args
        if self.parsed_args != args:
            self.parsed_args = args

            get_parsed_ctx_and_state(self.cli_ctx, args)

    def validate(self, document: "Document") -> None:
        """Validates input from the prompt by raising the
        :class:~prompt_toolkit.validation.ValidationError

        Keyword arguments:
        ---
        :param:`document` - :class:`~prompt_toolkit.document.Document` object
        containing the incomplete command line string
        """

        if document.text.startswith(("!", ":")):
            return

        try:
            self._validate(document)

        except ClickException as e:
            raise ValidationError(0, f"{type(e).__name__}: {e.format_message()}")

        # except (IndexError, KeyError) as e:
        #     raise e

        except Exception as e:
            raise ValidationError(0, f"{type(e).__name__}: {e}")
