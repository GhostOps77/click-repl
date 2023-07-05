"""
`click_repl.bottom_bar`

Utilities to manage bottom display bar of the click_repl app.
"""
import typing as t

import click
from prompt_toolkit.formatted_text import HTML

from ._globals import _RANGE_TYPES
from ._globals import HAS_CLICK6
from ._globals import ISATTY

if t.TYPE_CHECKING:
    from typing import Optional

    from click import Parameter

    from .parser import ArgsParsingState


__all__ = ["BOTTOMBAR", "BottomBar"]


# click.DateTime type is introduced in click v7.
# These types can generate metavar information by themselves.
# Therefore, we're gonna just use their names, to display it in
# the bottom toolbar.
if HAS_CLICK6:
    _METAVAR_PARAMS = (click.Choice,)
else:
    _METAVAR_PARAMS = (click.Choice, click.DateTime)  # type: ignore[assignment]


class BottomBar:
    """Toolbar class to manage the text in the bottom toolbar."""

    def __init__(self) -> None:
        """Initialize the BottomBar class."""

        self.state: "Optional[ArgsParsingState]" = None
        self._formatted_text: "t.Union[str, HTML]" = ""

    def reset_state(self) -> None:
        """
        Resets the `click_repl.parser.ArgsParsingState` object
        in order to clear the currently displayed parsing state
        information from the bottom bar.
        """

        if not ISATTY:
            # We don't have to render the bottom toolbar if the stdin is not
            # connected to a TTY device.
            return

        self.state = None

        # Clearing the text that shows up in the bottom bar.
        self._formatted_text = ""

    def get_formatted_text(self) -> "t.Union[str, HTML]":
        """
        Used by `prompt_toolkit.PromptSession` to retrieve the
        text that need to be rendered in the bottom bar.

        Returns
        -------
        str or prompt_toolkit.formatted_text.HTML
            The text that needs to be displayed in the bottom bar.
        """

        if not ISATTY:
            return ""

        return self._formatted_text

    def update_state(self, state: "ArgsParsingState") -> None:
        """
        Updates the current state of the `click_repl.parser.ArgsParsingState`
        object held in the `self.state` attribute.

        Parameters
        ----------
        state : click_repl.parser.ArgsParsingState
            A `click_repl.parser.ArgsParsingState` object that holds
            information about the current command and parameter, based
            on the current arguments.
        """

        if not ISATTY or state == self.state:
            return

        self.state = state
        self._formatted_text = self.make_formatted_text()

    def get_group_metavar_template(self) -> "HTML":
        """
        Gets the metavar to describe the CLI Group, indicating
        whether it is a chained Group or not.

        Returns
        -------
        prompt_toolkit.formatted_text.HTML
            A `prompt_toolkit.formatted_text.HTML` object that represents
            the metavar of the CLI Group information.
        """

        current_group = self.state.current_group  # type: ignore[union-attr]

        if getattr(current_group, "chain", False):
            metavar = "COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]..."
        else:
            metavar = "COMMAND [ARGS]..."

        return HTML(f"<b>Group</b> {current_group.name}: {metavar}")

    def get_param_info(self, param: "Parameter") -> str:
        """
        Returns a string containing basic information about the given
        parameter `param`, that to be displayed in the bottom bar.

        Parameters
        ----------
        param : click.Parameter
            A `click.Parameter` object to retrieve information from.

        Returns
        -------
        str
            A string containing basic information about the given parameter.
        """

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
        """
        Retrieves information about the type of the given `param` parameter.

        Parameters
        ----------
        param : click.Parameter
            A `click.Parameter` object to retrieve information from.

        Returns
        -------
        str
            A string containing basic information about the type of the given parameter.
        """

        param_type = param.type
        type_info = ""

        if isinstance(param_type, _RANGE_TYPES):
            if getattr(param, "count", False):
                # A counting option has the parameter type of IntRange.
                # So, its just represented as "counter".

                type_info += "counter"

            else:
                # The < and > symbols at the beginning and end of the repr of the
                # class are removed by slicing it with [1:-1]. The < and > symbols
                # within the representation, which represent the range, are replaced
                # with their URL encoded forms (&lt; and &gt;) to display them
                # correctly in HTML form.

                type_info += (
                    f"{param_type}"[1:-1].replace("<", "&lt;").replace(">", "&gt;")
                )

        elif isinstance(param_type, _METAVAR_PARAMS):
            # Here, only the name of the type's class is included in type_info. This
            # is because metavar classes generated by click itself can have
            # potentially longer strings.

            for i in _METAVAR_PARAMS:
                if isinstance(param_type, i):
                    type_info += i.__name__
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
        """
        Retrieves about the nargs information about the given parameter `param`,
        and adds it to the pre-existing `param_info` string, that has other
        information about the parameter `param`.

        Parameters
        ----------
        param : click.Parameter
            A `click.Parameter` object to retrieve information from.

        param_info : str
            A string containing pre-existing information about
            the parameter `param`.

        Returns
        -------
        str
            An updated string of `param_info` that includes information
            about the `nargs` attribute of the given parameter.
        """

        if param.nargs == -1:
            # This says that its a greedy consuming value.
            return f"[{param_info} ...]"

        elif param.nargs > 1:
            return f"[{param_info}x{param.nargs}]"

        return param_info

    def format_parsing_state_for_params(self, param: "Parameter", param_info: str) -> str:
        """
        Formats the given parameter info `param_info` based on the state of
        the parameter `param`, indicating whether it is the current parameter,
        whether it is yet to receive values from the REPL, or whether it has
        already received its values.

        Parameters
        ----------
        param : click.Parameter
            A `click.Parameter` object to retrieve information from.

        param_info : str
            A string containing pre-existing information about
            the parameter `param`.

        Returns
        -------
        str
            An updated string of `param_info` that includes information about
            the current state of the parameter in terms of receiving values.
        """

        if param == getattr(self.state, "current_param", None):
            # The current parameter is shown in bold letters.
            return f"<b>{param_info}</b>"

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
        """
        Generates and returns the formatted text based on the
        current parsing state.

        Returns
        -------
        str or prompt_toolkit.formatted_text.HTML
            The formatted text that needs to be displayed in the bottom bar.
        """

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
            output_text = f"Group {output_text}"

        # Join the strings containing information about each separate
        # parameter in the current command.
        formatted_params_info = " ".join(
            [
                self.format_parsing_state_for_params(param, self.get_param_info(param))
                for param in current_command.params
            ]
        )

        if formatted_params_info:
            # If there is information available about the parameters
            # for the current command, it is displayed along with
            # the command name.
            return HTML(f"<b>{output_text}:</b> {formatted_params_info}")

        # Otherwise, display the command name along with its type.
        # It is most likely to be a click.Command.
        return HTML(f"<b>Command {output_text}</b>")


BOTTOMBAR = BottomBar()
