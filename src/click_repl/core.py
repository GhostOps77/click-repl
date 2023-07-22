import typing as t

import click
from prompt_toolkit import PromptSession

from . import _repl
from ._globals import _pop_context
from ._globals import _push_context
from ._globals import ISATTY

if t.TYPE_CHECKING:
    from typing import Any, Dict, Generator, List, Optional

    from ._internal_cmds import InternalCommandSystem

    InfoDict = t.TypedDict(
        "InfoDict",
        {
            "group_ctx": click.Context,
            "prompt_kwargs": Dict[str, Any],
            "session": Optional[PromptSession[Dict[str, Any]]],
            "internal_command_system": InternalCommandSystem,
            "parent": Optional[ReplContext],  # type: ignore[used-before-def] # noqa: F821
            "_history": List[str],
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
        group_ctx: "click.Context",
        internal_command_system: "InternalCommandSystem",
        prompt_kwargs: "Dict[str, t.Any]" = {},
        parent: "Optional[ReplContext]" = None,
    ) -> None:
        """
        Initialize the `ReplContext` class.

        Parameters
        ----------
        group_ctx : click.Context
            The click context object that belong to the CLI/parent Group.

        internal_command_system : click_repl._internal_cmds.InternalCommandSystem
            The `InternalCommandSystem` object that holds information about
            the internal commands and their prefixes.

        prompt_kwargs : A dictionary of str: Any pairs.
            The extra Keyword arguments for `prompt_toolkit.PromptSession` class.

        styles : A dictionary of str: str pairs.
            A dictionary that denote the style schema of the prompt.
        """
        self._history: "List[str]" = []

        if ISATTY:
            self.session: "Optional[PromptSession[Dict[str, t.Any]]]" = PromptSession(
                **prompt_kwargs,
            )

        else:
            self.session = None

        self.internal_command_system = internal_command_system
        self.group_ctx: "t.Final[click.Context]" = group_ctx
        self.prompt_kwargs = prompt_kwargs
        self.parent: "t.Final[Optional[ReplContext]]" = parent

    def __enter__(self) -> "ReplContext":
        _push_context(self)
        return self

    def __exit__(self, *_: "t.Any") -> None:
        _pop_context()

    @property
    def prompt_message(self) -> "Optional[str]":
        """
        The message displayed for every prompt input in the REPL.

        Returns
        -------
        str or None
            string if `sys.stdin.isatty()` is `True`, else `None`
        """
        if isinstance(self.session, PromptSession):
            return str(self.session.message)
        return None

    @prompt_message.setter
    def prompt_message(self, value: str) -> None:
        if isinstance(self.session, PromptSession):
            self.session.message = value

    def to_info_dict(self) -> "InfoDict":
        """
        Provides the most minimal info about the current REPL

        Returns
        -------
        A dictionary that has the instance variables and its values.
        """

        return {
            "group_ctx": self.group_ctx,
            "prompt_kwargs": self.prompt_kwargs,
            "session": self.session,
            "internal_command_system": self.internal_command_system,
            "parent": self.parent,
            "_history": self._history,
        }

    def prompt_reset(self) -> None:
        """
        Resets values of `prompt_toolkit.session.PromptSession` to
        the provided `prompt_kwargs`, discarding any changes done to the
        `prompt_toolkit.session.PromptSession` object
        """

        if self.session is not None:
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

        if self.session is not None:
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
    """

    def __init__(
        self,
        prompt: str = "> ",
        startup: "Optional[t.Callable[[], None]]" = None,
        cleanup: "Optional[t.Callable[[], None]]" = None,
        repl_kwargs: "Dict[str, t.Any]" = {},
        **attrs: "t.Any",
    ):
        """
        Initialize the `ReplCli` class.

        Parameters
        ----------
        prompt : str, default: "> "
            The message that should be displayed for every prompt input.

        startup : A function that takes and returns nothing, optional.
            The function that gets called before invoking the REPL.

        cleanup : A function that takes and returns nothing, optional.
            The function that gets invoked after exiting out of the REPL.

        repl_kwargs : A dictionary of str: Any pairs
            The keyword arguments that needs to be sent to the
            `click_repl._repl.repl()` function.

        **attrs : dict, optional
            Extra keyword arguments that need to be passed to the `click.Group`
            class.
        """
        attrs["invoke_without_command"] = True
        super().__init__(**attrs)

        self.prompt = prompt
        self.startup = startup
        self.cleanup = cleanup

        repl_kwargs.setdefault("prompt_kwargs", {}).update({"message": prompt})

        self.repl_kwargs = repl_kwargs

    def invoke(self, ctx: "click.Context") -> "t.Any":
        return_val = super().invoke(ctx)
        if ctx.invoked_subcommand or ctx.protected_args:
            return return_val

        try:
            if self.startup is not None:
                self.startup()

            _repl.repl(ctx, **self.repl_kwargs)

        finally:
            # Finisher callback on the context.
            if self.cleanup is not None:
                self.cleanup()

            return return_val
