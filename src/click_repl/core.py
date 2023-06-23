import typing as t

import click
from prompt_toolkit import PromptSession

from . import _repl
from ._globals import ISATTY, pop_context, push_context

if t.TYPE_CHECKING:
    from typing import (Any, Callable, Dict, Final, Generator, List, Optional,
                        Union)

    from click import Context  # noqa: F401
    from prompt_toolkit.history import History  # noqa: F401

    from ._internal_cmds import InternalCommandSystem

    # InfoDict = t.TypedDict(
    #     "InfoDict",
    #     {
    #         "prompt_kwargs": Dict[str, Any],
    #         "group_ctx": Context,
    #         "parent": ClickReplContext,
    #         "cli_args": List[str],
    #     },
    # )


__all__ = ["ReplContext", "ReplCli"]


class ReplContext:
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
        "internal_command_system",
        "_history",
    )

    def __init__(
        self,
        group_ctx: "Context",
        internal_command_system: "InternalCommandSystem",
        prompt_kwargs: "Dict[str, Any]" = {},
        parent: "Optional[ReplContext]" = None,
    ) -> None:
        if ISATTY:
            self.session: "Optional[PromptSession[Dict[str, Any]]]" = PromptSession(
                **prompt_kwargs,
            )
            self._history: "Union[History, List[str]]" = self.session.history

        else:
            self.session = None
            self._history = []

        self.internal_command_system = internal_command_system
        self.group_ctx: "Final[Context]" = group_ctx
        self.prompt_kwargs = prompt_kwargs
        self.parent: "Final[Optional[ReplContext]]" = parent

    def __enter__(self) -> "ReplContext":
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
        repl_kwargs: "Dict[str, Any]" = {},
        **attrs: "Any",
    ):
        attrs["invoke_without_command"] = True
        super().__init__(**attrs)

        self.prompt = prompt
        self.startup = startup
        self.cleanup = cleanup

        repl_kwargs.setdefault("prompt_kwargs", {}).update({"message": prompt})

        self.repl_kwargs = repl_kwargs

    def invoke(self, ctx: "Context") -> "Any":
        return_val = super().invoke(ctx)
        if ctx.invoked_subcommand or ctx.protected_args:
            return return_val

        try:
            if self.startup is not None:
                self.startup()

            _repl.repl(
                ctx,
                **self.repl_kwargs,
            )

        finally:
            # Finisher callback on the context
            if self.cleanup is not None:
                self.cleanup()

            return return_val
