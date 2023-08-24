"""
`click_repl.bottom_bar`

Utility for the Bottom bar of the REPL.
"""
import typing as t

import click
from prompt_toolkit.formatted_text import HTML

from ._globals import _METAVAR_PARAMS
from ._globals import _PATH_TYPES
from ._globals import _RANGE_TYPES
from ._globals import ISATTY

if t.TYPE_CHECKING:
    from typing import Optional, List, Union

    from click import Parameter

    from .parser import ReplParsingState


__all__ = ["BottomBar"]


class BottomBar:
    """Toolbar class to manage the text in the bottom toolbar."""

    # __slots__ = ("state", "_formatted_text", "show_hidden_params", "marquee")

    def __init__(self, show_hidden_params: bool = False, marquee: bool = False) -> None:
        """
        Initialize the `BottomBar` class.

        Parameters
        ----------
        show_hidden_params : bool, default: False
            Determines whether to display hidden params at bottom bar.
        """

        self.state: "Optional[ReplParsingState]" = None
        self._formatted_text: "t.Union[str, HTML]" = ""
        self.show_hidden_params = show_hidden_params
        self.marquee = marquee

    def marquee_text(self) -> str:
        return ""

    def __call__(self) -> "t.Union[str, HTML]":
        return self.get_formatted_text()

    def reset_state(self) -> None:
        # if not ISATTY:
        #     # We don't have to render the bottom toolbar if the stdin is not
        #     # connected to a TTY device.
        #     return

        self.state = None
        self._formatted_text = ""

    def get_formatted_text(self) -> "t.Union[str, HTML]":
        # if not ISATTY:
        #     return ""

        # return str(self.state)
        return self._formatted_text

    def update_state(self, state: "ReplParsingState") -> None:
        if not ISATTY or state is None or state == self.state:
            return

        self.state = state

        self._formatted_text = self.make_formatted_text()
        # self._formatted_text = str(state)

    def get_group_metavar_template(self) -> "HTML":
        # Gets the metavar to describe the CLI Group, indicating
        # whether it is a chained Group or not.

        state = self.state
        current_group = state.current_group  # type: ignore[union-attr]

        if not current_group.list_commands(state.current_ctx):  # type: ignore[union-attr]
            # Empty string if there are no subcommands.
            return ""

        elif getattr(current_group, "chain", False):
            # Metavar for chained group.
            return (
                f"<b>Group {current_group.name}:</b> "
                "COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]..."
            )

        else:
            # Metavar for chained group.
            return f"<b>Group {current_group.name}:</b> COMMAND [ARGS]..."

    def get_param_info(self, param: "Parameter") -> str:
        param_info: "List[str]" = []

        if isinstance(param, click.Argument):
            param_info.append(param.name)  # type: ignore[arg-type]

        else:
            # If its a click.Option type, we print the smallest flag,
            # prioritizing limited space on the bottom bar for
            # other parameters.
            param_info.append(
                max(
                    param.opts + param.secondary_opts,
                    key=lambda x: len(click.parser.split_opt(x)[1]),
                )
            )

        if self.state.current_param == param:  # type: ignore[union-attr]
            # Displaying detailed information only for the current parameter
            # in the bottom bar, to save space.
            type_info = self.get_param_type_info(param, param.type)

            if isinstance(type_info, list):
                param_info.extend(type_info)
            else:
                param_info.append(type_info)

            if param.nargs != 1 and not isinstance(param.type, click.Tuple):
                param_info = [self.get_param_nargs_info(param, param_info)]

        return self.format_parsing_state_for_param(param, param_info)

    def get_param_type_info(
        self, param: "Parameter", param_type: "click.types.ParamType"
    ) -> "Union[str, List[str]]":
        if isinstance(param_type, click.Tuple):
            return [
                self.get_param_type_info(param, type_) or type_.name  # type: ignore[misc]
                for type_ in param_type.types
            ]

        type_info = ""

        if isinstance(param_type, _RANGE_TYPES):
            # The < and > symbols at the beginning and end of the repr of the
            # class are removed by slicing it with [1:-1]. The < and > symbols
            # within the representation, which represent the range, are replaced
            # with their URL encoded forms (&lt; and &gt;) to display them
            # correctly in HTML form.
            type_info = f"{param_type}"[1:-1]

        elif isinstance(param_type, _METAVAR_PARAMS):
            # Here, only the name of the type's class is included in type_info. This
            # is because metavar of classes generated by click itself can have
            # potentially longer strings.
            for metavar_param in _METAVAR_PARAMS:
                if isinstance(param_type, metavar_param):
                    type_info = metavar_param.__name__
                    break

        elif isinstance(param_type, _PATH_TYPES):
            # If the parameter type is an instance of any of these 3 types mentioned
            # above, there is no need to mention anything special about them. The
            # type information is simply added as the name attribute of the
            # respective type.
            type_info = param_type.name

        elif param_type not in (click.STRING, click.UNPROCESSED):
            type_info = f"{param_type}"

        if type_info:
            type_info = f"&lt;{type_info}&gt;".replace("<", "&lt;").replace(">", "&gt;")

        return type_info

    def get_param_nargs_info(self, param: "Parameter", param_info: "List[str]") -> str:
        _param_info = " ".join(param_info)

        if param.nargs == -1:
            return f"[{_param_info} ...]"

        elif param.nargs > 1:
            # Calculate the number of non-None values received for the parameter.
            param_values = self.state.current_ctx.params.get(  # type: ignore[union-attr]
                param.name, []  # type: ignore[arg-type]
            )

            if param_values is None:
                not_none_vals_count = 0

            else:
                not_none_vals_count = sum(1 for i in param_values if i is not None)

            return f"[{_param_info} ({not_none_vals_count}/{param.nargs})]"

            # return f"[{param_info}x{param.nargs}]"

        return _param_info

    def format_parsing_state_for_param(
        self, param: "Parameter", param_info: "List[str]"
    ) -> str:
        # Formats the given param_info string based on the state of
        # the given param, indicating whether it is the current parameter,
        # whether it is yet to receive values from the REPL, or whether it has
        # already received its values.

        if not param_info:
            return ""

        state = self.state

        if param == state.current_param:  # type: ignore[union-attr]
            # The current parameter is shown in bold and underlined letters.
            if not isinstance(param.type, click.Tuple):
                return f"<u><b>{' '.join(param_info)}</b></u>"

            res = f"<b>{param_info.pop(0)}</b>"
            type_info = []
            stop = False

            for type_str, value in zip(
                param_info, state.current_ctx.params[param.name]  # type: ignore
            ):
                if value is not None:
                    type_info.append(f"<s>{type_str}</s>")
                elif not stop:
                    type_info.append(f"<u><b>{type_str}</b></u>")
                    stop = True
                else:
                    type_info.append(type_str)

            res += f" ({' '.join(type_info)})"
            return res

        _param_info = " ".join(param_info)

        if (
            any(getattr(param, attr, False) for attr in ("count", "is_flag"))
            or param in state.remaining_params  # type: ignore[union-attr]
        ):
            # Counters, Flags, and Parameters that are awaiting for values
            # are displayed without special formatting.
            return _param_info

        # Parameters that have already received values are displayed
        # with a strikethrough.
        return f"<s>{_param_info}</s>"

    def make_formatted_text(self) -> "t.Union[str, HTML]":
        state = self.state

        current_command = state.current_command  # type: ignore[union-attr]

        if current_command is None:
            # If there is no command currently entered in the REPL,
            # the function returns the metavar template of the
            # parent/CLI/current Group.
            return self.get_group_metavar_template()

        output_text = current_command.name

        if isinstance(current_command, click.Group):
            output_text = f"Group {output_text}"  # type: ignore[no-redef]

        formatted_params_info = " ".join(
            [
                self.get_param_info(param)
                for param in current_command.params
                if not getattr(param, "hidden", False)
                or (
                    param == state.current_param  # type: ignore[union-attr]
                    and self.show_hidden_params
                )
            ]
        )

        if formatted_params_info:
            return HTML(f"<b>{output_text}:</b> {formatted_params_info}")

        # Here, It's most likely to be a click.Command object that has no parameters.
        return HTML(f"<b>Command {output_text}</b>")
