import click
import typing as t
from . import _repl

# from click_repl.parser import currently_introspecting_args

from prompt_toolkit import PromptSession
from ._globals import ISATTY, pop_context, push_context

if t.TYPE_CHECKING:
    from typing import List  # noqa: F401
    from typing import Any, Dict, Generator, Optional, Union, Callable

    from click import Context  # noqa: F401
    from prompt_toolkit.history import History  # noqa: F401

    # InfoDict = t.TypedDict(
    #     "InfoDict",
    #     {
    #         "prompt_kwargs": Dict[str, Any],
    #         "group_ctx": Context,
    #         "parent": ClickReplContext,
    #         "cli_args": List[str],
    #     },
    # )


class ClickReplContext:
    """Context object for REPL

    Keyword arguments:
    ---
    :param:`group_ctx` - Click Context object that belong to a Group
    :param:`validator` - Adds a Validator to the PromptSession
    :param:`prompt_kwargs` - Kwargs for PromptToolkit's `PromptSession` class
    :param:`styles` - Dictionary that denote the style schema of the prompt
    """

    __slots__ = (
        "group_ctx",
        "prompt_kwargs",
        "parent",
        "session",
        "_history",
    )

    def __init__(
        self,
        group_ctx: "Context",
        prompt_kwargs: "Dict[str, Any]",
        parent: "Optional[ClickReplContext]" = None,
    ) -> None:
        if ISATTY:
            self.session: "Optional[PromptSession[Dict[str, Any]]]" = PromptSession(
                **prompt_kwargs,
                # bottom_toolbar=currently_introspecting_args()
            )
            self._history: "Union[History, List[str]]" = self.session.history

        else:
            self.session = None
            self._history = []

        self.group_ctx = group_ctx
        self.prompt_kwargs = prompt_kwargs
        self.parent = parent

    def __enter__(self) -> "ClickReplContext":
        push_context(self)
        return self

    def __exit__(self, *_: "Any") -> None:
        pop_context()

    @property
    def prompt_message(self) -> "Optional[str]":
        if isinstance(self.session, PromptSession):
            return str(self.session.message)
        return None

    @prompt_message.setter
    def prompt_message(self, value: str) -> None:
        if isinstance(self.session, PromptSession):
            self.session.message = value

    # def to_info_dict(self) -> "InfoDict":
    #     """Provides the most minimal info about the current REPL
    #     Return: Dictionary that has some instance variables and its values
    #     """

    #     return {
    #         "prompt_kwargs": self.prompt_kwargs,
    #         "group_ctx": self.group_ctx,
    #         "parent": self.parent,
    #         "cli_args": self.cli_args,
    #     }

    def prompt_reset(self) -> None:
        """
        Resets values of :class:`prompt_toolkit.session.PromptSession` to
        the provided `prompt_kwargs`, discarding any changes done to the
        :class:`prompt_toolkit.session.PromptSession` object
        """

        if self.session is not None:
            self.session = PromptSession(**self.prompt_kwargs)

    def history(self) -> "Generator[str, None, None]":
        """Provides history of the past executed commands

        Yield: Executed command string from the history
        """

        if self.session is not None:
            _history = self._history.load_history_strings()  # type: ignore[union-attr]
        else:
            _history = reversed(self._history)  # type: ignore[arg-type]

        yield from _history


class ReplCli(click.Group):
    def __init__(
        self,
        prompt: str = "> ",
        startup: "Optional[Callable[[], None]]" = None,
        cleanup: "Optional[Callable[[], None]]" = None,
        ctx_args: "Dict[str, Any]" = {},
        repl_kwargs: "Dict[str, Any]" = {},
        **attrs: "Any",
    ):
        ctx_args["invoke_without_command"] = True
        super().__init__(**ctx_args)

        self.prompt = prompt
        self.startup = startup
        self.cleanup = cleanup
        self.repl_kwargs = repl_kwargs

    def invoke(self, ctx: "Context") -> "Any":
        return_val = super().invoke(ctx)

        try:
            if not (ctx.invoked_subcommand or ctx.protected_args):
                if self.startup is not None:
                    self.startup()

                _repl.repl(
                    ctx,
                    prompt_kwargs={
                        "message": self.prompt,
                    },
                    **self.repl_kwargs,
                )

        finally:
            # Finisher callback on the context
            if self.cleanup is not None:
                self.cleanup()

        return return_val
