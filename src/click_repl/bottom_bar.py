import typing as t

import click
from prompt_toolkit.formatted_text import HTML

from ._globals import _RANGE_TYPES
from ._globals import HAS_CLICK6
from .utils import join_options

if t.TYPE_CHECKING:
    from typing import Optional

    from .parser import ArgsParsingState
    from click import Parameter


__all__ = ["TOOLBAR", "ToolBar"]


# click.DateTime type is introduced in click v7
# These are the types that generate metavar information by themselves
if HAS_CLICK6:
    _METAVAR_PARAMS = (click.Choice,)
else:
    _METAVAR_PARAMS = (click.Choice, click.DateTime)  # type: ignore[assignment]


class ToolBar:
    """Toolbar class to manage the text in the bottom toolbar"""

    def __init__(self) -> None:
        self.state: "Optional[ArgsParsingState]" = None
        self._formatted_text: "t.Union[str, HTML]" = ""

    def state_reset(self) -> None:
        self.state = None
        self._formatted_text = ""

    def get_formatted_text(self) -> "t.Union[str, HTML]":
        # return str(self.state)
        # if self.state:
        #     return (
        #         f"{self.state.cmd_ctx.args} {self.state.cmd_ctx.params}"
        #     )
        # return ""
        return self._formatted_text

    def update_state(self, state: "ArgsParsingState") -> None:
        if state == self.state:
            return

        self.state = state
        self._formatted_text = self.make_formatted_text()

    def get_group_metavar_template(self) -> "HTML":
        current_group = self.state.current_group  # type: ignore[union-attr]

        if getattr(current_group, "chain", False):
            metavar = "COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]..."
        else:
            metavar = "COMMAND [ARGS]..."

        return HTML(
            f"<b>{type(current_group).__name__}</b> " f"{current_group.name}: {metavar}"
        )

    def get_param_info(self, param: "Parameter") -> str:
        if isinstance(param, click.Argument):
            param_info = f"{param.name} "

        else:
            options_metavar_list = param.opts + param.secondary_opts
            if len(options_metavar_list) == 1:
                param_info = f"{options_metavar_list[0].strip()} "
            else:
                opts, _ = join_options(options_metavar_list)
                # param_info = f"[{sep.join(opts)}] "
                param_info = f"{min(opts)} "

        return param_info.strip()

    def get_param_type_info(self, param: "Parameter") -> str:
        param_type = param.type
        type_info = ""

        if isinstance(param_type, _RANGE_TYPES):
            if getattr(param, "count", False):
                type_info += "counter"

            else:
                type_info += (
                    f"{param_type}"[1:-1].replace("<", "&lt;").replace(">", "&gt;")
                )

        elif isinstance(param_type, _METAVAR_PARAMS):
            type_info += param_type.get_metavar(param)

        elif isinstance(param_type, (click.Path, click.File, click.Tuple)):
            type_info += param_type.name

        elif param_type not in (click.STRING, click.UNPROCESSED):
            type_info += f"{param_type}"

        if type_info:
            type_info = f" &lt;{type_info}&gt;"

        return type_info

    def get_param_nargs_info(self, param: "Parameter", param_info: str) -> str:
        if param.nargs == -1:
            return f"[{param_info} ...]"

        elif param.nargs > 1:
            return f"[{param_info}x{param.nargs}]"

        return param_info

    def format_pre_parsed_parameters(self, param: "Parameter", param_info: str) -> str:
        if param == getattr(self.state, "current_param", None):
            return f"<b>{param_info}</b> "

        elif (
            any(getattr(param, attr, False) for attr in ("count", "is_bool_flag"))
            or param in self.state.remaining_params  # type: ignore[union-attr]
        ):
            return f"{param_info} "

        return f"<s>{param_info}</s> "

    def make_formatted_text(self) -> "t.Union[str, HTML]":
        state = self.state

        if state is None:
            return ""

        current_command = state.current_command

        if current_command is None:
            return self.get_group_metavar_template()

        out = current_command.name
        if isinstance(current_command, click.MultiCommand):
            out = f"{type(current_command).__name__} {out}"

        # print(f'\n{state.ctx.params = }\n{state.ctx.args = }\n'
        #       f'{state.remaining_params = }')

        all_params_info = ""

        for param in current_command.params:
            param_info = self.get_param_info(param) + self.get_param_type_info(param)

            if param.nargs != 1:
                param_info = self.get_param_nargs_info(param, param_info)

            all_params_info += self.format_pre_parsed_parameters(param, param_info)

        all_params_info = all_params_info.strip()
        if all_params_info:
            return HTML(f"<b>{out}:</b> {all_params_info}")

        return HTML(f"<b>Command {out}</b>")


TOOLBAR = ToolBar()
