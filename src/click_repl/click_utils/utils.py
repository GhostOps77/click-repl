from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

import click
from click import Command, Context, Parameter

from .._compat import RANGE_TYPES_TUPLE, MultiCommand

if TYPE_CHECKING:
    from ..parser import InfoDict


@lru_cache(maxsize=128)
def get_info_dict(
    obj: Context | Command | Parameter | click.ParamType,
) -> InfoDict:
    """
    :meth:`~click.Context.get_info_dict`
    :meth:`~click.Command.get_info_dict`
    :meth:`~click.Group.get_info_dict`
    :meth:`~click.Parameter.get_info_dict`
    :meth:`~click.ParamType.get_info_dict`
    """

    if isinstance(obj, Context):
        return {
            "command": get_info_dict(obj.command),
            "params": obj.params,
        }

    info_dict: InfoDict = {}

    if isinstance(obj, Command):
        ctx = Context(obj)

        info_dict.update(
            name=obj.name,
            params=tuple(get_info_dict(param) for param in obj.get_params(ctx)),
            callback=obj.callback,
        )

        if isinstance(obj, MultiCommand):
            commands = {}

            for name in obj.list_commands(ctx):
                command = obj.get_command(ctx, name)

                if command is None:
                    continue

                commands[name] = get_info_dict(command)

            info_dict.update(commands=commands, chain=obj.chain)

    elif isinstance(obj, Parameter):
        info_dict.update(
            name=obj.name,
            param_type_name=obj.param_type_name,
            opts=obj.opts,
            secondary_opts=obj.secondary_opts,
            type=get_info_dict(obj.type),
            required=obj.required,
            nargs=obj.nargs,
            multiple=obj.multiple,
        )

        if isinstance(obj, click.Option):
            info_dict.update(
                is_flag=obj.is_flag,
                flag_value=obj.flag_value,
                count=obj.count,
                hidden=obj.hidden,
            )

    elif isinstance(obj, click.ParamType):
        param_type = type(obj).__name__.split("ParamType", 1)[0]
        param_type = param_type.split("ParameterType", 1)[0]

        # Custom subclasses might not remember to set a name.
        name = getattr(obj, "name", param_type)
        info_dict.update(param_type=param_type, name=name)

        if isinstance(obj, click.types.FuncParamType):
            info_dict["func"] = obj.func

        elif isinstance(obj, click.Choice):
            info_dict["choices"] = obj.choices
            info_dict["case_sensitive"] = obj.case_sensitive

        elif isinstance(obj, click.DateTime):
            info_dict["formats"] = obj.formats

        elif isinstance(obj, RANGE_TYPES_TUPLE):
            info_dict.update(
                min=obj.min,
                max=obj.max,
                min_open=getattr(obj, "min_open", False),
                max_open=getattr(obj, "max_open", False),
                clamp=obj.clamp,
            )

        elif isinstance(obj, click.File):
            info_dict.update(mode=obj.mode, encoding=obj.encoding)

        elif isinstance(obj, click.Path):
            info_dict.update(
                exists=obj.exists,
                file_okay=obj.file_okay,
                dir_okay=obj.dir_okay,
                writable=obj.writable,
                readable=obj.readable,
                allow_dash=obj.allow_dash,
            )

        elif isinstance(obj, click.Tuple):
            info_dict["types"] = tuple(get_info_dict(t) for t in obj.types)

    return info_dict
