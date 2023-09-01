"""
`click_repl.bottom_bar`

Utility for the Bottom bar of the REPL.
"""
import typing as t

import click
from prompt_toolkit.formatted_text import HTML

from ._formatting import Bold
from ._formatting import Color
from ._formatting import StrikeThrough
from ._formatting import Underline
from ._globals import _METAVAR_PARAMS
from ._globals import _RANGE_TYPES
from ._globals import HAS_CLICK8
from ._globals import ISATTY
from .utils import _join_options

# from ._formatting import FormattedString

if t.TYPE_CHECKING:
    from typing import Optional, List, Union

    from click import Parameter
    from click.types import ParamType

    from .parser import ReplParsingState
    from ._formatting import HTMLTag

    ParamInfo = t.TypedDict(
        "ParamInfo", {"name": str, "type info": List[str], "desc str": str}
    )


__all__ = ["BottomBar"]


class BottomBar:
    """Toolbar class to manage the text in the bottom toolbar."""

    # __slots__ = ("state", "_formatted_text", "show_hidden_params", "marquee")

    def __init__(self, show_hidden_params: bool = False, marquee: bool = True) -> None:
        """
        Initialize the `BottomBar` class.

        Parameters
        ----------
        show_hidden_params : bool, default: False
            Determines whether to display hidden params at bottom bar.

        marquee : bool, default: True
            Displays the text in marquee style if it's content exceeds the
            terminal's display.
        """

        self.state: "Optional[ReplParsingState]" = None
        self._formatted_text: "Union[str, HTML]" = ""
        self.show_hidden_params = show_hidden_params
        self.marquee = marquee
        self.marquee_pointer_position = 0

    def marquee_text(self) -> "Union[str, HTML]":
        return self._formatted_text

    def __call__(self) -> "Union[str, HTML]":
        return self.get_formatted_text()

    def reset_state(self) -> None:
        self.state = None
        self._formatted_text = ""

    def get_formatted_text(self) -> "Union[str, HTML]":
        # return str(self.state)
        # if len(self._formatted_text) <= os.get_terminal_size().columns:
        return self._formatted_text

        # return self._formatted_text.get_text()

    def update_state(self, state: "ReplParsingState") -> None:
        if not ISATTY or state is None or state == self.state:
            return

        self.state = state
        self._formatted_text = self.make_formatted_text()
        # self._formatted_text = str(state)

    def get_group_metavar_template(self) -> "Union[str, HTML]":
        # Gets the metavar to describe the CLI Group, indicating
        # whether it is a chained Group or not.

        state = self.state
        current_group = state.current_group  # type: ignore[union-attr]

        if not current_group.list_commands(state.current_ctx):  # type: ignore[union-attr]
            # Empty string if there are no subcommands.
            return ""

        if getattr(current_group, "chain", False):
            # Metavar for chained group.
            res = (
                f"{Bold(f'Group {current_group.name}:')} "
                "COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]..."
            )

        else:
            # Metavar for non-chained group.
            res = f"{Bold(f'Group {current_group.name}:')} COMMAND [ARGS]..."

        return HTML(res)

    def get_param_info(self, param: "Parameter") -> str:
        param_info: "ParamInfo" = {
            "name": self.get_param_name(param),
            "type info": [],
            "desc str": "",
        }

        if self.state.current_param == param:  # type: ignore[union-attr]
            # Displaying detailed information only for the current parameter
            # in the bottom bar, to save space.

            type_info = self.get_param_type_info(param, param.type)

            if not isinstance(type_info, list):
                type_info = [type_info]

            param_info["type info"] = type_info
            param_info["desc str"] = self.get_param_nargs_info(param, param_info)

        return self.format_parsing_state_for_param(param, param_info)

    def get_param_name(self, param: "Parameter") -> str:
        if isinstance(param, click.Argument):
            return param.name  # type: ignore

        else:
            if not param.is_bool_flag:  # type: ignore[attr-defined]
                return max(  # type: ignore
                    param.opts + param.secondary_opts,
                    key=lambda x: len(click.parser.split_opt(x)[1]),
                )

            opts, split_char = _join_options(param.opts)
            opts_html_tag = Color(split_char.join(opts), "green")

            if not param.secondary_opts:
                return str(opts_html_tag)

            secondary_opts, split_char = _join_options(param.secondary_opts)
            secondary_opts_html_tag = Color(split_char.join(secondary_opts), "red")

            return f"{opts_html_tag}|{secondary_opts_html_tag}"

    def get_param_type_info(
        self, param: "Parameter", param_type: "ParamType"
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
            type_info = param_type.name  # [1:-1]

            if HAS_CLICK8:
                clamp = " clamped" if param_type.clamp else ""
                type_info += f" {param_type._describe_range()}{clamp}"

            else:
                lop = "<" if param_type.min_open else "<="
                rop = "<" if param_type.max_open else "<="
                type_info += f" {param_type.min}{lop}x{rop}{param_type.max}"

        elif isinstance(param_type, _METAVAR_PARAMS):
            # Here, only the name of the type's class is included in type_info. This
            # is because metavar of classes generated by click itself can have
            # potentially longer strings.
            for metavar_param in _METAVAR_PARAMS:
                if isinstance(param_type, metavar_param):
                    type_info = metavar_param.__name__
                    break

        # elif isinstance(param_type, _PATH_TYPES):
        #     # If the parameter type is an instance of any of these 3 types mentioned
        #     # above, there is no need to mention anything special about them. The
        #     # type information is simply added as the name attribute of the
        #     # respective type.
        #     type_info = param_type.name

        elif param_type not in (click.STRING, click.UNPROCESSED):
            type_info = getattr(param_type, "name", f"{param_type}")

        if type_info:
            type_info = f"<{type_info}>"

        return type_info

    def get_param_nargs_info(self, param: "Parameter", param_info: "ParamInfo") -> str:
        param_info_desc = f"{param_info['name']} {' '.join(param_info['type info'])}"

        if param.nargs == 1 or isinstance(param.type, click.Tuple):
            return param_info_desc

        elif param.nargs == -1:
            return f"[{param_info_desc} ...]"

        elif param.nargs > 1:
            # Calculate the number of non-None values received for the parameter.
            param_values = self.state.current_ctx.params.get(  # type: ignore[union-attr]
                param.name, []  # type: ignore[arg-type]
            )

            if param_values is None:
                not_none_vals_count = 0

            else:
                not_none_vals_count = sum(1 for i in param_values if i is not None)

            return f"[{param_info_desc} ({not_none_vals_count}/{param.nargs})]"

        return param_info_desc

    def format_parsing_state_for_param(
        self, param: "Parameter", param_info: "ParamInfo"
    ) -> str:
        # Formats the provided param_info string using HTML to indicate whether
        # the parameter is current, awaiting REPL input, or has received values.

        state = self.state

        if param == state.current_param:  # type: ignore[union-attr]
            # The current parameter is shown in bold and underlined letters.
            if not isinstance(param.type, click.Tuple):
                return str(Underline(Bold(param_info["desc str"])))

            res = str(Bold(param_info["name"]))
            type_info: "List[Union[str, HTMLTag]]" = []
            stop = False

            for type_str, value in zip(
                param_info["type info"],
                state.current_ctx.params[param.name],  # type: ignore
            ):
                if value is not None:
                    # To display that this paramtype has recieved its value,
                    # by strikethrough.
                    type_info.append(StrikeThrough(type_str))

                elif not stop:
                    # To display the current paramtype that requires a value.
                    type_info.append(Underline(Bold(type_str)))
                    stop = True

                else:
                    # To display it as it is, denoting that it still haven't recieved its
                    # value, and it's not the current paramtype in the given tuple type.
                    type_info.append(type_str)

            res += f" ({' '.join(type_info)})"  # type: ignore[arg-type]
            return res

        param_info_str = param_info["name"]

        if (
            any(getattr(param, attr, False) for attr in ("count", "is_flag"))
            or param in state.remaining_params  # type: ignore[union-attr]
        ):
            # Counters, Flags, and Parameters that are awaiting for values
            # are displayed without special formatting.
            return param_info_str

        # Parameters that have already received values are displayed
        # with a strikethrough.
        return str(StrikeThrough(param_info_str))

    def make_formatted_text(self) -> "Union[str, HTML]":
        state = self.state

        current_command = state.current_command  # type: ignore[union-attr]

        if current_command is None:
            # If there is no command currently entered in the REPL,
            # the function returns the metavar template of the
            # parent/CLI/current Group.
            return self.get_group_metavar_template()

        if isinstance(current_command, click.Group):
            command_type = "Group"
        else:
            command_type = "Command"

        output_text = f"{command_type} {current_command.name}"

        formatted_params_info = [
            self.get_param_info(param)
            for param in current_command.params
            if not getattr(param, "hidden", False)
            or (
                param == state.current_param  # type: ignore[union-attr]
                and self.show_hidden_params
            )
        ]

        if formatted_params_info:
            formatted_params_info.insert(0, str(Bold(f"{output_text}: ")))
            return " ".join(formatted_params_info)
        else:
            output_text = str(Bold(output_text))

        return output_text
