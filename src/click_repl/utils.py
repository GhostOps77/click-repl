"""
Utilities to facilitate the functionality of the module.
"""

from __future__ import annotations

import os
from difflib import get_close_matches
from functools import lru_cache
from typing import Any

import click
from click import Command, Context, Group, Parameter

from ._globals import RANGE_TYPES
from .parser import (
    Incomplete,
    InfoDict,
    ReplParsingState,
    _resolve_incomplete,
    _resolve_repl_parsing_state,
)
from .proxies import _create_proxy_command


def _expand_envvars(text: str) -> str:
    return os.path.expandvars(os.path.expanduser(text))


def _is_help_option(param: click.Option) -> bool:
    """
    Checks whether the given :class:`~click.Option` object is a help option or not.

    Parameters
    ----------
    param
        A click option object.

    Returns
    -------
    bool
        If ``True``, The given :class:`~click.Option` object is a help option.
        else, ``False``.
    """
    has_help_msg_as_help_text = bool(
        get_close_matches(param.help or "", ["Show this message and exit."], cutoff=0.5)
    )

    return (
        param.is_flag
        and not param.expose_value
        and "--help" in param.opts
        and param.is_eager
        and has_help_msg_as_help_text
    )


def is_param_value_incomplete(
    ctx: Context, param: Parameter, check_if_tuple_has_none: bool = True
) -> bool:
    """
    Checks whether the given name of a parameter doesn't recieve it's values completely.

    Parameters
    ----------
    ctx
        :class:`~click.Context` object corresponding to the parameter.

    param
        :class:`~click.Parameter` object to check it's value after parsing it.

    check_if_tuple_has_none
        Flag that checks whether the given parameter stores multiple
        values in a tuple, and the tuple has `None` in it.

    Returns
    -------
    bool
        Whether the given parameter has recieved all of
        it's necessary values from the prompt or not.
    """
    if param.name is None:
        return False

    if param.nargs == -1:
        return True

    value = ctx.params.get(param.name, None)

    check_if_tuple_has_none = (
        param.multiple or param.nargs != 1
    ) and check_if_tuple_has_none

    return (
        value in (None, ())
        or check_if_tuple_has_none
        and isinstance(value, tuple)
        and None in value
    )

    # return value in (None, ()) or (
    #     check_if_tuple_has_none and isinstance(value, tuple) and None in value
    # )


def _get_group_ctx(ctx: Context) -> Context:
    """
    Checks and returns the appropriate :class:`~click.Context` object to
    start repl on it.

    If there's a parent context object and its command type is :class:`~click.Group`,
    we return its parent context object. A parent context object should be
    available most of the time. If not, then we return the original context object.

    Parameters
    ----------
    ctx
        The :class:`~click.Context` object to check and start repl on it.

    Returns
    -------
    click.Context
        The :class:`~click.Context` object that should be used to start repl on it.
    """
    if ctx.parent is not None and not isinstance(ctx.command, Group):
        ctx = ctx.parent

    ctx.protected_args = []
    return ctx


@lru_cache(maxsize=128)
def get_info_dict(
    obj: Context | Command | Parameter | click.ParamType,
) -> InfoDict:
    """
    Similar to the ``get_info_dict`` method implementation in click objects,
    but it only retrieves the essential attributes required to
    differentiate between different ``ReplParsingState`` objects.

    Parameters
    ----------
    obj
        Click object for which the info dict needs to be generated.

    Returns
    -------
    InfoDict
        Dictionary that holds crucial details about the given click object
        that can be used to uniquely identify it.

    References
    ----------
    | .. [1] :meth:`click.Context.get_info_dict <click.Context.get_info_dict>`
    | :meth:`click.Command.get_info_dict <click.Command.get_info_dict>`
    | :meth:`click.Group.get_info_dict <click.Group.get_info_dict>`
    | :meth:`click.Parameter.get_info_dict <click.Parameter.get_info_dict>`
    | :meth:`click.Option.get_info_dict <click.Option.get_info_dict>`
    | :meth:`click.ParamType.get_info_dict <click.ParamType.get_info_dict>`
    | :meth:`click.Choice.get_info_dict <click.Choice.get_info_dict>`
    | :meth:`click.DateTime.get_info_dict <click.DateTime.get_info_dict>`
    | :meth:`click.File.get_info_dict <click.File.get_info_dict>`
    | :meth:`click.Path.get_info_dict <click.Path.get_info_dict>`
    | :meth:`click.Tuple.get_info_dict <click.Tuple.get_info_dict>`
    | :meth:`click.IntRange.get_info_dict <click.IntRange.get_info_dict>`
    | :meth:`click.FloatRange.get_info_dict <click.FloatRange.get_info_dict>`
    | :meth:`click.types.FuncParamType.get_info_dict <click.types.FuncParamType.get_info_dict>`
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

        if isinstance(obj, (Group, click.CommandCollection)):
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

        elif isinstance(obj, RANGE_TYPES):
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
    group: Group,
    parent_ctx: Context,
    args: tuple[str, ...],
    proxy: bool = False,
    **ctx_kwargs: dict[str, Any],
) -> tuple[Context, Command | None]:
    if not args:
        return parent_ctx, None

    # Since the resolve_command method only accepts string arguments in a
    # list format, we explicitly convert args into a list.
    _args = list(_expand_envvars(i) for i in args)

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
        with _create_proxy_command(cmd) as _cmd:
            ctx = _cmd.make_context(name, _args, parent=parent_ctx, **ctx_kwargs)

    else:
        ctx = cmd.make_context(name, _args, parent=parent_ctx, **ctx_kwargs)

    return ctx, cmd


@lru_cache(maxsize=3)
def _resolve_context(ctx: Context, args: tuple[str, ...], proxy: bool = False) -> Context:
    while args:
        command = ctx.command

        if isinstance(command, Group):
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


@lru_cache(maxsize=3)
def _resolve_state(
    ctx: Context, document_text: str
) -> tuple[Context, ReplParsingState, Incomplete]:
    """
    Resolves the parsing state of the arguments in the REPL prompt.

    Parameters
    ----------
    ctx
        The current :class:`click.Context` object of the parent group.

    document_text
        Text that's currently entered in the prompt.

    Returns
    -------
    tuple[Context,ReplParsingState,Incomplete]
        Returns the appropriate `click.Context` constructed from parsing
        the given input from prompt, current :class:`click_repl.parser.ReplParsingState`
        object, and the :class:`click_repl.parser.Incomplete` object that holds the
        incomplete data that requires suggestions.
    """
    args, incomplete = _resolve_incomplete(document_text)
    parsed_ctx = _resolve_context(ctx, args, proxy=True)
    state = _resolve_repl_parsing_state(ctx, parsed_ctx, args)

    return parsed_ctx, state, incomplete
