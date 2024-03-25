"""
`click_repl.completer`

Configuration for auto-completion for REPL.
"""

from __future__ import annotations

import typing as t
from collections.abc import Generator
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Tuple

import click
from click import Command
from click import Context
from click import MultiCommand
from click import Parameter
from click.types import ParamType
from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.completion import Completer
from prompt_toolkit.completion import Completion
from prompt_toolkit.document import Document
from typing_extensions import Final
from typing_extensions import TypeAlias
from typing_extensions import TypedDict

from ._formatting import TokenizedFormattedText
from ._globals import _PATH_TYPES
from ._globals import AUTO_COMPLETION_FUNC_ATTR
from ._globals import CLICK_REPL_DEV_ENV
from ._globals import HAS_CLICK_GE_8
from ._globals import IS_WINDOWS
from ._globals import ISATTY
from ._globals import StyleAndTextTuples
from ._globals import get_current_repl_ctx
from ._internal_cmds import InternalCommandSystem
from .bottom_bar import BottomBar
from .parser import Incomplete
from .parser import ReplParsingState
from .utils import CompletionStyleDictKeys
from .utils import _get_visible_subcommands
from .utils import _is_help_option
from .utils import _quotes
from .utils import _resolve_state
from .utils import get_option_flag_sep
from .utils import get_token_type
from .utils import is_param_value_incomplete
from .utils import join_options
from .utils import options_flags_joiner


class _CompletionStyleDict(TypedDict):
    completion_style: str
    selected_completion_style: str


CompletionStyleDict: TypeAlias = Dict[CompletionStyleDictKeys, _CompletionStyleDict]


__all__ = ["ClickCompleter", "ReplCompletion"]


class ClickCompleter(Completer):
    """
    Custom prompt Completion provider for the click-repl app.

    Parameters
    ----------
    ctx : `click.Context`
        The current click context object.

    bottom_bar : `BottomBar`, optional
        Object thats used to update the text displayed in the bottom bar.

    internal_commands_system : `InternalCommandSystem`
        Object that holds information about the internal commands and their prefixes.

    shortest_opts_only : bool, default=False
        Determines whether only the shortest flag of an option parameter
        is used for auto-completion.

        It is utilized when the user is requesting option flags without
        providing any text. They are not considered for flag options.

    show_only_unused_opts : bool, default=False
        Determines whether the options that are already mentioned or
        used in the current prompt will be displayed during auto-completion.

    show_hidden_commands : bool, default=False
        Determines whether the hidden commands should be shown
        in autocompletion or not.

    show_hidden_params : bool, default=False
        Determines whether the hidden parameters should be shown
        in autocompletion or not.

    expand_envvars : bool, default=False
        Determines whether to return completion with Environmental variables
        as expanded or not.

    style : A Dictionary of `str: str` pairs
        A dictionary denoting different styles for
        `prompt_toolkit.completion.Completion` objects for
        `'command'`, `'argument'`, and `'option'`.
    """

    def __init__(
        self,
        ctx: Context,
        internal_commands_system: InternalCommandSystem,
        bottom_bar: BottomBar | None = None,
        shortest_opts_only: bool = False,
        show_only_unused_opts: bool = False,
        show_hidden_commands: bool = False,
        show_hidden_params: bool = False,
        expand_envvars: bool = False,
        style: CompletionStyleDict | None = None,
    ) -> None:
        self.cli_ctx: Final[Context] = ctx
        self.cli: Final[MultiCommand] = self.cli_ctx.command  # type: ignore[assignment]

        if ISATTY:
            self.bottom_bar = bottom_bar

        else:
            self.bottom_bar = None

        self.shortest_opts_only = shortest_opts_only
        self.show_only_unused_opts = show_only_unused_opts

        self.show_hidden_commands = show_hidden_commands
        self.show_hidden_params = show_hidden_params
        self.expand_envvars = expand_envvars

        # if internal_commands_system is None:
        #     internal_commands_system = InternalCommandSystem(None, None)

        self.internal_commands_system = internal_commands_system

        if style is None:
            style = t.cast(
                CompletionStyleDict,
                {
                    "internal-command": {
                        "completion_style": "",
                        "selected_completion_style": "",
                    },
                    "command": {"completion_style": "", "selected_completion_style": ""},
                    "multicommand": {
                        "completion_style": "",
                        "selected_completion_style": "",
                    },
                    "argument": {"completion_style": "", "selected_completion_style": ""},
                    "option": {"completion_style": "", "selected_completion_style": ""},
                },
            )

        self.style = style

    def get_completions_for_internal_commands(
        self, prefix: str, incomplete: str
    ) -> Iterator[Completion]:
        """
        Generates auto-completions based on the given prefix present
        in the current incomplete prompt.

        Parameters
        ----------
        prefix : str
            The prefix string thats present in the start of the prompt.

        incomplete : `Incomplete`
            An object that holds the unfinished string in the REPL prompt,
            and its parsed state, that requires further input or completion.

        Yields
        ------
        `prompt_toolkit.completion.Completion`
            The `Completion` objects thats sent for auto-completion
            of the incomplete prompt.
        """

        incomplete = incomplete.strip()[len(prefix) :].lstrip().lower()
        info_table = (
            self.internal_commands_system._group_commands_by_callback_and_description()
        )

        internal_cmd_style = self.style["internal-command"]
        completion_style = internal_cmd_style["completion_style"]
        selected_style = internal_cmd_style["selected_completion_style"]

        for (_, desc), aliases in info_table.items():
            aliases_start_with_incomplete = [
                alias
                for alias in aliases
                if alias.startswith(incomplete) and alias != incomplete
            ]

            if aliases_start_with_incomplete:
                display = options_flags_joiner(
                    aliases,
                    "parameter.option.name",
                    "parameter.option.name.separator",
                    "/",
                )

                yield ReplCompletion(
                    aliases_start_with_incomplete[0],
                    incomplete,
                    display=TokenizedFormattedText(display, "autocompletion-menu"),
                    display_meta=desc,
                    quote=False,
                    style=completion_style,
                    selected_style=selected_style,
                )

    def get_completion_from_autocompletion_functions(
        self,
        ctx: Context,
        param: Parameter,
        state: ReplParsingState,
        incomplete: Incomplete,
        param_type: ParamType | None = None,
    ) -> Iterator[Completion]:
        """
        Generates auto-completions based on the output from the command's
        `shell_complete` or `autocompletion` function of the current parameter.
        """

        # click < v8 has a different name for their shell_complete
        # function, and its called "autocompletion". So, for backwards
        # compatibility, we're calling them based on the click's version.

        if HAS_CLICK_GE_8:
            if param_type is None:
                autocompletions = param.shell_complete(ctx, incomplete.parsed_str)

            else:
                autocompletions = param_type.shell_complete(
                    ctx, param, incomplete.parsed_str
                )

        else:
            autocompletions = param.autocompletion(  # type: ignore[attr-defined]
                ctx, state.args, incomplete.parsed_str
            )

        param_style = self.style[get_token_type(param)]
        completion_style = param_style["completion_style"]
        selected_style = param_style["selected_completion_style"]

        for autocomplete in autocompletions:
            if isinstance(autocomplete, tuple):
                yield ReplCompletion(
                    autocomplete[0],
                    incomplete,
                    display_meta=autocomplete[1],
                    style=param_style["completion_style"],
                    selected_style=param_style["selected_completion_style"],
                )

            elif HAS_CLICK_GE_8 and isinstance(
                autocomplete, click.shell_completion.CompletionItem
            ):
                yield ReplCompletion(
                    autocomplete.value,
                    incomplete,
                    style=completion_style,
                    selected_style=selected_style,
                )

            elif isinstance(autocomplete, Completion):
                yield autocomplete

            else:
                yield ReplCompletion(
                    str(autocomplete),
                    incomplete,
                    style=completion_style,
                    selected_style=selected_style,
                )

    def get_completion_from_choices_type(
        self, param: Parameter, param_type: click.Choice, incomplete: Incomplete
    ) -> Iterator[Completion]:
        """
        Generates auto-completions based on data from the given
        `click.Choice` parameter type of a parameter.

        This method is used for backwards compatibility with click v7
        as `click.Choice` class didn't have a `shell_complete` method
        until click v8.

        Parameters
        ----------
        param : `click.Parameter`
            A `click.Parameter` object which is referred to generate
            auto-completions.

        param_type : `click.Choice`
            The click paramtype object of a parameter, to which the choice
            auto-completions should be generated.

        incomplete : `Incomplete`
            An object that holds the unfinished string in the REPL prompt,
            and its parsed state, that requires further input or completion.

        Yields
        ------
        `prompt_toolkit.completion.Completion`
            The `Completion` objects thats sent for auto-completion
            of the incomplete prompt, based on the given parameter type.
        """

        case_insensitive = not param_type.case_sensitive

        _incomplete = incomplete.expand_envvars()

        if case_insensitive:
            _incomplete = _incomplete.lower()

        param_style = self.style[get_token_type(param)]
        completion_style = param_style["completion_style"]
        selected_style = param_style["selected_completion_style"]

        for choice in param_type.choices:
            _choice = choice.lower() if case_insensitive else choice

            if _choice.startswith(_incomplete):
                # if not self.expand_envvars:
                #     choice = incomplete.parsed_str + choice[len(_incomplete) :]

                yield ReplCompletion(
                    choice,
                    incomplete,
                    style=completion_style,
                    selected_style=selected_style,
                )

    def get_completion_for_path_types(
        self,
        param: Parameter,
        param_type: click.Path | click.File,
        incomplete: Incomplete,
    ) -> Iterator[Completion]:
        """
        Generates auto-completions for `click.Path` and `click.File` type parameters
        based on the given incomplete path string.

        Parameters
        ----------
        param : `click.Parameter`
            A `click.Parameter` object which is referred to generate
            auto-completions.

        param_type : `click.Path` or `click.File`
            The click paramtype object of a parameter, to which the path
            auto-completions should be generated.

        incomplete : `Incomplete`
            An unfinished object that holds the path string in the REPL prompt,
            and its parsed state, that requires further input or completion.

        Yields
        ------
        `prompt_toolkit.completion.Completion`
            The `Completion` objects thats sent for auto-completion
            of the incomplete prompt.
        """

        _incomplete: str = incomplete.expand_envvars()

        if "*" in _incomplete:
            return

        search_pattern = _incomplete.strip("\"'") + "*"
        temp_path_obj = Path(search_pattern)

        param_style = self.style[get_token_type(param)]
        completion_style = param_style["completion_style"]
        selected_style = param_style["selected_completion_style"]

        for path in temp_path_obj.parent.glob(temp_path_obj.name):
            if param_type.name == "directory" and path.is_file():
                continue

            if path.is_dir():
                path_style = "parameter.type.path.directory"

            else:
                path_style = "parameter.type.path.file"

            path_str = str(path)

            if IS_WINDOWS:
                path_str = path_str.replace("\\\\", "\\")

            # if path.is_dir():
            #     path_str += os.path.sep

            if not self.expand_envvars:
                path_str = incomplete.reverse_prefix_envvars(path_str)

            yield ReplCompletion(
                path_str,
                incomplete,
                display=TokenizedFormattedText(
                    [(path_style, path.name)], "autocompletion-menu"
                ),
                start_position=-len(incomplete.raw_str),
                style=completion_style,
                selected_style=selected_style,
            )

    def get_completion_for_boolean_type(
        self, param: Parameter, incomplete: Incomplete
    ) -> Iterator[Completion]:
        """
        Generates auto-completions for boolean type parameter
        based on the given incomplete string.

        Parameters
        ----------
        param : `click.Parameter`
            A `click.Parameter` object which is referred to generate
            auto-completions.

        incomplete : `Incomplete`
            An object that holds the unfinished string in the REPL prompt,
            and its parsed state, that requires further input or completion.

        Yields
        ------
        `prompt_toolkit.completion.Completion`.
            The `Completion` objects thats sent for auto-completion
            of the incomplete prompt.
        """

        _incomplete = incomplete.expand_envvars()

        boolean_mapping: dict[str, Tuple[str, ...]] = {
            "true": ("1", "true", "t", "yes", "y", "on"),
            "false": ("0", "false", "f", "no", "n", "off"),
        }

        param_style = self.style[get_token_type(param)]
        completion_style = param_style["completion_style"]
        selected_style = param_style["selected_completion_style"]

        for value, aliases in boolean_mapping.items():
            if any(alias.startswith(_incomplete) for alias in aliases):
                if not self.expand_envvars:
                    value = incomplete.reverse_prefix_envvars(value)

                yield ReplCompletion(
                    value,
                    incomplete,
                    display=TokenizedFormattedText(
                        [(f"parameter.type.bool.to{value}", value)], "autocompletion-menu"
                    ),
                    display_meta="/".join(aliases),
                    style=completion_style,
                    selected_style=selected_style,
                )

    def get_completion_from_param_type(
        self,
        ctx: Context,
        param: Parameter,
        param_type: ParamType,
        state: ReplParsingState,
        incomplete: Incomplete,
    ) -> Iterator[Completion]:
        """
        Generates auto-completions based on the given `param_type` object
        of the given parameter `param`.

        Parameters
        ----------
        param : `click.Parameter`
            A `click.Parameter` object which is referred to generate
            auto-completions.

        param_type : `click.types.ParamType`
            The click patamtype object object of a parameter, to which
            appropriate auto-completions should've to be generated.

        state : `ReplParsingState`
            An ReplParsingState object that contains information about
            the parsing state of the parameters of the current command.

        incomplete : `Incomplete`
            An object that holds the unfinished string in the REPL prompt,
            and its parsed state, that requires further input or completion.

        Yields
        ------
        `prompt_toolkit.completion.Completion`
            The `Completion` objects thats sent for auto-completion
            of the incomplete prompt.
        """

        if isinstance(param_type, click.Tuple):
            values = state.current_ctx.params[param.name]  # type: ignore[index]
            if None in values:
                yield from self.get_completion_from_param_type(
                    ctx, param, param_type.types[values.index(None)], state, incomplete
                )

        # shell_complete method for click.Choice class is introduced in click-v8.
        # So, we're implementing shell_complete for Choice, exclusively.
        elif isinstance(param_type, click.Choice):
            yield from self.get_completion_from_choices_type(
                param, param_type, incomplete
            )

        elif isinstance(param_type, click.types.BoolParamType):
            yield from self.get_completion_for_boolean_type(param, incomplete)

        elif isinstance(param_type, _PATH_TYPES):
            # Both click.Path and click.File types are expected
            # to receive input as a path string.
            yield from self.get_completion_for_path_types(param, param_type, incomplete)

        elif HAS_CLICK_GE_8:
            yield from self.get_completion_from_autocompletion_functions(
                ctx, param, state, incomplete, param_type
            )

    def get_completion_from_param(
        self,
        ctx: Context,
        param: Parameter,
        state: ReplParsingState,
        incomplete: Incomplete,
    ) -> Iterator[Completion]:
        """
        Generates auto-completions based on the given parameter.

        Parameters
        ----------
        ctx : `click.Context`
            A click context object that contains information about the
            current command and its parameters based on the input in the
            REPL prompt.

        param : `click.Parameter`
            A `click.Parameter` object which is referred to generate
            auto-completions.

        state : `ReplParsingState`
            A `ReplParsingState` object that contains information about the
            parsing state of the parameters of the current command
            based on the text in the prompt.

        incomplete : `Incomplete`
            An object that holds the unfinished string in the REPL prompt,
            and its parsed state, that requires further input or completion.

        Yields
        ------
        `prompt_toolkit.completion.Completion`
            The `Completion` objects that's sent for auto-completion of the
            incomplete prompt, based on the given parameter.
        """

        param_type = param.type

        if getattr(param, AUTO_COMPLETION_FUNC_ATTR, None) is not None:
            yield from self.get_completion_from_autocompletion_functions(
                ctx, param, state, incomplete
            )

        elif not isinstance(
            param_type, (click.types.StringParamType, click.types.UnprocessedParamType)
        ):
            yield from self.get_completion_from_param_type(
                ctx, param, param_type, state, incomplete
            )

        return

    def get_completions_for_joined_boolean_option_flags(
        self,
        ctx: Context,
        option: click.Option,
        state: ReplParsingState,
        incomplete: Incomplete,
    ) -> Iterator[Completion]:
        # Display coloured option flags, only if there are
        # any exclusive flags to pass in the False'y value

        for flags_list, bool_val in zip(
            [option.opts, option.secondary_opts], ["true", "false"]
        ):
            # The primary flags are assigned for the boolean value of "True",
            # And "False" for secondary flags, despite the default value.

            item_token = f"parameter.type.bool.to{bool_val}"

            display_lst = options_flags_joiner(
                flags_list,
                item_token,
                f"parameter.option.name.separator,{item_token}",
                get_option_flag_sep(flags_list),
            )

            yield ReplCompletion(
                min(flags_list, key=len),
                incomplete,
                display=TokenizedFormattedText(display_lst, "autocompletion-menu"),
                display_meta=option.help or "",
            )

    def get_completion_for_option_flags(
        self,
        ctx: Context,
        command: Command,
        state: ReplParsingState,
        incomplete: Incomplete,
    ) -> Iterator[Completion]:
        """
        Generates auto-completions for option flags based on the given command.

        Parameters
        ----------
        ctx : `click.Context`
            A click context object that contains information about the
            current command and its parameters based on the input in the
            REPL prompt.

        command : `click.Command`
            A click command object, which is referred to generate auto-completions
            based on its parameters.

        state : `ReplParsingState`
            A `ReplParsingState` object that contains information about the
            parsing state of the parameters of the current command
            based on the text in the prompt.

        incomplete : `Incomplete`
            An object that holds the unfinished string in the REPL prompt,
            and its parsed state, that requires further input or completion.

        Yields
        ------
        `prompt_toolkit.completion.Completion`
            The `Completion` objects thats sent for auto-completion of the
            incomplete prompt, based on the given parameter.
        """

        _incomplete = incomplete.parsed_str

        for option in command.params:
            if not isinstance(option, click.Option):
                continue

            if option.hidden and not self.show_hidden_params:
                continue

            already_used = not is_param_value_incomplete(ctx, option.name)

            if option.is_flag and already_used:
                continue

            hide = (
                self.show_only_unused_opts
                and already_used
                and not (option.multiple or option.count)
            )

            if hide:
                continue

            is_shortest_opts_only = self.shortest_opts_only and not _incomplete

            if is_shortest_opts_only and option.is_bool_flag and option.secondary_opts:
                yield from self.get_completions_for_joined_boolean_option_flags(
                    ctx, option, state, incomplete
                )
                continue

            option_flags = option.opts + option.secondary_opts

            flags_that_start_with_incomplete = [
                opt for opt in option_flags if opt.startswith(_incomplete)
            ]

            if not flags_that_start_with_incomplete:
                continue

            flag_token = "parameter.option.name"

            if is_shortest_opts_only:
                option_flags, sep = join_options(flags_that_start_with_incomplete)

                def display_text_func(flag_token: str) -> StyleAndTextTuples:
                    if not flag_token.startswith("parameter.option.name"):
                        flag_token = f"parameter.option.name.separator,{flag_token}"

                    return options_flags_joiner(option_flags, flag_token, flag_token, sep)

                flags_that_start_with_incomplete = [
                    min(flags_that_start_with_incomplete, key=len)
                ]

            for option_flag in flags_that_start_with_incomplete:
                if not is_shortest_opts_only:

                    def display_text_func(flag_token: str) -> StyleAndTextTuples:
                        return [(flag_token, option_flag)]

                if option.is_bool_flag and not _is_help_option(option):
                    if option.secondary_opts:
                        # Display coloured option flags, only if there're
                        # any exclusive flags to pass in the False'y value
                        bool_opt_value: bool = option_flag in option.opts

                    else:
                        bool_opt_value = option.flag_value

                    flag_token = f"parameter.type.bool.to{bool_opt_value}"

                yield ReplCompletion(
                    option_flag,
                    incomplete,
                    display=TokenizedFormattedText(
                        display_text_func(flag_token), "autocompletion-menu"
                    ),
                    display_meta=option.help or "",
                )

    def get_completion_for_command_arguments(
        self,
        ctx: Context,
        command: Command,
        state: ReplParsingState,
        incomplete: Incomplete,
    ) -> Iterator[Completion]:
        """
        Generates auto-completions to display the flags of the options
        based on the given command object.

        Parameters
        ----------
        ctx : `click.Context`
            A click context object that contains information about the
            current command and its parameters based on the input in the
            REPL prompt.

        command : `click.Command`
            A click command object, which is referred to generate auto-completions
            based on its parameters.

        state : `ReplParsingState`
            A `ReplParsingState` object that contains information about the
            parsing state of the parameters of the current command
            based on the text in the prompt.

        incomplete : `Incomplete`
            An object that holds the unfinished string in the REPL prompt,
            and its parsed state, that requires further input or completion.

        Yields
        ------
        `prompt_toolkit.completion.Completion`
            The `Completion` objects thats sent
            for auto-completion of the incomplete prompt.
        """

        current_param = state.current_param
        _incomplete_prefix = incomplete.expand_envvars()[:2]

        current_argument_havent_received_values = isinstance(
            current_param, click.Argument
        ) and is_param_value_incomplete(
            ctx, current_param.name, check_if_tuple_has_none=False
        )

        ctx_opt_prefixes: set[str] = getattr(ctx, "_opt_prefixes", set())

        interspersed_args_available = (
            not state.current_group.chain
            and not current_param
            and ctx.allow_interspersed_args
            and any(_incomplete_prefix.startswith(i) for i in ctx_opt_prefixes)
        )

        prompt_requires_option_flags_suggestions = (
            not current_param
            or current_argument_havent_received_values
            or interspersed_args_available
            and not state.double_dash_found
        )

        if prompt_requires_option_flags_suggestions:
            yield from self.get_completion_for_option_flags(
                ctx, command, state, incomplete
            )

        allow_current_hidden_param = (
            not getattr(current_param, "hidden", False) or self.show_hidden_params
        )

        if current_param and allow_current_hidden_param:
            # If the current param is not None and it's not a hidden param,
            # or if the current param is a hidden param and
            # self.show_completions_for_hidden_param is true,
            # generate auto-completion for it.
            yield from self.get_completion_from_param(
                ctx, current_param, state, incomplete
            )

    def check_for_command_arguments_request(
        self, ctx: Context, state: ReplParsingState, incomplete: Incomplete
    ) -> bool:
        """
        Determines whether the user has requested auto-completions for the
        given command's parameter.

        Parameters
        ----------
        ctx : `click.Context`
            A click context object that contains information about the
            current command and its parameters based on the input in the
            REPL prompt.

        state : `ReplParsingState`
            A `ReplParsingState` object that contains information about the
            parsing state of the parameters of the current command
            based on the text in the prompt.

        incomplete : `Incomplete`
            An object that holds the unfinished string in the REPL prompt,
            and its parsed state, that requires further input or completion.

        Returns
        -------
        bool
            Whether to generate auto-completions for the parameters of the
            given function or not.
        """
        current_command = state.current_command
        args_list = [
            param for param in ctx.command.params if isinstance(param, click.Argument)
        ]

        incomplete_visible_args = not args_list or any(
            is_param_value_incomplete(ctx, param.name) for param in args_list
        )

        # If there's a sub-command found in the state object,
        # generate completions for its arguments.
        is_chained_command = state.current_group.chain or getattr(
            ctx.command, "chain", False
        )

        is_current_command_a_group_or_none = current_command is None or isinstance(
            current_command, click.MultiCommand
        )

        return ctx.command != self.cli and (
            incomplete_visible_args
            or not (is_chained_command or is_current_command_a_group_or_none)
        )

    def get_multicommand_for_generating_subcommand_completions(
        self, ctx: Context, state: ReplParsingState, incomplete: Incomplete
    ) -> MultiCommand | None:
        """
        Returns the appropriate `click.MultiCommand` object that should be used
        to generate auto-completions for subcommands of a group.

        Parameters
        ----------
        ctx : `click.Context`
            A click context object that contains information about the
            current command and its parameters based on the input in the
            REPL prompt.

        state : `ReplParsingState`
            A `ReplParsingState` object that contains information about the
            parsing state of the parameters of the current command
            based on the text in the prompt.

        incomplete : `Incomplete`
            An object that holds the unfinished string in the REPL prompt,
            and its parsed state, that requires further input or completion.

        Returns
        -------
        MultiCommand, optional
            A click multicommand object, if available, which is supposed to be used for
            generating auto-completion for suggesting its subcommands.
        """
        any_argument_param_incomplete = any(
            is_param_value_incomplete(ctx, param.name)
            for param in ctx.command.params
            if isinstance(param, click.Argument)
        )

        if any_argument_param_incomplete or state.current_param:
            return None

        if isinstance(ctx.command, click.MultiCommand):
            return ctx.command

        if state.current_group.chain:
            return state.current_group

        return None

    def get_completions_for_subcommands(
        self,
        ctx: Context,
        state: ReplParsingState,
        incomplete: Incomplete,
    ) -> Iterator[Completion]:
        """
        Provides auto-completions for command names, based on the
        current command and group.

        Parameters
        ----------
        ctx : `click.Context`
            A click context object that contains information about the
            current command and its parameters based on the input in the
            REPL prompt.

        state : `ReplParsingState`
            A `ReplParsingState` object that contains information about the
            parsing state of the parameters of the current command
            based on the text in the prompt.

        incomplete : `Incomplete`
            An object that holds the unfinished string in the REPL prompt,
            and its parsed state, that requires further input or completion.

        Yields
        ------
        `prompt_toolkit.completion.Completion`
            The `Completion` objects thats sent for auto-completion
            of the incomplete prompt.
        """

        if self.check_for_command_arguments_request(ctx, state, incomplete):
            yield from self.get_completion_for_command_arguments(
                ctx, ctx.command, state, incomplete
            )

        multicommand = self.get_multicommand_for_generating_subcommand_completions(
            ctx, state, incomplete
        )

        if multicommand is None:
            return

        _incomplete = incomplete.parsed_str

        for name, command in _get_visible_subcommands(
            ctx, multicommand, _incomplete, self.show_hidden_commands
        ):
            cmd_token_type = get_token_type(command)

            cmd_style = self.style[cmd_token_type]
            completion_style = cmd_style["completion_style"]
            selected_style = cmd_style["selected_completion_style"]

            yield ReplCompletion(
                name,
                incomplete,
                display=TokenizedFormattedText(
                    [(f"class:{cmd_token_type}.name", name)], "autocompletion-menu"
                ),
                display_meta=command.get_short_help_str(),
                style=completion_style,
                selected_style=selected_style,
            )

    def handle_internal_commands_request(
        self, document_text: str
    ) -> Generator[Completion, None, bool]:
        flag, ics_prefix = self.internal_commands_system.get_prefix(document_text)

        internal_cmds_requested = flag == "Internal"

        if ics_prefix is not None:
            if ISATTY and self.bottom_bar is not None:
                self.bottom_bar.reset_state()

            if internal_cmds_requested:
                yield from self.get_completions_for_internal_commands(
                    ics_prefix, document_text
                )

        return internal_cmds_requested

    def get_completions(
        self, document: Document, complete_event: CompleteEvent | None = None
    ) -> Iterator[Completion]:
        """
        Provides `prompt_toolkit.completion.Completion`
        objects from the obtained current input string in the REPL prompt.

        Parameters
        ----------
        document : `prompt_toolkit.document.Document`
            The `Document` object containing the incomplete command line string.

        complete_event : `prompt_toolkit.completion.CompleteEvent`
            The `CompleteEvent` object of the current prompt.

        Yields
        ------
        `prompt_toolkit.completion.Completion`
            The `Completion` objects for command line autocompletion.
        """

        internal_cmds_requested = yield from self.handle_internal_commands_request(
            document.text_before_cursor
        )

        if internal_cmds_requested:
            return  # type:ignore[unreachable]

        try:
            parsed_ctx, state, incomplete = _resolve_state(
                self.cli_ctx, document.text_before_cursor
            )

            if parsed_ctx.command.hidden and not self.show_hidden_commands:
                # We skip the hidden command if self.show_hidden_commands is False.
                return

            if ISATTY:
                get_current_repl_ctx().update_state(state)  # type:ignore[union-attr]

                if self.bottom_bar is not None:
                    self.bottom_bar.update_state(state)

            yield from self.get_completions_for_subcommands(parsed_ctx, state, incomplete)

        except Exception:
            if CLICK_REPL_DEV_ENV:
                raise


class ReplCompletion(Completion):
    """
    Custom Completion class to generate Completion
    objects with the default settings for proper auto-completion
    in the REPL prompt.

    Parameters
    ----------
    text : str
        The string that should fill into the prompt
        during auto-completion.

    incomplete : `Incomplete`
        The string thats not completed in the prompt.
        It's used to get the `start_position` for the Completion to
        swap text with, in the prompt.

    quote : bool, default=True
        Boolean value to determine whether the given incomplete
        text with space should be double-quoted.

    *args : tuple
        Additional arguments should be passed as keyword arguments to the
        `prompt_toolkit.completion.Completion` class.

    **kwargs : dict, optional
        Extra arguments to `metric`: refer to each metric documentation for a
        list of all possible arguments to the
        `prompt_toolkit.completion.Completion` class.
    """

    def __init__(
        self,
        text: str,
        incomplete: Incomplete | str,
        quote: bool = True,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        if quote:
            text = _quotes(text)

        if isinstance(incomplete, Incomplete):
            incomplete = incomplete.raw_str

        # diff = len(incomplete) - len(text)
        # if diff > 0:
        #     text += " " * diff + "\b" * diff

        kwargs.setdefault("start_position", -len(incomplete))

        super().__init__(text, *args, **kwargs)
