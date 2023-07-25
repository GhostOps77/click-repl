"""
`click_repl.completer`

Configuration for auto-completion for REPL.
"""
import typing as t
from pathlib import Path

import click
from prompt_toolkit.completion import Completer
from prompt_toolkit.completion import Completion

from ._globals import _RANGE_TYPES
from ._globals import AUTO_COMPLETION_PARAM
from ._globals import HAS_CLICK8
from ._globals import IS_WINDOWS
from ._globals import ISATTY
from ._internal_cmds import InternalCommandSystem
from .parser import Incomplete
from .utils import _is_param_value_incomplete
from .utils import _join_options
from .utils import _resolve_state

if t.TYPE_CHECKING:
    from typing import Any, Dict, Final, Generator, Optional, Tuple, Union

    from click import Context, MultiCommand, Parameter
    from prompt_toolkit.completion import CompleteEvent
    from prompt_toolkit.document import Document

    from .bottom_bar import BottomBar
    from .core import ReplContext
    from .parser import ArgsParsingState


__all__ = ["ClickCompleter", "ReplCompletion"]


def _quotes(text: str) -> str:
    if " " in text and text[0] != '"' != text[-1]:
        text = text.strip('"').replace('"', '\\"')
        return f'"{text}"'

    return text


class ClickCompleter(Completer):
    """
    Custom prompt Completion provider for the click-repl app.

    Parameters
    ----------
    ctx : click.Context
        The current click context object.

    bottom_bar : BottomBar, optional
        The `click_repl.bottom_bar.BottomBar` object thats used to update
        the text displayed in the bottom bar.

    internal_commands_system : click_repl._internal_cmds.InternalCommandSystem
        The `click_repl._internal_cmds.InternalCommandSystem` object that
        holds information about the internal commands and their prefixes.

    styles : A dictionary of str: str pairs.
        A dictionary denoting different styles for
        `prompt_toolkit.completion.Completion` objects for
        `'command'`, `'argument'`, and `'option'`.

    shortest_opts_only : bool, default: False
        If `True`, only the shortest flag of an option parameter is used
        for auto-completion.

    show_only_unused_opts : bool, default: False
        If `True`, only the options that are not mentioned or unused in
        the current prompt will be displayed during auto-completion.

    show_hidden_commands: bool, default: False
        Determines whether the hidden commands should be shown
        in autocompletion or not.

    show_hidden_params: bool, default: False
        Determines whether the hidden parameters should be shown
        in autocompletion or not.
    """

    def __init__(
        self,
        ctx: "Context",
        bottom_bar: "Optional[BottomBar]" = None,
        internal_commands_system: "Optional[InternalCommandSystem]" = None,
        styles: "Dict[str, str]" = {},
        shortest_opts_only: bool = False,
        show_only_unused_opts: bool = False,
        show_hidden_commands: bool = False,
        show_hidden_params: bool = False,
    ) -> None:
        self.cli_ctx: "Final[Context]" = ctx
        self.cli: "Final[MultiCommand]" = self.cli_ctx.command  # type: ignore[assignment]

        self.repl_ctx: "Optional[ReplContext]" = None

        if ISATTY:
            self.bottom_bar = bottom_bar

        else:
            self.bottom_bar = None

        self.shortest_opts_only = shortest_opts_only
        self.show_only_unused_opts = show_only_unused_opts

        self.show_hidden_commands = show_hidden_commands
        self.show_hidden_params = show_hidden_params

        if not styles:
            styles = {
                "command": "",
                "option": "",
                "argument": "",
            }

        self.styles = styles

        if internal_commands_system is None:
            internal_commands_system = InternalCommandSystem(None, None)

        self.internal_commands_system = internal_commands_system

    def get_completion_from_autocompletion_functions(
        self,
        ctx: "Context",
        param: "Parameter",
        state: "ArgsParsingState",
        incomplete: "Incomplete",
    ) -> "Generator[Completion, None, None]":
        """
        Generates `prompt_toolkit.completion.Completion` objects
        based on the output from the command's `shell_complete` or
        `autocompletion` function of the current parameter.

        Parameters
        ----------
        ctx : click.Context
            A click context object that holds
            information about the currently parsed args string from the REPL prompt.

        param : click.Parameter
            A `click.Parameter` object that holds information about
            the current parameter thats being parsed by the parser.

        state : click_repl.parser.ArgsParsingState
            A `click_repl.parser.ArgsParsingState` object
            that contains information about the parsing state of the parameters
            of the current comman.

        incomplete : Incomplete
            An object that holds the unfinished string in the REPL prompt,
            and its parsed state, that requires further input or completion.

        Yields
        ------
        prompt_toolkit.completion.Completion type object.
            The `prompt_toolkit.completion.Completion` objects thats sent
            for auto-completion of the incomplete prompt.
        """

        # click < v8 has a different name for their shell_complete
        # function, and its "autocompletion". So, for backwards
        # compatibility, we're calling them based on the click's version.

        if HAS_CLICK8:
            autocompletions = param.shell_complete(ctx, incomplete.parsed_str)

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

            elif HAS_CLICK8 and isinstance(
                autocomplete, click.shell_completion.CompletionItem
            ):
                yield ReplCompletion(autocomplete.value, incomplete)

            elif isinstance(autocomplete, Completion):
                yield autocomplete

            else:
                yield ReplCompletion(str(autocomplete), incomplete)

    def get_completion_from_choices_click_v7(
        self, param_type: "click.Choice", incomplete: "Incomplete"
    ) -> "Generator[Completion, None, None]":
        """
        Generates `prompt_toolkit.completion.Completion` objects
        based on data from the given `click.Choice` parameter type
        of a parameter.

        This method is used for backwards compatibility with click v7
        as `click.Choice` class didn't have a `shell_complete` method
        until click v8.

        Parameters
        ----------
        param_type : click.Choice
            The `click.Choice` object of a parameter, to which the choice
            completions should be generated.

        incomplete : Incomplete
            An object that holds the unfinished string in the REPL prompt,
            and its parsed state, that requires further input or completion.

        Yields
        ------
        prompt_toolkit.completion.Completion type object.
            The `prompt_toolkit.completion.Completion` objects thats sent
            for auto-completion of the incomplete prompt, based on the
            given parameter type.
        """

        case_insensitive = not param_type.case_sensitive

        _incomplete = incomplete._expand_envvars()

        if case_insensitive:
            _incomplete = _incomplete.lower()

        for choice in param_type.choices:
            _choice = choice.lower() if case_insensitive else choice

            if _choice.startswith(_incomplete):
                yield ReplCompletion(
                    choice,
                    incomplete,
                    display=choice,
                    style=self.styles["argument"],
                )

    def get_completion_for_path_types(
        self, incomplete: "Incomplete"
    ) -> "Generator[Completion, None, None]":
        """
        Generates `prompt_toolkit.completion.Completion` objects
        for `click.Path` and `click.File` type parameters based on
        the given incomplete path string.

        Parameters
        ----------
        incomplete : Incomplete
            An unfinished object that holds the path string in the REPL prompt,
            and its parsed state, that requires further input or completion.

        Yields
        ------
        prompt_toolkit.completion.Completion type object.
            The `prompt_toolkit.completion.Completion` objects thats sent
            for auto-completion of the incomplete prompt.
        """

        _incomplete: str = incomplete._expand_envvars()

        if "*" in _incomplete:
            return

        # print(f'\n{incomplete = }')

        # quoted = incomplete.count('"') % 2

        # print(f"\n{has_space = } {quoted = } {incomplete = }")

        search_pattern = _incomplete.strip("\"'") + "*"
        # if has_space and not quoted:
        #     incomplete = f'"{incomplete}'

        temp_path_obj = Path(search_pattern)

        # quote = ""  # Quote thats used to surround the path in shell

        # if " " in incomplete:
        #     for i in incomplete:
        #         if i in ("'", '"'):
        #             quote = i
        #             break

        completion_txt_len = -len(incomplete.raw_str)  # - has_space * 2  # + quoted * 2

        # print(f"{temp_path_obj = }")
        for path in temp_path_obj.parent.glob(temp_path_obj.name):
            #     if " " in path:
            #         if quote:
            #             path = quote + path
            #         else:
            #             if IS_WINDOWS:
            #                 path = repr(path).replace("\\\\", "\\")
            #     else:
            #         if IS_WINDOWS:
            #             path = path.replace("\\", "\\\\")

            path_str = str(path)

            if IS_WINDOWS:
                path_str = path_str.replace("\\\\", "\\")

            if path.is_dir():
                path_str += "/"

            # if " " in path_str:
            #     path_str = f'"{path_str}"'

            # if quoted:
            #     path_str = f'"{path_str}'
            # else:
            #     path_str = f'"{path_str}"'

            # completion_txt_len -= 1

            yield ReplCompletion(
                path_str,
                incomplete,
                start_position=completion_txt_len,
                display=path.name,
            )

    def get_completion_for_boolean_type(
        self, incomplete: "Incomplete"
    ) -> "Generator[Completion, None, None]":
        """
        Generates `prompt_toolkit.completion.Completion` objects
        for boolean type parameter based on the given incomplete string.

        Parameters
        ----------
        incomplete : Incomplete
            An object that holds the unfinished string in the REPL prompt,
            and its parsed state, that requires further input or completion.

        Yields
        ------
        prompt_toolkit.completion.Completion type object.
            The `prompt_toolkit.completion.Completion` objects thats sent
            for auto-completion of the incomplete prompt.
        """

        _incomplete = incomplete._expand_envvars()

        boolean_mapping: "Dict[str, Tuple[str, ...]]" = {
            "true": ("1", "true", "t", "yes", "y", "on"),
            "false": ("0", "false", "f", "no", "n", "off"),
        }

        for value, aliases in boolean_mapping.items():
            if any(alias.startswith(_incomplete) for alias in aliases):
                yield ReplCompletion(value, incomplete, display_meta="/".join(aliases))

    def get_completion_for_range_types(
        self,
        param_type: "Union[click.IntRange, click.FloatRange]",
        incomplete: "Incomplete",
    ) -> "Generator[Completion, None, None]":
        """
        Generates `prompt_toolkit.completion.Completion` objects
        based on data from the given parameter type object
        of a click command's parameter.

        Parameters
        ----------
        param_type : click.Parameter
            The `click.Parameter` object, to which the auto-completion
            objects should be generated.

        incomplete : Incomplete
            An object that holds the unfinished string in the REPL prompt,
            and its parsed state, that requires further input or completion.

        Yields
        ------
        prompt_toolkit.completion.Completion type object.
            The `prompt_toolkit.completion.Completion` objects thats sent
            for auto-completion of the incomplete prompt, based on the
            given parameter type.
        """

        _incomplete = incomplete._expand_envvars()

        lower_bound = param_type.min or 0
        upper_bound = param_type.max or 0

        if isinstance(param_type, click.IntRange):
            display_template = "{}"

        elif HAS_CLICK8 and isinstance(param_type, click.FloatRange):
            lower_bound = int(lower_bound)
            upper_bound = int(upper_bound)
            display_template = "{}."

        lower_bound *= not getattr(param_type, "min_open", False)
        upper_bound *= (not getattr(param_type, "max_open", False)) + 1

        for i in range(lower_bound, upper_bound):  # type: ignore[arg-type]
            text = display_template.format(i)

            if text.startswith(_incomplete):
                yield ReplCompletion(text, incomplete)

    def get_completion_from_params(
        self,
        ctx: "Context",
        state: "ArgsParsingState",
        incomplete: "Incomplete",
    ) -> "Generator[Completion, None, None]":
        """
        Generates `prompt_toolkit.completion.Completion` objects
        based on the current parameter.

        Parameters
        ----------
        ctx : click.Context
            A click context object that contains information about the
            current command and its parameters based on the input in the
            REPL prompt.

        state : click_repl.parser.ArgsParsingState
            A `click_repl.parser.ArgsParsingState` object that contains
            information about the parsing state of the parameters of the
            current command based on the text in the prompt.

        incomplete : Incomplete
            An object that holds the unfinished string in the REPL prompt,
            and its parsed state, that requires further input or completion.

        Yields
        ------
        prompt_toolkit.completion.Completion type object.
            The `prompt_toolkit.completion.Completion` objects thats sent
            for auto-completion of the incomplete prompt, based on the
            given parameter.
        """

        param = state.current_param
        param_type: "click.ParamType" = param.type  # type: ignore[union-attr]

        if isinstance(param_type, _RANGE_TYPES):
            yield from self.get_completion_for_range_types(param_type, incomplete)

        # elif isinstance(param_type, click.Tuple):
        #     return [Completion("-", display=_type.name) for _type in param_type.types]

        # shell_complete method for click.Choice class is introduced in click-v8.
        elif not HAS_CLICK8 and isinstance(param_type, click.Choice):
            yield from self.get_completion_from_choices_click_v7(param_type, incomplete)

        elif isinstance(param_type, click.types.BoolParamType):
            # Completion for click.BOOL types.
            yield from self.get_completion_for_boolean_type(incomplete)

        elif isinstance(param_type, (click.Path, click.File)):
            # Both Path and File types are expected to receive input as path strings.
            yield from self.get_completion_for_path_types(incomplete)

        elif getattr(param, AUTO_COMPLETION_PARAM, None) is not None:
            # Completions for parameters that have auto-completion functions.
            yield from self.get_completion_from_autocompletion_functions(
                ctx, param, state, incomplete  # type: ignore[arg-type]
            )

        return

    def get_completion_for_command_arguments(
        self,
        ctx: "Context",
        state: "ArgsParsingState",
        incomplete: "Incomplete",
    ) -> "Generator[Completion, None, None]":
        """
        Generates `prompt_toolkit.completion.Completion` objects
        to display the flags of the options of the current command object.

        Parameters
        ----------
        ctx : click.Context
            A click context object that contains information about the
            current command and its parameters based on the input in the
            REPL prompt.

        state : click_repl.parser.ArgsParsingState
            A `click_repl.parser.ArgsParsingState` object that contains
            information about the parsing state of the parameters of the
            current command based on the text in the prompt.

        incomplete : Incomplete
            An object that holds the unfinished string in the REPL prompt,
            and its parsed state, that requires further input or completion.

        Yields
        ------
        prompt_toolkit.completion.Completion type object.
            The `prompt_toolkit.completion.Completion` objects thats sent
            for auto-completion of the incomplete prompt.
        """

        args = state.args
        current_param = state.current_param
        is_current_param_not_none = current_param is not None
        _incomplete = incomplete.parsed_str

        if not is_current_param_not_none or (
            isinstance(current_param, click.Argument)
            and ctx.params[current_param.name] is None  # type: ignore[index, union-attr]
        ):
            for param in state.current_command.params:  # type: ignore[union-attr]
                if isinstance(param, click.Argument) or (
                    param.hidden  # type: ignore[union-attr]
                    and not self.show_hidden_params
                ):
                    # We skip the Arguments and hidden parameters
                    # if self.show_hidden_params is False.
                    continue

                opts = param.opts + param.secondary_opts

                previous_args = args[: param.nargs * -1]  # type: ignore[index]
                already_used = any(opt in previous_args for opt in opts)
                hide = self.show_only_unused_opts and already_used and not param.multiple

                opts_with_incomplete_prefix = [
                    opt for opt in opts if opt.startswith(_incomplete) and not hide
                ]

                if (
                    getattr(param, "is_flag", False) and any(i in args for i in opts)
                ) or not opts_with_incomplete_prefix:
                    # Skip the current iteration, if param is a flag,
                    # and its already in args, or the param is called
                    # recently within its nargs length.
                    continue

                display = ""  # Display text for the auto-completion.

                if self.shortest_opts_only and not _incomplete:
                    # Displays all the aliases of the option in the completion,
                    # only if the incomplete string is empty.
                    # It provides only the shortest one for auto-completion,
                    # by joining all the aliases into a single string.

                    _, sep = _join_options(opts)
                    display = sep.join(opts_with_incomplete_prefix)

                    # Changed for the auto-completion.
                    opts_with_incomplete_prefix = [
                        min(opts_with_incomplete_prefix, key=len)
                    ]

                for opt in opts_with_incomplete_prefix:
                    display_meta = getattr(param, "help", "")

                    if not self.shortest_opts_only:
                        # If shortest_opts_only=False, display the alias
                        # of the option as it is.
                        display = opt

                    if not (getattr(param, "count", False) or param.default is None):
                        # Display the default value of the option, only if
                        # the option is not a counting option, and
                        # the default value is not None.
                        display += f" [Default: {param.default}]"

                    yield ReplCompletion(
                        opt,
                        incomplete,
                        display=display,
                        display_meta=display_meta,
                        style=self.styles["option"],
                    )

        if is_current_param_not_none and (
            not getattr(current_param, "hidden", False) or self.show_hidden_params
        ):
            # If the current param is not None and it's not a
            # hidden param, generate auto-completion for it.
            # If the current param is a hidden param and
            # self.show_completions_for_hidden_param is true,
            # generate auto-completion for it.
            yield from self.get_completion_from_params(ctx, state, incomplete)

    def get_completions_for_subcommands(
        self,
        ctx: "Context",
        state: "ArgsParsingState",
        incomplete: "Incomplete",
    ) -> "Generator[Completion, None, None]":
        """
        Provides command names as `prompt_toolkit.completion.Completion`,
        based to the current command and group.

        Parameters
        ----------
        ctx : click.Context
            A click context object that contains information about the
            current command and its parameters based on the input in the
            REPL prompt.

        state : click_repl.parser.ArgsParsingState
            A `click_repl.parser.ArgsParsingState` object that contains
            information about the parsing state of the parameters of the
            current command based on the text in the prompt.

        incomplete : Incomplete
            An object that holds the unfinished string in the REPL prompt,
            and its parsed state, that requires further input or completion.

        Yields
        ------
        prompt_toolkit.completion.Completion type object.
            The `prompt_toolkit.completion.Completion` objects thats sent
            for auto-completion of the incomplete prompt.
        """

        current_group = state.current_group
        is_current_command_available = state.current_command is not None
        is_chain = state.is_current_group_chained

        if is_current_command_available:
            # If there's a sub-command found in the state object,
            # generate completions for its arguments.
            yield from self.get_completion_for_command_arguments(ctx, state, incomplete)

        # To check whether all the parameters in the current command
        # has receieved their values.
        all_ctx_values_provided = all(
            not _is_param_value_incomplete(ctx, param_name) for param_name in ctx.params
        )

        if is_current_command_available and not (is_chain and all_ctx_values_provided):
            # If the current command is not a chained multicommand, or it haven't
            # received values for all of its parameters yet, then we can't show
            # its subcommands for auto-completion.
            return

        _incomplete = incomplete.parsed_str

        for cmd_name in current_group.list_commands(ctx):
            command = current_group.get_command(ctx, cmd_name)

            if command is None or (command.hidden and not self.show_hidden_commands):
                # We skip the hidden command if self.show_hidden_commands is False,
                # or if there's no command found.
                continue

            elif cmd_name.startswith(_incomplete):
                yield ReplCompletion(
                    cmd_name,
                    incomplete,
                    display_meta=getattr(command, "short_help", ""),
                )

    def get_completions(
        self, document: "Document", complete_event: "Optional[CompleteEvent]" = None
    ) -> "Generator[Completion, None, None]":
        """
        Provides `prompt_toolkit.completion.Completion`
        objects from the obtained current input string in the REPL prompt.

        Parameters
        ----------
        document: prompt_toolkit.document.Document
            The `prompt_toolkit.document.Document` object
            containing the incomplete command line string.

        complete_event : prompt_toolkit.completion.CompleteEvent
            The `prompt_toolkit.completion.CompleteEvent`
            object of the current prompt.

        Yields
        ------
        prompt_toolkit.completion.Completion type object.
            The `prompt_toolkit.completion.Completion` objects for
            command line autocompletion.
        """

        if self.internal_commands_system.get_prefix(document.text_before_cursor)[0]:
            # If the input text in the prompt starts with a prefix indicating an internal
            # or system command, it is considered as such. In this case, generating
            # completions for the incomplete input is unnecessary. Therefore, the text
            # in the bottom bar is cleared and the function returns without generating
            # any completions.

            if ISATTY and self.bottom_bar is not None:
                self.bottom_bar.reset_state()

            return

        try:
            parsed_ctx, state, incomplete = _resolve_state(
                self.cli_ctx, document.text_before_cursor
            )

            if parsed_ctx.command.hidden and not self.show_hidden_commands:
                # We skip the hidden parameter if self.show_hidden_params is False.
                return

            if ISATTY:
                self.repl_ctx.current_state = state  # type: ignore[union-attr]

                if self.bottom_bar is not None:
                    # Update the state object of the bottom bar to display
                    # different info text.
                    self.bottom_bar.update_state(state)

            yield from self.get_completions_for_subcommands(parsed_ctx, state, incomplete)

        # except Exception:
        #     pass

        except Exception as e:
            if not __debug__:
                raise e


class ReplCompletion(Completion):
    """
    Custom Completion class to generate Completion
    objects with the default settings for proper auto-completion
    in the REPL prompt.

    Parameters
    ---
    text : str
        The string that should fill into the prompt
        during auto-completion.

    incomplete : Incomplete
        The string thats not completed in the prompt.
        It's used to get the `start_position` for the Completion to
        swap text with, in the prompt.

    quote : bool, default: True
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
        incomplete: "Union[Incomplete, str]",
        quote: bool = True,
        *args: "Any",
        **kwargs: "Any",
    ) -> None:
        display = text

        if quote:
            text = _quotes(text)

        if isinstance(incomplete, Incomplete):
            incomplete = incomplete.raw_str

        kwargs.setdefault("start_position", -len(incomplete))
        kwargs.setdefault("display", display)

        if not ISATTY:
            # We don't have to pass the style attributes if the completions
            # are not gonna be displayed.
            kwargs.pop("style", None)
            kwargs.pop("selected_style", None)

        super().__init__(text, *args, **kwargs)
