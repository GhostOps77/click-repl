import click
import typing as t

from click.parser import split_opt

from prompt_toolkit.formatted_text import HTML

from ._globals import _RANGE_TYPES

if t.TYPE_CHECKING:
    from typing import Optional
    from .parser import ArgsParsingState


__all__ = ["TOOLBAR", "ToolBar"]


def join_options(options: "t.Sequence[str]") -> "t.Tuple[t.List[str], str]":
    """Given a list of option strings this joins them in the most appropriate
    way and returns them in the form ``(formatted_string,
    any_prefix_is_slash)`` where the second item in the tuple is a flag that
    indicates if any of the option prefixes was a slash.
    """
    rv = []
    any_prefix_is_slash = False

    for opt in options:
        prefix = split_opt(opt)[0]
        any_prefix_is_slash = prefix == "/"
        rv.append((len(prefix), opt))

    rv.sort(key=lambda x: x[0])
    return (x[1] for x in rv), ";" if any_prefix_is_slash else "/"


class ToolBar:
    def __init__(self) -> None:
        self.state: "Optional[ArgsParsingState]" = None
        self._formatted_text: "t.Union[str, HTML]" = ""

    def state_reset(self) -> None:
        self.state = None
        self._formatted_text = ""

    def get_formatted_text(self) -> "t.Union[str, HTML]":
        return self._formatted_text

    def update_state(self, state: "ArgsParsingState") -> None:
        self.state = state
        self._formatted_text = self.make_formatted_text()

    def make_formatted_text(self) -> "t.Union[str, HTML]":
        state = self.state

        if state is None:
            return ""

        if state.current_cmd is None:
            return HTML(
                f"<b>{type(state.current_group).__name__} "
                f"{state.current_group.name}: "
                "&lt;COMMAND&gt;</b> [OPTIONS ...] ARGS ..."
            )

        out = state.current_cmd.name
        if isinstance(state.current_cmd, click.MultiCommand):
            out = f"{type(state.current_cmd).__name__} {out}"

        out = f"<b>{out}:</b> "

        # print(f'\n{state.ctx.params = }\n{state.ctx.args = }\n'
        #       f'{state.remaining_params = }')

        for param in state.current_cmd.params:
            if isinstance(param, click.Argument):
                param_info = f"{param.name} "
            else:
                options_metavar_list = param.opts + param.secondary_opts
                if len(options_metavar_list) == 1:
                    param_info = f"{options_metavar_list[0].strip()} "
                else:
                    opts, sep = join_options(options_metavar_list)
                    param_info = f"[{sep.join(opts)}] "

            type_info = " "
            param_type = param.type

            if param_type not in (click.STRING, click.UNPROCESSED):
                if isinstance(param_type, _RANGE_TYPES):
                    if getattr(param, "count", False):
                        type_info += "counter"

                    else:
                        type_info += (
                            f"{param_type}".strip("<>")
                            .replace("<", "&lt;")
                            .replace(">", "&gt;")
                        )

                elif isinstance(param_type, (click.Choice, click.DateTime)):
                    type_info += param_type.get_metavar(param)

                elif isinstance(param_type, (click.Path, click.File, click.Tuple)):
                    type_info += f"{param_type.name}"

                else:
                    type_info += f"{param_type}"

            type_info = type_info.strip()
            if type_info:
                type_info = f" &lt;{type_info}&gt;"

            param_info = f"{param_info.strip()}{type_info}"

            if param.nargs == -1:
                param_info = f"[{param_info} ...]"

            elif param.nargs > 1:
                param_info = f"[{param_info}x{param.nargs}]"

            if param == getattr(state, "current_param", None):
                out += f"<b>{param_info.strip()}</b> "

            elif (
                any(getattr(param, i, False) for i in ("count", "is_bool_flag"))
                or param in state.remaining_params
            ):
                out += f"{param_info} "

            else:
                out += f"<s>{param_info}</s> "

        # return out.strip()
        return HTML(out.strip())


TOOLBAR = ToolBar()
