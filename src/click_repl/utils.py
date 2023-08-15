"""
`click_repl.utils`

Utilities to facilitate the functionality of the click_repl module.
"""
import os
import typing as t
from functools import lru_cache
from gettext import gettext as _

import click
from click.parser import split_opt

from ._globals import _RANGE_TYPES
from .parser import currently_introspecting_args
from .parser import get_args_and_incomplete_from_args
from .proxies import _create_proxy_command

if t.TYPE_CHECKING:
    from typing import Any, Dict, List, Optional, Tuple, Union, Generator
    from click import Command, Context, Parameter, MultiCommand
    from .parser import ArgsParsingState, Incomplete


def _expand_envvars(text: str) -> str:
    return os.path.expandvars(os.path.expanduser(text))


def _is_help_option(param: "click.Option") -> bool:
    return (
        param.is_flag
        and not param.expose_value
        and param.is_eager
        and param.help == _("Show this message and exit.")
    )


def _print_err(text: str) -> None:
    # Prints the given text to the stderr, in red colour.
    click.secho(text, color=True, err=True, fg="red")


def _is_param_value_incomplete(ctx: "Context", param_name: "Optional[str]") -> bool:
    # Checks whether the given value of the parameter contains `None` values.
    if param_name is None:
        return False

    value = ctx.params.get(param_name, None)  # type: ignore[arg-type]
    return value in (None, ()) or (isinstance(value, tuple) and None in value)


def _join_options(options: "t.List[str]") -> "t.Tuple[t.List[str], str]":
    # Same implementation as ijoin_options functionn click.formatting..
    any_prefix_is_slash = any(split_opt(opt)[0] == "/" for opt in options)
    options.sort(key=len)

    return options, ";" if any_prefix_is_slash else "/"


def _get_group_ctx(ctx: "Context") -> "Context":
    # If there's a parent context object and its command type is click.MultiCommand,
    # we return its parent context object. A parent context object should be
    # available most of the time. If not, then we return the original context object.

    if ctx.parent is not None and not isinstance(ctx.command, click.MultiCommand):
        return ctx.parent

    return ctx


def _get_visible_subcommands(
    ctx: "Context",
    multicommand: "MultiCommand",
    incomplete: str,
    show_hidden_commands: bool = False,
) -> "Generator[Tuple[str, Command], None, None]":
    for command_name in multicommand.list_commands(ctx):
        if not command_name.startswith(incomplete):
            continue

        subcommand = multicommand.get_command(ctx, command_name)

        if subcommand is None or (subcommand.hidden and not show_hidden_commands):
            # We skip the hidden command if self.show_hidden_commands is False,
            # or if there's no command found.
            continue

        yield command_name, subcommand


@lru_cache(maxsize=128)
def get_info_dict(
    obj: "Union[Context, Command, Parameter, click.ParamType]",
) -> "Dict[str, Any]":
    if isinstance(obj, click.Context):
        return {
            "command": get_info_dict(obj.command),
            "params": obj.params,
        }

    info_dict: "Dict[str, Any]" = {}  # type: ignore[no-redef]

    if isinstance(obj, click.Command):
        ctx = click.Context(obj)

        info_dict.update(
            name=obj.name,
            params=tuple(get_info_dict(param) for param in obj.get_params(ctx)),
            callback=obj.callback,
        )

        if isinstance(obj, click.MultiCommand):
            commands = {}

            for name in obj.list_commands(ctx):
                command = obj.get_command(ctx, name)

                if command is None:
                    continue

                commands[name] = get_info_dict(command)

            info_dict.update(commands=commands, chain=obj.chain)

    elif isinstance(obj, click.Parameter):
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

        elif isinstance(obj, _RANGE_TYPES):
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


@lru_cache(maxsize=6)
def _generate_next_click_ctx(
    command: "MultiCommand",
    parent_ctx: "Context",
    args: "Tuple[str, ...]",
    proxy: bool = False,
    **ctx_kwargs: "Dict[str, Any]"
) -> "Tuple[Context, Optional[Command]]":
    # Since the resolve_command method only accepts string arguments in a
    # list format, we explicitly convert _args into a list.

    _args = list(args)
    name, cmd, _args = command.resolve_command(parent_ctx, _args)

    if cmd is None:
        return parent_ctx, None

    if proxy:
        # When using click.parser.OptionParser.parse_args, incomplete
        # string arguments that do not meet the nargs requirement of
        # the current parameter are normally ignored. However, in our
        # case, we want to handle these incomplete arguments. To
        # achieve this, we use a proxy command object to modify
        # the command parsing behavior in click.
        with _create_proxy_command(cmd) as cmd:
            ctx = cmd.make_context(name, _args, parent=parent_ctx, **ctx_kwargs)
    else:
        ctx = cmd.make_context(name, _args, parent=parent_ctx, **ctx_kwargs)

    return ctx, cmd


@lru_cache(maxsize=3)
def _resolve_context(
    ctx: "Context", args: "Tuple[str, ...]", proxy: bool = False
) -> "Tuple[Context, Tuple[str, ...]]":
    while args:
        command = ctx.command

        if isinstance(command, click.MultiCommand):
            if not command.chain:
                ctx, cmd = _generate_next_click_ctx(
                    command,
                    ctx,
                    args,
                    proxy=proxy,
                )

                if cmd is None:
                    return ctx, args

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
                        return ctx, args

                    args = tuple(sub_ctx.args)

                    if args and args[0] == ";":
                        return sub_ctx, args

                ctx = sub_ctx

            args = tuple(ctx.protected_args + ctx.args)

            if args and args[0] == ";":
                return ctx, args

        else:
            break

    return ctx, args


@lru_cache(maxsize=3)
def resolve_context(
    cli_ctx: "Context",
    args: "Tuple[str, ...]",
    proxy: bool = False,
    return_top_level_ctx_only: bool = True,
) -> "List[Context]":
    if not args:
        return [cli_ctx]

    res = []
    ctx = cli_ctx
    tmp_ctx = None

    while args:
        tmp_ctx = None
        if return_top_level_ctx_only:
            _ctx, _ = _generate_next_click_ctx(ctx.command, ctx, args, proxy=proxy)
            res.append(_ctx)

            _args = _ctx.args
            if isinstance(_ctx.command, click.MultiCommand) and not _ctx.command.chain:
                _args = _ctx.protected_args + _args

            ctx, args = _resolve_context(_ctx, tuple(_args), proxy=proxy)
            if args and args[0] == ";":
                args = args[1:]

        else:
            ctx, args = _resolve_context(ctx, args, proxy=proxy)
            res.append(ctx)
            if args and args[0] == ";":
                args = args[1:]
                ctx = cli_ctx

                tmp_ctx = cli_ctx

    if tmp_ctx:
        res.append(cli_ctx)

    # print(f'{res = }')
    return res


@lru_cache(maxsize=3)
def _resolve_state(
    ctx: "Context", document_text: str
) -> "Tuple[Context, ArgsParsingState, Incomplete]":
    # Resolves the parsing state of the arguments in the REPL prompt.
    args, incomplete = get_args_and_incomplete_from_args(document_text)

    parsed_ctx = resolve_context(ctx, args, proxy=True, return_top_level_ctx_only=False)[
        -1
    ]

    state = currently_introspecting_args(ctx, parsed_ctx, args)

    return parsed_ctx, state, incomplete
