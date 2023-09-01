"""
`click_repl.core`

Core functionality of the click-repl module.
"""
import typing as t

import click
from prompt_toolkit import PromptSession

from . import _repl
from ._globals import _pop_context
from ._globals import _push_context
from ._globals import ISATTY

if t.TYPE_CHECKING:
    from typing import Any, Callable, Dict, Generator, List, Optional, Final

    from click import Context
    from ._internal_cmds import InternalCommandSystem
    from .parser import ReplParsingState

    InfoDict = t.TypedDict(
        "InfoDict",
        {
            "group_ctx": Context,
            "prompt_kwargs": Dict[str, Any],
            "session": Optional[PromptSession[Dict[str, Any]]],
            "internal_command_system": InternalCommandSystem,
            "parent": Optional[ReplContext],  # type: ignore[used-before-def] # noqa: F821
            "_history": List[str],
            "current_state": Optional[ReplParsingState],
        },
    )


__all__ = ["ReplContext", "ReplCli"]


class ReplContext:
    """
    Context object for the REPL (Read-Eval-Print-Loop).

    This class tracks the depth of nested REPLs, ensuring seamless navigation
    between different levels. It facilitates nested REPL scenarios, allowing
    multiple levels of interactive REPL sessions.

    Each REPL's properties are stored inside this context class, allowing them to
    be accessed and shared with their parent REPL.

    All the settings for each REPL session persist until the session is terminated.

    Parameters
    ----------
    group_ctx : `click.Context`
        The click context object that belong to the CLI/parent Group.

    internal_command_system : `InternalCommandSystem`
        The `InternalCommandSystem` object that holds information about
        the internal commands and their prefixes.

    prompt_kwargs : A dSictionary of `str: Any` pairs
        The extra Keyword arguments for `prompt_toolkit.PromptSession` class.

    styles : A dictionary of `str: str` pairs
        A dictionary that denote the style schema of the prompt.
    """

    __slots__ = (
        "group_ctx",
        "prompt_kwargs",
        "parent",
        "session",
        "internal_command_system",
        "_history",
        "current_state",
    )

    def __init__(
        self,
        group_ctx: "Context",
        internal_command_system: "InternalCommandSystem",
        prompt_kwargs: "Dict[str, Any]",
        parent: "Optional[ReplContext]" = None,
    ) -> None:
        self._history: "List[str]" = []

        if ISATTY:
            prompt_kwargs["completer"].repl_ctx = self
            self.session: "PromptSession[Dict[str, Any]]" = PromptSession(
                **prompt_kwargs,
            )

        self.internal_command_system = internal_command_system
        self.group_ctx: "Final[Context]" = group_ctx
        self.prompt_kwargs = prompt_kwargs
        self.parent: "Final[Optional[ReplContext]]" = parent
        self.current_state: "Optional[ReplParsingState]" = None

    def __enter__(self) -> "ReplContext":
        _push_context(self)
        return self

    def __exit__(self, *_: "Any") -> None:
        _pop_context()

    @property
    def prompt_message(self) -> "Optional[str]":
        """
        The message displayed for every prompt input in the REPL.

        Returns
        -------
        str or None
            String if `sys.stdin.isatty()` is `True`, else `None`
        """
        if ISATTY:
            return str(self.session.message)
        return None

    @prompt_message.setter
    def prompt_message(self, value: str) -> None:
        if ISATTY:
            self.session.message = value

    def to_info_dict(self) -> "InfoDict":
        """
        Provides the most minimal info about the current REPL

        Returns
        -------
        A dictionary that has the instance variables and its values.
        """

        res: "InfoDict" = {
            "group_ctx": self.group_ctx,
            "prompt_kwargs": self.prompt_kwargs,
            "internal_command_system": self.internal_command_system,
            "session": None,
            "parent": self.parent,
            "_history": self._history,
            "current_state": self.current_state,
        }

        if ISATTY:
            res.update({"session": self.session})

        return res

    def session_reset(self) -> None:
        """
        Resets values of `prompt_toolkit.session.PromptSession` to
        the provided `prompt_kwargs`, discarding any changes done to the
        `prompt_toolkit.session.PromptSession` object
        """

        if ISATTY:
            self.session = PromptSession(**self.prompt_kwargs)

    def history(self) -> "Generator[str, None, None]":
        """
        Generates the history of past executed commands.

        Yields
        ------
        str
            The executed command string from the history,
            in chronological order from most recent to oldest.
        """

        if ISATTY:
            yield from self.session.history.load_history_strings()

        else:
            yield from reversed(self._history)


class ReplCli(click.Group):
    """
    Custom `click.Group` subclass for invoking the REPL.

    This class extends the functionality of the `click.Group`
    class and is designed to be used as a wrapper to
    automatically invoke the `click_repl._repl.repl()`
    function when the group is invoked without any sub-command.

    Parameters
    ----------
    prompt : str, default: "> "
        The message that should be displayed for every prompt input.

    startup : A function that takes and returns nothing, optional
        The function that gets called before invoking the REPL.

    cleanup : A function that takes and returns nothing, optional
        The function that gets invoked after exiting out of the REPL.

    repl_kwargs : A dictionary of `str: Any` pairs
        The keyword arguments that needs to be sent to the `repl()` function.

    **attrs : dict, optional
        Extra keyword arguments that need to be passed to the `click.Group` class.
    """

    def __init__(
        self,
        prompt: str = "> ",
        startup: "Optional[Callable[[], None]]" = None,
        cleanup: "Optional[Callable[[], None]]" = None,
        repl_kwargs: "Dict[str, Any]" = {},
        **attrs: "t.Any",
    ):
        attrs["invoke_without_command"] = True
        super().__init__(**attrs)

        self.prompt = prompt
        self.startup = startup
        self.cleanup = cleanup

        repl_kwargs.setdefault("prompt_kwargs", {}).update({"message": prompt})

        self.repl_kwargs = repl_kwargs

    def invoke_repl(self, ctx: "Context") -> None:
        try:
            if self.startup is not None:
                self.startup()

            _repl.repl(ctx, **self.repl_kwargs)

        finally:
            if self.cleanup is not None:
                self.cleanup()

    def invoke(self, ctx: "Context") -> "Any":
        return_val = super().invoke(ctx)

        if ctx.invoked_subcommand or ctx.protected_args:
            return return_val

        self.invoke_repl(ctx)

        return return_val
