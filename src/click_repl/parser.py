"""
Parsing functionalities for the module.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Any, Dict, cast

import click
from click import Command, Context, Group, Parameter
from typing_extensions import TypeAlias

from ._compat import split_arg_string
from .click_custom.shell_completion import _resolve_context
from .utils import is_param_value_incomplete, iterate_command_params

InfoDict: TypeAlias = Dict[str, Any]
# Dictionary that has info about the click objects.

_quotes_to_empty_str_dict = str.maketrans(dict.fromkeys("'\"", ""))

# Just gonna assume that people use only '-' and '--' as prefix for option flags
# _EQUALS_SIGN_AFTER_OPT_FLAG = re.compile(r"^(--?[a-z][\w-]*)=(.*)$", re.I)
_EQUALS_SIGN_AFTER_OPT_FLAG = re.compile(
    r"^(([^a-z\d\s])\2?[a-z]+(?:[\w-]+)?)=(.*)$", re.I
)


class Incomplete:
    """
    Stores the last incomplete text token in the current prompt input, that requires
    suggestions. It stores the incomplete last text token in its raw form in
    :attr:`~.raw_str` attribute, and in its parsed form in
    :attr:`~.parsed_str` attribute. The parsed form has no unpaired quotes
    surrounding it if the draw form had any.

    Parameters
    ----------
    raw_str
        Raw form of the incomplete text.

    parsed_str
        Parsed form of the raw incomplete text.
    """

    __slots__ = ("raw_str", "parsed_str")

    def __init__(self, raw_str: str, parsed_str: str) -> None:
        """Initializes the `Incomplete` class."""

        self.raw_str = raw_str.strip()
        """Raw form of the incomplete text."""

        self.parsed_str = parsed_str
        """Parsed form of the raw incomplete text."""

    def __str__(self) -> str:
        return self.parsed_str

    def __repr__(self) -> str:
        return repr(self.parsed_str)

    def __bool__(self) -> bool:
        return bool(self.raw_str)

    def __len__(self) -> int:
        return len(self.parsed_str)

    def expand_envvars(self) -> str:
        """
        Expands Environmental variables in :attr:`~.parsed_str` and returns
        it as a new string.

        Returns
        -------
        str
            String with all the Environmental in :attr:`~.parsed_str`
            variables expanded.
        """
        return os.path.expandvars(os.path.expanduser(self.parsed_str)).strip()


class ReplInputState:
    """
    Describes about the current input state of the text in the current prompt.
    It includes the details about the current click group, command and parameter
    the user is requesting autocompletions for.

    Parameters
    ----------
    cli_ctx
        The click context object of the main group.

    current_ctx
        The most recently created click context object, after parsing :attr:`~.args`.

    args
        List of text that's entered in the prompt.
    """

    __slots__ = (
        "current_ctx",
        "cli_ctx",
        "args",
        "current_group",
        "current_command",
        "current_param",
        "remaining_params",
        "double_dash_found",
    )

    def __init__(
        self,
        cli_ctx: Context,
        current_ctx: Context,
        args: tuple[str, ...],
    ) -> None:
        """
        Initializes the `ReplInputState` class.
        """

        self.cli_ctx = cli_ctx
        """The click context object of the main group."""

        self.current_ctx = current_ctx
        """
        The most recently created click context object,
        after parsing :attr:`~.args`
        """

        self.args = args
        """List of text that's entered into the prompt."""

        self.remaining_params: list[Parameter] = []
        """List of unused parameters of the current command."""

        self.double_dash_found = getattr(current_ctx, "_double_dash_found", False)
        """Determines whether there's a ``'--'`` in :attr:`~.args`."""

        current_group, current_command, current_param = self.parse()

        self.current_group = current_group
        """The current click group the user is in."""

        self.current_command = current_command
        """The current click command the user is in."""

        self.current_param = current_param
        """The current click parameter the user is on."""

    def __str__(self) -> str:
        res = [str(self.current_group.name)]

        cmd = getattr(self.current_command, "name", None)
        if cmd is not None:
            res.append(cmd)

        param = getattr(self.current_param, "name", None)
        if param is not None:
            if len(res) == 1:
                res.append("None")
            res.append(param)

        return " > ".join(res)

    def __repr__(self) -> str:
        return f'"{str(self)}"'

    def parse(self) -> tuple[Group, Command | None, Parameter | None]:
        """
        Parse the :attr`~.current_ctx` and returns the current click group, command
        and paramter that's been requested in the prompt.

        Returns
        -------
        tuple[Group,Command | None,Parameter | None]
            The current click group, command and parameter, if requested, in the prompt.
        """
        current_group, current_command = self.get_current_group_and_command()
        current_param = None

        if current_command is not None:
            current_param = self.get_current_param(current_command)

        return current_group, current_command, current_param

    def get_current_group_and_command(self) -> tuple[Group, Command | None]:
        """
        Parse the :attr:`~.current_ctx` and returns the current click group
        and command that's been requested in the prompt.

        Returns
        -------
        tuple[Group,Command | None]
            The current click group and command, if requested, in the prompt.
        """
        current_ctx_command = self.current_ctx.command

        current_group = current_ctx_command
        current_command = None

        if current_ctx_command == self.cli_ctx.command:
            return current_group, current_command  # type:ignore[return-value]

        # If parent ctx exist, we change current_group to the parent ctx's command.
        if self.current_ctx.parent is not None:
            current_group = self.current_ctx.parent.command

        current_group = cast(Group, current_group)

        cmd_arguments_list = [
            param
            for param in current_ctx_command.params
            if isinstance(param, click.Argument)
        ]

        all_arguments_got_values = all(
            not is_param_value_incomplete(self.current_ctx, param)
            for param in cmd_arguments_list
        )

        has_incomplete_args = not (cmd_arguments_list and all_arguments_got_values)

        if isinstance(current_ctx_command, click.Group) and all_arguments_got_values:
            # Promote the current command as current group, only if it
            # has got values to all of its click.Argument type args.
            current_group = current_ctx_command

        elif not current_group.chain or (
            current_ctx_command.params and has_incomplete_args
        ):
            current_command = current_ctx_command

        return current_group, current_command

    def get_current_param(self, current_command: Command) -> Parameter | None:
        """
        Parse the :attr:`~.current_ctx` and returns the current click parameter
        from the given :attr:`~.current_command` that's been requested in the prompt.

        Parameters
        ----------
        current_command
            The current click command.

        Returns
        -------
        Parameter | None
            The current click parameter, if requested, in the prompt.
        """
        self.remaining_params = [
            param
            for param in current_command.params
            if is_param_value_incomplete(self.current_ctx, param)
        ]

        return self.get_current_opt(current_command) or self.get_current_arg(
            current_command
        )

    def get_current_opt(self, current_command: Command) -> click.Option | None:
        """
        Parse the :attr:`~.current_ctx` and returns the current click option
        from the given :attr:`~.current_command` that's been requested in the prompt.

        Parameters
        ----------
        current_command
            The current click command.

        Returns
        -------
        click.Option | None
            The current click option, if requested, in the prompt.
        """
        if "--" in self.args:
            # click parses all input strings after "--" as values for click.Argument
            # type parameters. So, we don't check for click.Optional parameters.
            return None

        for param in current_command.params:
            if not isinstance(param, click.Option):
                continue

            if param.is_flag or param.count:
                continue

            opts = param.opts + param.secondary_opts
            current_args_for_param = self.args[param.nargs * -1 :]

            if any(opt in current_args_for_param for opt in opts):
                # We want to make sure if this parameter was called
                # If we are inside a parameter that was called, we want
                # to show only relevant choices
                return param

        return None

    def get_current_arg(self, current_command: Command) -> click.Argument | None:
        """
        Parse the :attr:`~.current_ctx` and returns the current click argument
        from the given :attr:`~.current_command` that's been requested in the prompt.

        Parameters
        ----------
        current_command
            The current click command.

        Returns
        -------
        click.Argument | None
            The current click argument, if requested, in the prompt.
        """
        for param in iterate_command_params(current_command):
            if not isinstance(param, click.Argument):
                continue

            elif is_param_value_incomplete(self.current_ctx, param):
                return param

        return None


@lru_cache(maxsize=3)
def _resolve_incomplete(document_text: str) -> tuple[tuple[str, ...], Incomplete]:
    """
    Resolves the last incomplete string token from the prompt to
    generate suggestions based on it.

    Parameters
    ----------
    document_text
        The text currently in the prompt.

    Returns
    -------
    tuple[tuple[str,...],Incomplete]
        A tuple that containing:
            - A list of text, lexically split from the text in prompt.
            - An Incomplete object that has the recent incomplete text token.
    """

    # Expand environmental variables in the input text.
    args = split_arg_string(document_text)

    # Assess and retrieve the last incomplete text in the prompt.
    cursor_within_command = not document_text[-1:].isspace()

    if args and cursor_within_command:
        incomplete = args.pop()
    else:
        incomplete = ""

    # Check if the 'incomplete' resembles an option name, and has an '=' after that
    # option name. If yes, split it and append the option name to args, and use the
    # incomplete text's explicit value as the new incomplete text.
    equal_sign_match = _EQUALS_SIGN_AFTER_OPT_FLAG.match(incomplete)

    if equal_sign_match:
        opt, _, incomplete = equal_sign_match.groups()
        args.append(opt)

    _args = tuple(args)

    # If the user hasn't requested anything with an incomplete text,
    # No need to resolve the incomplete text anymore further.
    if not incomplete:
        return _args, Incomplete("", "")

    # Retrieve the last incomplete token from the raw text from the prompt to
    # reference it to calculate its length and insert the suggestions
    # from the prompt at the right place. This step is done especially to
    # handle incomplete texts that has unclosed quotes.

    raw_incomplete_with_quotes = ""
    secondary_check = False

    args_splitted_by_space = document_text.split(" ")

    # Handles the equals sign with option name as its prefix condition.
    if equal_sign_match:
        args_splitted_by_space.pop()
        args_splitted_by_space.extend([args[-1], incomplete])

    for token in reversed(args_splitted_by_space):
        _tmp = f"{token} {raw_incomplete_with_quotes}".rstrip()

        if _tmp.translate(_quotes_to_empty_str_dict).strip() == incomplete:
            secondary_check = True

        elif secondary_check:
            break

        raw_incomplete_with_quotes = _tmp

    return _args, Incomplete(raw_incomplete_with_quotes, incomplete)


@lru_cache(maxsize=3)
def _resolve_repl_input_state(
    cli_ctx: Context,
    current_ctx: Context,
    args: tuple[str, ...],
) -> ReplInputState:
    """
    Initializes :class:`~click_repl.parser.ReplInputState` class if its arguments
    are not cached. Otherwise, returns the cached ReplInputState object.

    Parameters
    ----------
    cli_ctx
        The click context object of the parent group.

    current_ctx
        The current click context object.

    args
        Tuple of strings containing the arguments.

    Returns
    -------
    ReplInputState
        Object that describes the current input state.
    """
    return ReplInputState(cli_ctx, current_ctx, args)


@lru_cache(maxsize=3)
def _resolve_state(
    ctx: Context, document_text: str
) -> tuple[Context, ReplInputState, Incomplete]:
    """
    Resolves the input state of the arguments in the REPL prompt.

    Parameters
    ----------
    ctx
        The current context object of the parent group.

    document_text
        The text currently in the prompt.

    Returns
    -------
    tuple[Context,ReplInputState,Incomplete]
        A tuple that contains:
            - click context object constructed from parsing the given input from prompt.
            - Current REPL input state object.
            - Object that holds the incomplete text token that requires suggestions.
    """
    args, incomplete = _resolve_incomplete(document_text)
    parsed_ctx = _resolve_context(ctx, args)
    state = _resolve_repl_input_state(ctx, parsed_ctx, args)

    return parsed_ctx, state, incomplete
