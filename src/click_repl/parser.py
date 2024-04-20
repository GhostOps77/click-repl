"""
Parsing functionalities for the module.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Any, Dict, Optional, Tuple, cast

import click
from click import Command, Context, Group, Parameter
from typing_extensions import TypeAlias

from ._compat import split_arg_string
from .click_utils.shell_completion import _resolve_context
from .click_utils.utils import get_info_dict
from .utils import is_param_value_incomplete, iterate_command_params

InfoDict: TypeAlias = Dict[str, Any]
# Dictionary that has info about the click objects.

_REPL_PARSING_STATE_KEY: TypeAlias = Tuple[
    Optional[InfoDict], Optional[InfoDict], Optional[InfoDict], Tuple[InfoDict, ...]
]
# Tuple that's used for comparing 2 ReplParsingState objects.


_quotes_to_empty_str_dict = str.maketrans(dict.fromkeys("'\"", ""))

# Just gonna assume that people use only '-' and '--' as prefix for option flags
# _EQUALS_SIGN_AFTER_OPT_FLAG = re.compile(r"^(--?[a-z][\w-]*)=(.*)$", re.I)
_EQUALS_SIGN_AFTER_OPT_FLAG = re.compile(
    r"^(([^a-z\d\s])\2?[a-z]+(?:[\w-]+)?)=(.*)$", re.I
)


class Incomplete:
    """
    Stores the last incomplete text token in the current prompt input.
    It stores the incomplete last text token in it's raw form in
    :attr:`.raw_str` attribute, and in it's parsed form in
    :attr:`.parsed_str` attribute. The parsed form has no unpaired quotes
    surrounding it if the raw form had any.

    Parameters
    ----------
    raw_str
        Raw form of the incomplete text.

    parsed_str
        Parsed form of the raw incomplete text.
    """

    __slots__ = ("raw_str", "parsed_str")

    def __init__(self, raw_str: str, parsed_str: str) -> None:
        """Initialize the `Incomplete` class."""

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
        Expands Environmental variables in :attr:`.parsed_str` and returns
        it as a new string.

        Returns
        -------
            String with all the Environmental in :attr:`.parsed_str`
            variables expanded.
        """
        self.parsed_str = os.path.expandvars(os.path.expanduser(self.parsed_str)).strip()
        return self.parsed_str

    def reverse_prefix_envvars(self, value: str) -> str:
        expanded_incomplete = self.expand_envvars()

        if value.startswith(expanded_incomplete):
            value = self.parsed_str + value[len(expanded_incomplete) :]

        return value


class ReplParsingState:
    """
    Describes about the current parsing state of the text in the current prompt.
    It includes the details about the current click :class:`~click.Group`,
    :class:`~click.Command` and :class:`~click.Parameter` the user is requesting
    autocompletions for.

    Parameters
    ----------
    cli_ctx
        The :class:`~click.Context` object of the main group.

    current_ctx
        The most recently created :class:`~click.Context` object, after
        parsing :attr:`.args`.

    args
        List of text that's entered into the prompt.
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
        Initialize the `ReplParsingState` class.
        """

        self.cli_ctx = cli_ctx
        """The :class:`~click.Context` object of the main group."""

        self.current_ctx = current_ctx
        """
        The most recently created :class:`~click.Context` object, after parsing
        :attr:`.args`
        """

        self.args = args
        """List of text that's entered into the prompt."""

        self.remaining_params: list[Parameter] = []
        """List of unused parameters of the current command."""

        self.double_dash_found = getattr(current_ctx, "_double_dash_found", False)
        """Flag that determines whether there's a `'--'` in :attr:`.args`."""

        self.current_group, self.current_command, self.current_param = self.parse()

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

    def __key(self) -> _REPL_PARSING_STATE_KEY:
        keys: list[InfoDict | None] = []

        for i in (
            self.current_group,
            self.current_command,
            self.current_param,
            self.current_ctx,
        ):
            keys.append(None if i is None else get_info_dict(i))

        return (  # type: ignore[return-value]
            *keys,
            tuple(get_info_dict(param) for param in self.remaining_params),
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ReplParsingState):
            return NotImplemented  # type:ignore[no-any-return]
        return self.__key() == other.__key()

    def parse(self) -> tuple[Group, Command | None, Parameter | None]:
        """
        Parse the ``current_ctx`` and returns the current :classs`~click.Group`,
        :class`~click.Command` and :class`~click.Parameter` that's been requested
        in the prompt.

        Returns
        -------
        tuple[Group,Command | None,Parameter | None]
            The current :class:`~click.Group`, current :class:`~click.Command` if
            requested, and current :class:`~click.Parameter` if requested in
            the prompt.
        """
        current_group, current_command = self.get_current_group_and_command()
        current_param = None

        if current_command is not None:
            current_param = self.get_current_param(current_command)

        return current_group, current_command, current_param

    def get_current_group_and_command(self) -> tuple[Group, Command | None]:
        """
        Parse the ``current_ctx`` and returns the current :class:`~click.Group`
        and :class:`~click.Command` that's been requested in the prompt.

        Returns
        -------
        tuple[Group,Command | None]
            The current :class:`~click.Group`, and current
            :class:`~click.Command` if requested in the prompt.
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
            # has got values to all of it's click.Argument type args.
            current_group = current_ctx_command

        elif not current_group.chain or (
            current_ctx_command.params and has_incomplete_args
        ):
            current_command = current_ctx_command

        return current_group, current_command

    def get_current_param(self, current_command: Command) -> Parameter | None:
        """
        Parse the ``current_ctx`` and returns the current :class:`~click.Parameter`
        from the given ``current_command`` that's been requested in the prompt.

        Returns
        -------
        Parameter | None
            The current :class:`~click.Parameter` if requested in the prompt.
        """
        self.remaining_params = [
            param
            for param in current_command.params
            if is_param_value_incomplete(self.current_ctx, param)
        ]

        return self.parse_param_opt(current_command) or self.parse_param_arg(
            current_command
        )

    def parse_param_opt(self, current_command: Command) -> click.Option | None:
        """
        Parse the ``current_ctx`` and returns the current :class:`~click.Option`
        from the given ``current_command`` that's been requested in the prompt.

        Returns
        -------
        click.Option | None
            The current :class:`~click.Option` if requested in the prompt.
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

    def parse_param_arg(self, current_command: Command) -> click.Argument | None:
        """
        Parse the ``current_ctx`` and returns the current :class:`~click.Argument`
        from the given ``current_command`` that's been requested in the prompt.

        Returns
        -------
        click.Argument | None
            The current :class:`~click.Argument` if requested in the prompt.
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
    Resolves the last incomplete string token from the prompt, to use it to
    generate suggestions based on that.

    Parameters
    ----------
    document_text
        The full text that's currently in the prompt.

    Returns
    -------
    tuple[tuple[str,...],Incomplete]
        A tuple that has
        - A list of text, which is splitted from the full text in prompt.

        - An instance of :class:`~
    """
    args = split_arg_string(document_text)
    cursor_within_command = not document_text[-1:].isspace()

    if args and cursor_within_command:
        incomplete = args.pop()
    else:
        incomplete = ""

    equal_sign_match = _EQUALS_SIGN_AFTER_OPT_FLAG.match(incomplete)

    if equal_sign_match:
        opt, _, incomplete = equal_sign_match.groups()
        args.append(opt)

    _args = tuple(args)

    if not incomplete:
        return _args, Incomplete("", "")

    raw_incomplete_with_quotes = ""
    secondary_check = False

    args_splitted_by_space = document_text.split(" ")

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
def _resolve_repl_parsing_state(
    cli_ctx: Context,
    current_ctx: Context,
    args: tuple[str, ...],
) -> ReplParsingState:
    """
    Initializes :class:`.ReplParsingState` class if it's arguments are not in cache.
    Else, returns the previously initialized :class:`.ReplParsingState` object.
    """
    return ReplParsingState(cli_ctx, current_ctx, args)


@lru_cache(maxsize=3)
def _resolve_state(
    ctx: Context, document_text: str
) -> tuple[Context, ReplParsingState, Incomplete]:
    """
    Resolves the parsing state of the arguments in the REPL prompt.

    Parameters
    ----------
    ctx
        The current :class:`click.Context` object of the parent group.

    document_text
        Text that's currently entered in the prompt.

    Returns
    -------
    tuple[Context,ReplParsingState,Incomplete]
        Returns the appropriate `click.Context` constructed from parsing
        the given input from prompt, current :class:`click_repl.parser.ReplParsingState`
        object, and the :class:`click_repl.parser.Incomplete` object that holds the
        incomplete data that requires suggestions.
    """
    args, incomplete = _resolve_incomplete(document_text)
    parsed_ctx = _resolve_context(ctx, args, proxy=True)
    state = _resolve_repl_parsing_state(ctx, parsed_ctx, args)

    return parsed_ctx, state, incomplete
