import os
import typing as t
from pathlib import Path

import click
from prompt_toolkit.completion import Completer, Completion

from ._globals import _RANGE_TYPES, HAS_CLICK8, ISATTY
from ._internal_cmds import InternalCommandSystem
from .bottom_bar import TOOLBAR
from .parser import quotes
from .utils import _resolve_state, get_group_ctx, join_options

__all__ = ["ClickCompleter"]

IS_WINDOWS = os.name == "nt"

# Handle backwards compatibility for click<=8
if HAS_CLICK8:
    AUTO_COMPLETION_PARAM = "shell_complete"
else:
    AUTO_COMPLETION_PARAM = "autocompletion"


if t.TYPE_CHECKING:
    from typing import Dict, Final, Generator, Iterable, Optional, Union

    from click import Context, MultiCommand, Parameter
    from prompt_toolkit.completion import CompleteEvent
    from prompt_toolkit.document import Document

    from .parser import ArgsParsingState


class ClickCompleter(Completer):
    """Custom prompt Completion provider for the click-repl app.

    Keyword arguments:
    ---
    :param:`ctx` - The given :class:`~click.MultiCommand`'s Context.
    :param:`styles` - Dictionary of style mapping for the Completion objects.
    """

    def __init__(
        self,
        ctx: "Context",
        internal_commands_system: "Optional[InternalCommandSystem]" = None,
        shortest_opts_only: bool = False,
        show_only_unused_opts: bool = False,
        styles: "Optional[Dict[str, str]]" = None,
    ) -> None:
        self.cli_ctx: "Final[Context]" = get_group_ctx(ctx)
        self.cli: "Final[MultiCommand]" = self.cli_ctx.command  # type: ignore[assignment]
        self.shortest_opts_only = shortest_opts_only
        self.show_only_unused_opts = show_only_unused_opts

        if styles is None:
            styles = {
                "command": "",
                "option": "",
                "argument": "",
            }

        self.styles = styles
        self.internal_commands_system = internal_commands_system

    def get_completion_from_autocompletion_functions(
        self,
        param: "Parameter",
        autocomplete_ctx: "Context",
        args: "Iterable[str]",
        incomplete: str,
    ) -> "Generator[Completion, None, None]":
        if HAS_CLICK8:
            autocompletions = param.shell_complete(autocomplete_ctx, incomplete)
        else:
            autocompletions = param.autocompletion(  # type: ignore[attr-defined]
                autocomplete_ctx, args, incomplete
            )

        for autocomplete in autocompletions:
            if isinstance(autocomplete, tuple):
                yield Completion(
                    quotes(autocomplete[0]),
                    -len(incomplete),
                    display_meta=autocomplete[1],
                )

            elif HAS_CLICK8 and isinstance(
                autocomplete, click.shell_completion.CompletionItem
            ):
                yield Completion(quotes(autocomplete.value), -len(incomplete))

            elif isinstance(autocomplete, Completion):
                yield autocomplete

            else:
                yield Completion(quotes(str(autocomplete)), -len(incomplete))

    def get_completion_from_choices_click_le_7(
        self, param_type: "click.Choice", incomplete: str
    ) -> "Generator[Completion, None, None]":
        case_insensitive = not getattr(param_type, "case_sensitive", True)

        if case_insensitive:
            incomplete = incomplete.lower()

        for choice in param_type.choices:
            if case_insensitive:
                choice = choice.lower()

            if choice.startswith(incomplete):
                yield Completion(
                    quotes(choice),
                    -len(incomplete),
                    style=self.styles["argument"],
                    display=choice,
                )

    def get_completion_for_Path_types(
        self, incomplete: str
    ) -> "Generator[Completion, None, None]":
        if "*" in incomplete:
            return []  # type: ignore[return-value]

        # print(f'\n{incomplete = }')

        has_space = " " in incomplete
        # quoted = incomplete.count('"') % 2

        # print(f"\n{has_space = } {quoted = } {incomplete = }")

        search_pattern = incomplete.strip("\"'") + "*"
        # if has_space and not quoted:
        #     incomplete = f'"{incomplete}'

        temp_path_obj = Path(search_pattern)

        # quote = ""  # Quote thats used to surround the path in shell

        # if " " in incomplete:
        #     for i in incomplete:
        #         if i in ("'", '"'):
        #             quote = i
        #             break

        completion_txt_len = -len(incomplete) - has_space * 2  # + quoted * 2

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

            if " " in path_str:
                path_str = f'"{path_str}"'

                # if quoted:
                #     path_str = f'"{path_str}'
                # else:
                #     path_str = f'"{path_str}"'

                # completion_txt_len -= 1

            yield Completion(
                path_str,
                completion_txt_len,
                display=path.name,
            )

    def get_completion_for_Boolean_type(
        self, incomplete: str
    ) -> "Generator[Completion, None, None]":
        boolean_mapping = {
            "true": ("1", "true", "t", "yes", "y", "on"),
            "false": ("0", "false", "f", "no", "n", "off"),
        }

        for value, aliases in boolean_mapping.items():
            if any(alias.startswith(incomplete) for alias in aliases):
                yield Completion(value, -len(incomplete), display_meta="/".join(aliases))

    def get_completion_for_Range_types(
        self, param_type: "Union[click.IntRange, click.FloatRange]", incomplete: str
    ) -> "Generator[Completion, None, None]":
        if isinstance(param_type, click.IntRange):
            _min = (param_type.min or 0) * (not param_type.min_open)
            _max = (param_type.max or 0) * (not param_type.max_open)
            _display_template = "{}"

        elif HAS_CLICK8 and isinstance(param_type, click.FloatRange):
            _min = int(param_type.min or 0) * (not param_type.min_open)
            _max = int(param_type.max or 0) * (not param_type.max_open)
            _display_template = "{}."

        for i in range(_min, _max + 1):  # type: ignore[arg-type]
            text = _display_template.format(i)
            if text.startswith(incomplete):
                yield Completion(text, -len(incomplete))

        # clamp = " clamped" if param_type.clamp else ""
        # display_meta = f"{param_type._describe_range()}{clamp}"

        # return [Completion("-", display_meta=display_meta)]

    def get_completion_from_params(
        self,
        ctx: "Context",
        param: "Parameter",
        args: "Iterable[str]",
        incomplete: str,
    ) -> "Generator[Completion, None, None]":
        # choices: "List[Completion]" = []
        param_type: "click.ParamType" = param.type

        if isinstance(param_type, _RANGE_TYPES):
            yield from self.get_completion_for_Range_types(param_type, incomplete)

        # elif isinstance(param_type, click.Tuple):
        #     return [Completion("-", display=_type.name) for _type in param_type.types]

        # shell_complete method for click.Choice is introduced in click-v8
        elif not HAS_CLICK8 and isinstance(param_type, click.Choice):
            yield from self.get_completion_from_choices_click_le_7(param_type, incomplete)

        elif isinstance(param_type, click.types.BoolParamType):
            yield from self.get_completion_for_Boolean_type(incomplete)

        elif isinstance(param_type, (click.Path, click.File)):
            yield from self.get_completion_for_Path_types(incomplete)

        elif getattr(param, AUTO_COMPLETION_PARAM, None) is not None:
            yield from self.get_completion_from_autocompletion_functions(
                param, ctx, args, incomplete
            )

        else:
            yield from []

    def get_completion_for_command_args(
        self,
        ctx: "Context",
        state: "ArgsParsingState",
        args: "Iterable[str]",
        incomplete: "str",
    ) -> "Generator[Completion, None, None]":
        opt_names = []
        for param in state.current_command.params:  # type: ignore[union-attr]
            if isinstance(param, click.Argument) or getattr(param, "hidden", False):
                continue

            opts = param.opts + param.secondary_opts

            previous_args = args[: param.nargs * -1]  # type: ignore[index]
            already_present = any(opt in previous_args for opt in opts)
            hide = self.show_only_unused_opts and already_present and not param.multiple

            opts_with_incomplete_prefix = [
                opt for opt in opts if opt.startswith(incomplete) and not hide
            ]
            opts_for_completion = opts_with_incomplete_prefix

            if (  # If param is a bool flag, and its already in args
                getattr(param, "is_bool_flag", False)
                and any(i in args for i in opts)
                # Or the param is called recently within its nargs length
            ) or not opts_with_incomplete_prefix:
                continue

            if self.shortest_opts_only:
                _, sep = join_options(opts)
                display = sep.join(opts_with_incomplete_prefix)
                opts_for_completion = [  # Changed for Actual Completion
                    min(opts_with_incomplete_prefix, key=len)
                ]

            for opt in opts_for_completion:
                display_meta = getattr(param, "help", "")

                if not self.shortest_opts_only:
                    display = opt

                if not (getattr(param, "count", False) or param.default is None):
                    display += f" [Default={param.default}]"

                opt_names.append(
                    Completion(
                        opt,
                        -len(incomplete),
                        display=display,
                        display_meta=display_meta,
                        style=self.styles["option"],
                    )
                )

        current_param = state.current_param

        current_param_is_None = current_param is None
        if current_param_is_None or isinstance(current_param, click.Argument):
            yield from opt_names

        if not (current_param_is_None or getattr(current_param, "hidden", False)):
            yield from self.get_completion_from_params(
                ctx, current_param, args, incomplete  # type: ignore[arg-type]
            )

    def get_completions_for_command(
        self,
        ctx: "Context",
        state: "ArgsParsingState",
        args: "Iterable[str]",
        incomplete: str,
    ) -> "Generator[Completion, None, None]":
        current_group = state.current_group
        current_command_exists = state.current_command is not None
        is_chain = getattr(current_group, "chain", False)

        if current_command_exists:
            yield from self.get_completion_for_command_args(ctx, state, args, incomplete)

        if not current_command_exists or (is_chain and any(ctx.params.values())):
            for cmd_name in current_group.list_commands(ctx):
                command = current_group.get_command(ctx, cmd_name)
                if getattr(command, "hidden", False):
                    continue

                elif cmd_name.startswith(incomplete):
                    yield Completion(
                        cmd_name,
                        -len(incomplete),
                        display_meta=getattr(command, "short_help", ""),
                    )

    def get_completions(
        self, document: "Document", complete_event: "Optional[CompleteEvent]" = None
    ) -> "Generator[Completion, None, None]":
        """Provides :class:`~prompt_toolkit.completion.Completion`
        objects from the obtained command line string.
        Code analogous to :func:`~click._bashcomplete.do_complete`.

        Keyword arguments:
        ---
        :param:`document` - :class:`~prompt_toolkit.document.Document` object
        containing the incomplete command line string
        :param:`complete_event` - :class:`~prompt_toolkit.completion.CompleteEvent`
        object of the current prompt.

        Yield: :class:`~prompt_toolkit.completion.Completion` objects for
            command line autocompletion
        """
        if (
            self.internal_commands_system is not None
            and self.internal_commands_system.get_prefix(document.text_before_cursor)
        ):
            if ISATTY:
                TOOLBAR.state_reset()
            return

        try:
            parsed_ctx, ctx_command, state, args, incomplete = _resolve_state(
                self.cli_ctx, document.text_before_cursor
            )

            # print(f'\n(from get_completions) {vars(parsed_ctx) = }\n')
            # print(f'{state = }')
            if ISATTY:
                TOOLBAR.update_state(state)

            if getattr(ctx_command, "hidden", False):
                return

            yield from self.get_completions_for_command(
                parsed_ctx, state, args, incomplete
            )

        except Exception as e:
            # TOOLBAR.state_reset()
            raise e
            # pass
