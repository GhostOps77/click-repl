import typing as t

import click
from prompt_toolkit.formatted_text import HTML

from ._globals import _RANGE_TYPES
from ._globals import get_current_repl_ctx
from ._globals import ISATTY

if t.TYPE_CHECKING:
    from typing import Optional

    from click import Parameter

    from .parser import ArgsParsingState


__all__ = ["BottomBar"]


_METAVAR_PARAMS = (click.Choice, click.DateTime)  # type: ignore[assignment]


class BottomBar:
    """Toolbar class to manage the text in the bottom toolbar."""

    def __init__(self) -> None:
        self.state: "Optional[ArgsParsingState]" = None
        self._formatted_text: "t.Union[str, HTML]" = ""
        self.show_hidden_params: bool = False

        if not ISATTY:
            return

        repl_ctx = get_current_repl_ctx(silent=True)

        if repl_ctx is None:
            return

        self.show_hidden_params = (
            repl_ctx.session.completer.show_hidden_params  # type: ignore[union-attr]
        )

    def reset_state(self) -> None:
        if not ISATTY:
            # We don't have to render the bottom toolbar if the stdin is not
            # connected to a TTY device.
            return

        self.state = None

        # Clearing the text that shows up in the bottom bar.
        self._formatted_text = ""

    def get_formatted_text(self) -> "t.Union[str, HTML]":
        if not ISATTY:
            return ""

        return self._formatted_text

    def update_state(self, state: "ArgsParsingState") -> None:
        if not ISATTY or (state and state == self.state):
            return

        self.state = state
        # self._formatted_text = self.make_formatted_text()
        self._formatted_text = str(state)

    def get_group_metavar_template(self) -> "HTML":
        # Gets the metavar to describe the CLI Group, indicating
        # whether it is a chained Group or not.

        current_group = self.state.current_group  # type: ignore[union-attr]

        if not current_group.list_commands(
            self.state.current_ctx  # type: ignore[union-attr]
        ):
            # Empty string if no subcommands.
            metavar = ""

        elif getattr(current_group, "chain", False):
            # Metavar for chained group.
            metavar = ": COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]..."

        else:
            # Metavar for chained group.
            metavar = ": COMMAND [ARGS]..."

        return HTML(f"<b>Group {current_group.name}</b>{metavar}")

    def get_param_info(self, param: "Parameter") -> str:
        if isinstance(param, click.Argument):
            param_info: str = param.name  # type: ignore[assignment]

        else:
            # If its a click.Option type, we print the smallest flag,
            # prioritizing limited space on the bottom bar for
            # other parameters.

            param_info = min(param.opts + param.secondary_opts, key=len)

        if self.state.current_param == param:  # type: ignore[union-attr]
            # Displaying detailed information only for the current parameter
            # in the bottom bar, to save space.

            param_info += self.get_param_type_info(param)

            if param.nargs != 1:
                param_info = self.get_param_nargs_info(param, param_info)

        return param_info

    def get_param_type_info(self, param: "Parameter") -> str:
        param_type = param.type
        type_info = ""

        if isinstance(param_type, _RANGE_TYPES):
            # The < and > symbols at the beginning and end of the repr of the
            # class are removed by slicing it with [1:-1]. The < and > symbols
            # within the representation, which represent the range, are replaced
            # with their URL encoded forms (&lt; and &gt;) to display them
            # correctly in HTML form.

            type_info += f"{param_type}"[1:-1].replace("<", "&lt;").replace(">", "&gt;")

        elif isinstance(param_type, _METAVAR_PARAMS):
            # Here, only the name of the type's class is included in type_info. This
            # is because metavar classes generated by click itself can have
            # potentially longer strings.

            for metavar_param in _METAVAR_PARAMS:
                if isinstance(param_type, metavar_param):
                    type_info += metavar_param.__name__
                    break

        elif isinstance(param_type, (click.Path, click.File, click.Tuple)):
            # If the parameter type is an instance of any of these 3 types mentioned
            # above, there is no need to mention anything special about them. The
            # type information is simply added as the name attribute of the
            # respective type.

            type_info += param_type.name

        elif param_type not in (click.STRING, click.UNPROCESSED):
            type_info += f"{param_type}"

        if type_info:
            type_info = f" &lt;{type_info}&gt;"

        return type_info

    def get_param_nargs_info(self, param: "Parameter", param_info: str) -> str:
        if param.nargs == -1:
            # This says that its a greedy consuming value.
            return f"[{param_info} ...]"

        elif param.nargs > 1:
            # Calculate the number of non-None values received for the parameter.
            param_values = self.state.current_ctx.params.get(  # type: ignore[union-attr]
                param.name, []  # type: ignore[arg-type]
            )

            if param_values is None:
                not_none_vals_count = 0

            else:
                not_none_vals_count = sum(1 for i in param_values if i is not None)

            return f"[{param_info} ({not_none_vals_count}/{param.nargs})]"

            # Displays the nargs of a parameter.
            # return f"[{param_info}x{param.nargs}]"

        return param_info

    def format_parsing_state_for_params(self, param: "Parameter", param_info: str) -> str:
        # Formats the given param_info string based on the state of
        # the given param, indicating whether it is the current parameter,
        # whether it is yet to receive values from the REPL, or whether it has
        # already received its values.

        if param == getattr(self.state, "current_param", None):
            # The current parameter is shown in bold and underlined letters.
            return f"<u><b>{param_info}</b></u>"

        elif (
            any(getattr(param, attr, False) for attr in ("count", "is_bool_flag"))
            or param in self.state.remaining_params  # type: ignore[union-attr]
        ):
            # Counters, Boolean Flags, and Parameters awaiting values are displayed
            # without special formatting.
            return param_info

        # Parameters that have already received values are displayed
        # with a strikethrough.
        return f"<s>{param_info}</s>"

    def make_formatted_text(self) -> "t.Union[str, HTML]":
        state = self.state

        if state is None:
            return ""

        current_command = state.current_command

        if current_command is None:
            # If there is no command currently entered in the REPL,
            # the function returns the metavar template of the
            # parent/CLI/current Group.
            return self.get_group_metavar_template()

        output_text = current_command.name

        if isinstance(current_command, click.Group):
            # If the current command is a Group, prepend "Group"
            # to the display text.
            output_text = f"Group {output_text}"  # type: ignore[no-redef]

        # Join the strings containing information about each separate
        # parameter in the current command.
        formatted_params_info = " ".join(
            [
                self.format_parsing_state_for_params(param, self.get_param_info(param))
                for param in current_command.params
                if not getattr(param, "hidden", False)
            ]
        )

        if formatted_params_info:
            # If there is information available about the parameters
            # for the current command, it is displayed along with
            # the command name.
            return HTML(f"<b>{output_text}:</b> {formatted_params_info}")

        # Otherwise, display the command name along with its type.
        # It is most likely to be a click.Command object that has no parameters.
        return HTML(f"<b>Command {output_text}</b>")
