from prompt_toolkit.validation import Validator, ValidationError

from click.exceptions import ClickException
from .utils import get_parsed_ctx_and_state
import typing as t

if t.TYPE_CHECKING:
    from click import Group, Context
    from prompt_toolkit.document import Document

__all__ = ["ReplValidator"]


class ReplValidator(Validator):
    __slots__ = ("cli", "cli_ctx")

    def __init__(self, ctx: "Context") -> None:
        self.cli_ctx = ctx
        self.cli: "Group" = ctx.command  # type: ignore[assignment]

        # self.parsed_args = []
        # self.parsed_ctx = cli_ctx
        # self.ctx_command = cli

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
            (
                parsed_ctx,
                parsed_args,
                incomplete,
                ctx_command,
                state,
            ) = get_parsed_ctx_and_state(self.cli_ctx, document.text_before_cursor)

        except ClickException as e:
            raise ValidationError(0, f"{type(e).__name__}: {e.format_message()}")

        except (IndexError, KeyError) as e:
            raise e

        except Exception as e:
            raise ValidationError(0, f"{type(e).__name__}: {e}")
