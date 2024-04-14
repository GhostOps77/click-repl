from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, Any

import click
from click import Command, Context, Parameter
from click.utils import _expand_args

from ._compat import RANGE_TYPES_TUPLE, MultiCommand, split_opt
from .proxies import _create_proxy_command

if TYPE_CHECKING:
    from .parser import InfoDict


def get_option_flag_sep(option_names: list[str]) -> str:
    any_prefix_is_slash = any(split_opt(opt)[0] == "/" for opt in option_names)
    return ";" if any_prefix_is_slash else "/"


def join_options(options: list[str]) -> tuple[list[str], str]:
    """
    Reference: :meth:`~click.formatting.join_options`
    """
    # Same implementation as :meth:`~click.formatting.join_options`, but much simpler.

    # Parameters
    # ----------
    # options
    #     List of option flags that needs to be joined together.

    # References
    # ----------
    # :meth:`~click.formatting.join_options`
    return sorted(options, key=len), get_option_flag_sep(options)


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
    # Similar to the ``get_info_dict`` method implementation in click objects,
    # but it only retrieves the essential attributes required to
    # differentiate between different ``ReplParsingState`` objects.

    # Parameters
    # ----------
    # obj
    #     Click object for which the info dict needs to be generated.

    # Returns
    # -------
    # InfoDict
    #     Dictionary that holds crucial details about the given click object
    #     that can be used to uniquely identify it.

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
        param_type = type(obj).__name__.partition("ParamType")[0]
        param_type = param_type.partition("ParameterType")[0]

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


@lru_cache(maxsize=3)
def _generate_next_click_ctx(
    group: MultiCommand,
    parent_ctx: Context,
    args: tuple[str, ...],
    proxy: bool = False,
    **ctx_kwargs: dict[str, Any],
) -> tuple[Context, Command | None]:

    if not args:
        return parent_ctx, None

    # Since the resolve_command method only accepts string arguments in a
    # list format, we explicitly convert args into a list.
    _args = _expand_args(args)

    name, cmd, _args = group.resolve_command(parent_ctx, _args)

    if cmd is None:
        return parent_ctx, None

    if proxy:
        # When using click.parser.OptionParser.parse_args, incomplete
        # string arguments that do not meet the nargs requirement of
        # the current parameter are normally ignored. However, in our
        # case, we want to handle these incomplete arguments. To
        # achieve this, we use a proxy command object to modify
        # the command parsing behavior in click.
        with _create_proxy_command(cmd) as _command:
            ctx = _command.make_context(name, _args, parent=parent_ctx, **ctx_kwargs)

    else:
        ctx = cmd.make_context(name, _args, parent=parent_ctx, **ctx_kwargs)

    return ctx, cmd


@lru_cache(maxsize=3)
def _resolve_context(ctx: Context, args: tuple[str, ...], proxy: bool = False) -> Context:
    """
    Reference: :func:`~click.shell_completion._resolve_context`
    """
    while args:
        command = ctx.command

        if isinstance(command, MultiCommand):
            if not command.chain:
                ctx, cmd = _generate_next_click_ctx(command, ctx, args, proxy=proxy)

                if cmd is None:
                    return ctx

            else:
                while args:
                    sub_ctx, cmd = _generate_next_click_ctx(
                        command,
                        ctx,
                        args,
                        proxy=proxy,
                        allow_extra_args=True,
                        allow_interspersed_args=False,
                    )

                    if cmd is None:
                        return ctx

                    args = tuple(sub_ctx.args)
                ctx = sub_ctx
            args = tuple(ctx.protected_args + ctx.args)

        else:
            break

    return ctx
