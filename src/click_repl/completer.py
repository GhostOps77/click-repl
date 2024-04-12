"""
Configuration for auto-completion in the REPL.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

import click
from click import Command, Context, Group, Parameter
from click.types import ParamType
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import AnyFormattedText
from prompt_toolkit.formatted_text import StyleAndTextTuples as ListOfTokens
from typing_extensions import Final

from ._compat import AUTO_COMPLETION_FUNC_ATTR, PATH_TYPES_TUPLE, MultiCommand
from .bottom_bar import BottomBar
from .click_utils import get_option_flag_sep, join_options
from .globals_ import (
    CLICK_REPL_DEV_ENV,
    HAS_CLICK_GE_8,
    IS_WINDOWS,
    ISATTY,
    get_current_repl_ctx,
)
from .internal_commands import InternalCommandSystem
from .parser import Incomplete, ReplParsingState, _resolve_state
from .tokenizer import TokenizedFormattedText, get_token_type, option_flag_tokens_joiner
from .utils import _is_help_option, is_param_value_incomplete

__all__ = ["ClickCompleter", "ReplCompletion"]


class ClickCompleter(Completer):
    """
    Custom prompt Completion provider for the click-repl app.

    Parameters
    ----------
    group_ctx
        The current :class:`click.Context` object.

    bottom_bar
        Object thats used to update the text displayed in the bottom bar.

    internal_commands_system
        Object that holds information about the internal commands and their prefixes.

    shortest_opt_names_only
        Determines whether only the shortest name of an option parameter
        should be used for auto-completion.

        It is utilized when the user is requesting option flags without
        providing any text. They are not considered for option flags.

    show_only_unused_options
        Determines whether the options that are already mentioned or
        used in the current prompt will be displayed during auto-completion.

    show_hidden_commands
        Determines whether the hidden commands should be shown
        in autocompletion or not.

    show_hidden_params
        Determines whether the hidden parameters should be shown
        in autocompletion or not.

    expand_envvars
        Determines whether to return completion with Environmental variables
        as expanded or not.
    """

    def __init__(
        self,
        group_ctx: Context,
        internal_commands_system: InternalCommandSystem,
        bottom_bar: AnyFormattedText | BottomBar = None,
        shortest_opt_names_only: bool = False,
        show_only_unused_options: bool = False,
        show_hidden_commands: bool = False,
        show_hidden_params: bool = False,
        expand_envvars: bool = False,
    ) -> None:
        """
        Initialize the `ClickCompleter` class.
        """
        self.group_ctx: Final[Context] = group_ctx
        self.group: Final[Group] = self.group_ctx.command  # type: ignore[assignment]

        if not ISATTY:
            bottom_bar = None

        self.bottom_bar = bottom_bar

        self.shortest_opt_names_only = shortest_opt_names_only
        self.show_only_unused_options = show_only_unused_options

        self.show_hidden_commands = show_hidden_commands
        self.show_hidden_params = show_hidden_params
        self.expand_envvars = expand_envvars

        self.internal_commands_system = internal_commands_system

        self.parent_token_class_name: str = "autocompletion-menu"
        """Parent class name for tokens that are related to :class:`~ClickCompleter`."""

    def get_completion_from_autocompletion_functions(
        self,
        ctx: Context,
        param: Parameter,
        state: ReplParsingState,
        incomplete: Incomplete,
        param_type: ParamType | None = None,
    ) -> Generator[Completion, None, None]:
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

        for autocomplete in autocompletions:
            if isinstance(autocomplete, tuple):
                yield ReplCompletion(
                    autocomplete[0],
                    incomplete,
                    display_meta=autocomplete[1],
                )

            elif HAS_CLICK_GE_8 and isinstance(
                autocomplete, click.shell_completion.CompletionItem
            ):
                yield ReplCompletion(autocomplete.value, incomplete)

            elif isinstance(autocomplete, Completion):
                yield autocomplete

            else:
                yield ReplCompletion(str(autocomplete), incomplete)

    def get_completion_from_choices_type(
        self, param: Parameter, param_type: click.Choice, incomplete: Incomplete
    ) -> Generator[Completion, None, None]:
        """
        Generates auto-completions based on data from the given
        `click.Choice` parameter type of a parameter.

        This method is used for backwards compatibility with click v7
        as `click.Choice` class didn't have a `shell_complete` method
        until click v8.

        Parameters
        ----------
        param
            A `click.Parameter` object which is referred to generate
            auto-completions.

        param_type
            The click paramtype object of a parameter, to which the choice
            auto-completions should be generated.

        incomplete
            An object that holds the unfinished string in the REPL prompt,
            and its parsed state, that requires further input or completion.

        Yields
        ------
        prompt_toolkit.completion.Completion
            The :class:`prompt_toolkit.completion.Completion`
            objects thats sent for auto-completion
            of the incomplete prompt, based on the given parameter type.
        """

        case_insensitive = not param_type.case_sensitive

        _incomplete = incomplete.expand_envvars()

        if case_insensitive:
            _incomplete = _incomplete.lower()

        for choice in param_type.choices:
            _choice = choice.lower() if case_insensitive else choice

            if _choice.startswith(_incomplete):
                # if not self.expand_envvars:
                #     choice = incomplete.parsed_str + choice[len(_incomplete) :]

                yield ReplCompletion(choice, incomplete)

    def get_completion_for_path_types(
        self,
        param: Parameter,
        param_type: click.Path | click.File,
        incomplete: Incomplete,
    ) -> Generator[Completion, None, None]:
        """
        Generates auto-completions for `click.Path` and `click.File` type parameters
        based on the given incomplete path string.

        Parameters
        ----------
        param
            A `click.Parameter` object which is referred to generate
            auto-completions.

        param_type
            The click paramtype object of a parameter, to which the path
            auto-completions should be generated.

        incomplete
            An unfinished object that holds the path string in the REPL prompt,
            and its parsed state, that requires further input or completion.

        Yields
        ------
        prompt_toolkit.completion.Completion
            The :class:`prompt_toolkit.completion.Completion`
            objects thats sent for auto-completion
            of the incomplete prompt.
        """

        _incomplete: str = incomplete.expand_envvars()

        if "*" in _incomplete:
            return

        search_pattern = _incomplete.strip("\"'") + "*"
        temp_path_obj = Path(search_pattern)

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
                    [(path_style, path.name)], self.parent_token_class_name
                ),
                start_position=-len(incomplete.raw_str),
            )

    def get_completion_for_boolean_type(
        self, param: Parameter, incomplete: Incomplete
    ) -> Generator[Completion, None, None]:
        """
        Generates auto-completions for boolean type parameter
        based on the given incomplete string.

        Parameters
        ----------
        param
            A `click.Parameter` object which is referred to generate
            auto-completions.

        incomplete
            An object that holds the unfinished string in the REPL prompt,
            and its parsed state, that requires further input or completion.

        Yields
        ------
        prompt_toolkit.completion.Completion.
            The :class:`prompt_toolkit.completion.Completion`
            objects thats sent for auto-completion
            of the incomplete prompt.
        """

        _incomplete = incomplete.expand_envvars()

        boolean_mapping: dict[str, tuple[str, ...]] = {
            "true": ("1", "true", "t", "yes", "y", "on"),
            "false": ("0", "false", "f", "no", "n", "off"),
        }

        for value, aliases in boolean_mapping.items():
            if any(alias.startswith(_incomplete) for alias in aliases):
                if not self.expand_envvars:
                    value = incomplete.reverse_prefix_envvars(value)

                yield ReplCompletion(
                    value,
                    incomplete,
                    display=TokenizedFormattedText(
                        [(f"parameter.type.bool.to{value}", value)],
                        self.parent_token_class_name,
                    ),
                    display_meta="/".join(aliases),
                )

    def get_completion_from_param_type(
        self,
        ctx: Context,
        param: Parameter,
        param_type: ParamType,
        state: ReplParsingState,
        incomplete: Incomplete,
    ) -> Generator[Completion, None, None]:
        """
        Generates auto-completions based on the given `param_type` object
        of the given parameter `param`.

        Parameters
        ----------
        param
            A `click.Parameter` object which is referred to generate
            auto-completions.

        param_type
            The click patamtype object object of a parameter, to which
            appropriate auto-completions should've to be generated.

        state
            An ReplParsingState object that contains information about
            the parsing state of the parameters of the current command.

        incomplete
            An object that holds the unfinished string in the REPL prompt,
            and its parsed state, that requires further input or completion.

        Yields
        ------
        prompt_toolkit.completion.Completion
            The :class:`prompt_toolkit.completion.Completion`
            objects thats sent for auto-completion
            of the incomplete prompt.
        """

        if isinstance(param_type, click.Tuple):
            values = state.current_ctx.params[param.name]  # type: ignore[index]
            index_of_none = values.index(None)

            if index_of_none == -1:
                return

            yield from self.get_completion_from_param_type(
                ctx, param, param_type.types[index_of_none], state, incomplete
            )

        # shell_complete method for click.Choice class is introduced in click v8.
        # So, we're implementing shell_complete for Choice, separately.
        elif isinstance(param_type, click.Choice) and not HAS_CLICK_GE_8:
            yield from self.get_completion_from_choices_type(
                param, param_type, incomplete
            )

        elif isinstance(param_type, click.types.BoolParamType):
            yield from self.get_completion_for_boolean_type(param, incomplete)

        elif isinstance(param_type, PATH_TYPES_TUPLE):
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
    ) -> Generator[Completion, None, None]:
        """
        Generates auto-completions based on the given parameter.

        Parameters
        ----------
        ctx
            A click context object that contains information about the
            current command and its parameters based on the input in the
            REPL prompt.

        param
            A `click.Parameter` object which is referred to generate
            auto-completions.

        state
            A `ReplParsingState` object that contains information about the
            parsing state of the parameters of the current command
            based on the text in the prompt.

        incomplete
            An object that holds the unfinished string in the REPL prompt,
            and its parsed state, that requires further input or completion.

        Yields
        ------
        prompt_toolkit.completion.Completion
            The :class:`prompt_toolkit.completion.Completion`
            objects that's sent for auto-completion of the
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
    ) -> Generator[Completion, None, None]:
        # Display coloured option flags, only if there are
        # any exclusive flags to pass in the False'y value

        for flags_list, bool_val in zip(
            [option.opts, option.secondary_opts], ["true", "false"]
        ):
            # The primary flags are assigned for the boolean value of "True",
            # And "False" for secondary flags, despite the default value.

            item_token = f"parameter.type.bool.to{bool_val}"

            display_lst = option_flag_tokens_joiner(
                flags_list,
                item_token,
                f"parameter.option.name.separator,{item_token}",
                get_option_flag_sep(flags_list),
            )

            yield ReplCompletion(
                min(flags_list, key=len),
                incomplete,
                display=TokenizedFormattedText(display_lst, self.parent_token_class_name),
                display_meta=option.help or "",
            )

    def get_completion_for_option_flags(
        self,
        ctx: Context,
        command: Command,
        state: ReplParsingState,
        incomplete: Incomplete,
    ) -> Generator[Completion, None, None]:
        """
        Generates auto-completions for option flags based on the given command.

        Parameters
        ----------
        ctx
            A click context object that contains information about the
            current command and its parameters based on the input in the
            REPL prompt.

        command
            A click command object, which is referred to generate auto-completions
            based on its parameters.

        state
            A `ReplParsingState` object that contains information about the
            parsing state of the parameters of the current command
            based on the text in the prompt.

        incomplete
            An object that holds the unfinished string in the REPL prompt,
            and its parsed state, that requires further input or completion.

        Yields
        ------
        prompt_toolkit.completion.Completion
            The :class:`prompt_toolkit.completion.Completion`
            objects thats sent for auto-completion of the
            incomplete prompt, based on the given parameter.
        """

        _incomplete = incomplete.parsed_str

        for option in command.params:
            if not isinstance(option, click.Option):
                continue

            if option.hidden and not self.show_hidden_params:
                continue

            already_used = not is_param_value_incomplete(ctx, option)

            if option.is_flag and already_used:
                continue

            hide = (
                self.show_only_unused_options
                and already_used
                and not (option.multiple or option.count)
            )

            if hide:
                continue

            is_shortest_opt_names_only = self.shortest_opt_names_only and not _incomplete

            if (
                is_shortest_opt_names_only
                and option.is_bool_flag
                and option.secondary_opts
            ):
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

            if is_shortest_opt_names_only:
                option_flags, sep = join_options(flags_that_start_with_incomplete)

                def display_text_func(flag_token: str) -> ListOfTokens:
                    if not flag_token.startswith("parameter.option.name"):
                        flag_token = f"parameter.option.name.separator,{flag_token}"

                    return option_flag_tokens_joiner(
                        option_flags, flag_token, flag_token, sep
                    )

                flags_that_start_with_incomplete = [
                    min(flags_that_start_with_incomplete, key=len)
                ]

            for option_flag in flags_that_start_with_incomplete:
                if not is_shortest_opt_names_only:

                    def display_text_func(flag_token: str) -> ListOfTokens:
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
                        display_text_func(flag_token), self.parent_token_class_name
                    ),
                    display_meta=option.help or "",
                )

    def get_completion_for_command_arguments(
        self,
        ctx: Context,
        command: Command,
        state: ReplParsingState,
        incomplete: Incomplete,
    ) -> Generator[Completion, None, None]:
        """
        Generates auto-completions to display the flags of the options
        based on the given command object.

        Parameters
        ----------
        ctx
            A click context object that contains information about the
            current command and its parameters based on the input in the
            REPL prompt.

        command
            A click command object, which is referred to generate auto-completions
            based on its parameters.

        state
            A `ReplParsingState` object that contains information about the
            parsing state of the parameters of the current command
            based on the text in the prompt.

        incomplete
            An object that holds the unfinished string in the REPL prompt,
            and its parsed state, that requires further input or completion.

        Yields
        ------
        prompt_toolkit.completion.Completion
            The :class:`prompt_toolkit.completion.Completion`
            objects thats sent
            for auto-completion of the incomplete prompt.
        """

        current_param = state.current_param
        _incomplete_prefix = incomplete.expand_envvars()[:2]

        current_argument_havent_received_values = isinstance(
            current_param, click.Argument
        ) and is_param_value_incomplete(ctx, current_param, check_if_tuple_has_none=False)

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
        ctx
            A :class:`click.Context` object that contains information about the
            current command and its parameters based on the input in the
            REPL prompt.

        state
            A :class:`~click_repl.parser.ReplParsingState` object that contains
            information about the parsing state of the parameters of the current command
            based on the text in the prompt.

        incomplete
            An :class:`~click_repl.parser.Incomplete` object that holds the unfinished
            string in the REPL prompt, and its parsed state, that requires further
            input or completion.

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
            is_param_value_incomplete(ctx, param) for param in args_list
        )

        # If there's a sub-command found in the state object,
        # generate completions for its arguments.
        is_chained_command = state.current_group.chain or getattr(
            ctx.command, "chain", False
        )

        is_current_command_a_group_or_none = current_command is None or isinstance(
            current_command, click.Group
        )

        return ctx.command != self.group and (
            incomplete_visible_args
            or not (is_chained_command or is_current_command_a_group_or_none)
        )

    def get_multicommand_for_generating_subcommand_completions(
        self, ctx: Context, state: ReplParsingState, incomplete: Incomplete
    ) -> MultiCommand | None:
        """
        Returns the appropriate :class:`~click.Group` object that should be used
        to generate auto-completions for subcommands of a group.

        Parameters
        ----------
        ctx
            A :class:`click.Context` object that contains information about the
            current command and its parameters based on the input in the
            REPL prompt.

        state
            A :class:`~click_repl.parser.ReplParsingState` object that contains
            information about the parsing state of the parameters of the current command
            based on the text in the prompt.

        incomplete
            An :class:`~click_repl.parser.Incomplete` object that holds the unfinished
            string in the REPL prompt, and its parsed state, that requires
            further input or completion.

        Returns
        -------
        Group | None
            A click multicommand object, if available, which is supposed to be used for
            generating auto-completion for suggesting its subcommands.
        """
        if state.current_param:
            return None

        any_argument_param_incomplete = any(
            is_param_value_incomplete(ctx, param)
            for param in ctx.command.params
            if isinstance(param, click.Argument)
        )

        if any_argument_param_incomplete:
            return None

        if isinstance(ctx.command, MultiCommand):
            return ctx.command

        if state.current_group.chain:
            return state.current_group

        return None

    def _get_visible_subcommands(
        self,
        ctx: Context,
        group: MultiCommand,
        incomplete: str,
        show_hidden_commands: bool = False,
    ) -> Generator[tuple[str, Command], None, None]:
        """
        Get all the subcommands from the given ``multicommand`` whose name
        starts with the given ``incomplete`` prefix string.
        """

        for command_name in group.list_commands(ctx):
            if not command_name.startswith(incomplete):
                continue

            subcommand = group.get_command(ctx, command_name)

            if subcommand is None or (subcommand.hidden and not show_hidden_commands):
                # We skip if there's no command found or it's a hidden command
                # and show_hidden_commands is False.
                continue

            yield command_name, subcommand

    def get_completions_for_subcommands(
        self,
        ctx: Context,
        state: ReplParsingState,
        incomplete: Incomplete,
    ) -> Generator[Completion, None, None]:
        """
        Provides auto-completions for command names, based on the
        current command and group.

        Parameters
        ----------
        ctx
            A click context object that contains information about the
            current command and its parameters based on the input in the
            REPL prompt.

        state
            A `ReplParsingState` object that contains information about the
            parsing state of the parameters of the current command
            based on the text in the prompt.

        incomplete
            An object that holds the unfinished string in the REPL prompt,
            and its parsed state, that requires further input or completion.

        Yields
        ------
        prompt_toolkit.completion.Completion
            The :class:`prompt_toolkit.completion.Completion`
            objects thats sent for auto-completion
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

        for name, command in self._get_visible_subcommands(
            ctx, multicommand, _incomplete, self.show_hidden_commands
        ):
            cmd_token_type = get_token_type(command)

            yield ReplCompletion(
                name,
                incomplete,
                display=TokenizedFormattedText(
                    [(f"class:{cmd_token_type}.name", name)], self.parent_token_class_name
                ),
                display_meta=command.get_short_help_str(),
            )

    def get_completions_for_internal_commands(
        self, prefix: str, incomplete: str
    ) -> Generator[Completion, None, None]:
        """
        Generates auto-completions based on the given prefix present
        in the current incomplete prompt.

        Parameters
        ----------
        prefix
            The prefix string thats present in the start of the prompt.

        incomplete
            An object that holds the unfinished string in the REPL prompt,
            and its parsed state, that requires further input or completion.

        Yields
        ------
        prompt_toolkit.completion.Completion
            The :class:`prompt_toolkit.completion.Completion`
            objects thats sent for auto-completion
            of the incomplete prompt.
        """

        incomplete = incomplete.strip()[len(prefix) :].lstrip().lower()
        info_table = self.internal_commands_system._group_commands_by_callback_and_desc()

        for (_, desc), aliases in info_table.items():
            aliases_start_with_incomplete = [
                alias
                for alias in aliases
                if alias.startswith(incomplete) and alias != incomplete
            ]

            if aliases_start_with_incomplete:
                display = option_flag_tokens_joiner(
                    aliases,
                    "parameter.option.name",
                    "parameter.option.name.separator",
                    "/",
                )

                yield ReplCompletion(
                    aliases_start_with_incomplete[0],
                    incomplete,
                    display=TokenizedFormattedText(display, self.parent_token_class_name),
                    display_meta=desc,
                )

    def handle_internal_commands_request(
        self, document_text: str
    ) -> Generator[Completion, None, bool]:
        flag, ics_prefix = self.internal_commands_system.get_prefix(document_text)

        internal_commands_requested = flag == "internal"

        if ics_prefix is not None:
            if ISATTY and isinstance(self.bottom_bar, BottomBar):
                self.bottom_bar.reset_state()

            if internal_commands_requested:
                yield from self.get_completions_for_internal_commands(
                    ics_prefix, document_text
                )

        return internal_commands_requested

    def get_completions(
        self, document: Document, complete_event: CompleteEvent | None = None
    ) -> Generator[Completion, None, None]:
        """
        Provides `prompt_toolkit.completion.Completion`
        objects from the obtained current input string in the REPL prompt.

        Parameters
        ----------
        document
            The :class:`~prompt_toolkit.document.Document` object containing the
            incomplete command line string.

        complete_event
            The :class:`~prompt_toolkit.completion.CompleteEvent` object of the
            current prompt.

        Yields
        ------
        prompt_toolkit.completion.Completion
            The :class:`prompt_toolkit.completion.Completion`
            objects for command line autocompletion.
        """

        internal_commands_requested = yield from self.handle_internal_commands_request(
            document.text_before_cursor
        )

        if internal_commands_requested:
            return  # type:ignore[unreachable]

        try:
            parsed_ctx, state, incomplete = _resolve_state(
                self.group_ctx, document.text_before_cursor
            )

            if parsed_ctx.command.hidden and not self.show_hidden_commands:
                # We skip the hidden command if self.show_hidden_commands is False.
                return

            if ISATTY:
                get_current_repl_ctx().update_state(state)  # type:ignore[union-attr]

                if isinstance(self.bottom_bar, BottomBar):
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
    text
        The string that should fill into the prompt during auto-completion.

    incomplete
        The string thats not completed in the prompt.
        It's used to get the :attr:`.start_position` for the Completion to
        swap text with, in the prompt.

    *args
        Additional arguments should be passed as keyword arguments to the
        :class:`~prompt_toolkit.completion.Completion` class.

    **kwargs
        Extra arguments to ``metric``: refer to each metric documentation for a
        list of all possible arguments to the
        :class:`~prompt_toolkit.completion.Completion` class.
    """

    __slots__ = (
        "text",
        "start_position",
        "_display_meta",
        "display",
        "style",
        "selected_style",
    )

    def __init__(
        self,
        text: str,
        incomplete: Incomplete | str,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Initializes the `ReplCompletion` class.
        """

        no_surrounding_quotes = not (text.startswith('"') or text.endswith('"'))

        if " " in text and no_surrounding_quotes:
            # Surrounding text by quotes, as it has space in it.
            text = text.replace('"', '\\"')
            text = f'"{text}"'

        if isinstance(incomplete, Incomplete):
            incomplete = incomplete.raw_str

        # diff = len(incomplete) - len(text)
        # if diff > 0:
        #     text += " " * diff + "\b" * diff

        kwargs.setdefault("start_position", -len(incomplete))

        super().__init__(text, *args, **kwargs)
