import typing as t
from functools import lru_cache

import click
from click.parser import split_opt

from ._globals import _RANGE_TYPES, HAS_CLICK8
from .parser import (CustomOptionsParser, currently_introspecting_args,
                     get_args_and_incomplete_from_args)

if t.TYPE_CHECKING:
    from typing import Any, Dict, List, Tuple, Union

    from click import Command, Context, Parameter

    from .parser import ArgsParsingState

    V = t.TypeVar("V")


# def flatten_click_tuple(tuple_type: "click.Tuple") -> "Generator[Any, None, None]":
#     """Unpacks types provided through :class:`~click.Tuple` into a single list

#     Keyword arguments:
#     :param `tuple_type`: :class:`~click.Tuple` type that has collection
#         of other types
#     Yield: Each type inside the Tuple
#     """

#     for val in tuple_type.types:
#         if isinstance(val, click.Tuple):
#             for item in flatten_click_tuple(val):
#                 yield item
#         else:
#             yield val


def join_options(
    options: "t.List[str]",
) -> "t.Tuple[t.List[str], str]":
    """
    Given a list of option strings this joins them in the most appropriate
    way and returns them in the form `(formatted_string,
    any_prefix_is_slash)` where the second item in the tuple is a flag that
    indicates if any of the option prefixes was a slash.
    """
    any_prefix_is_slash = False

    for opt in options:
        prefix = split_opt(opt)[0]
        if prefix == "/":
            any_prefix_is_slash = True

    options.sort(key=len)
    return options, ";" if any_prefix_is_slash else "/"


def get_group_ctx(group_ctx: "Context") -> "Context":
    # parent should be available, but we're not going to bother if not
    if group_ctx.parent is not None and not isinstance(
        group_ctx.command, click.MultiCommand
    ):
        group_ctx = group_ctx.parent

    return group_ctx


class Proxy:
    def __init__(self, obj: "V") -> None:
        object.__setattr__(self, "_obj", obj)

    def __getattr__(self, name: str) -> "t.Any":
        return getattr(object.__getattribute__(self, "_obj"), name)

    def __setattr__(self, name: str, value: "t.Any") -> None:
        setattr(object.__getattribute__(self, "_obj"), name, value)

    def __delattr__(self, name: str) -> None:
        delattr(object.__getattribute__(self, "_obj"), name)


class ProxyCommand(Proxy, click.Command):
    """A Proxy class for :class:`~click.Command` class
    that changes its parser class to the click_repl's
    :class:`~CustomOptionParser` class
    """

    def make_parser(self, ctx: "Context") -> "CustomOptionsParser":
        return CustomOptionsParser(ctx)


# class ProxyGroup(click.Group):
#     def make_parser(self, ctx: "Context") -> "CustomOptionsParser":
#         return CustomOptionsParser(ctx)

# class ProxyCommandCollection(click.CommandCollection):
#     def make_parser(self, ctx: "Context") -> "CustomOptionsParser":
#         return CustomOptionsParser(ctx)


# def ProxyMultiCommand(obj):
#     # cls = type(obj)
#     attrs = vars(obj)
#     _result_callback = attrs.pop("_result_callback", None)
#     attrs.pop('__doc__', None)
#     print(f'{attrs = }')

#     if isinstance(obj, click.Group):
#         res = ProxyGroup(**attrs)

#     elif isinstance(obj, click.CommandCollection):
#         res = ProxyCommandCollection(**attrs)

#     res._result_callback = _result_callback
#     return res


def _resolve_context(ctx: "Context", args: "List[str]") -> "Context":
    """Produce the context hierarchy starting with the command and
    traversing the complete arguments. This only follows the commands,
    it doesn't trigger input prompts or callbacks.

    :param ctx: `~click.Context` object of the CLI group.
    :param args: List of complete args before the incomplete value.
    """

    # ctx.resilient_parsing = True

    # cli = ctx.command
    # ctx = cli.make_context("", args.copy(), resilient_parsing=True)
    # args = ctx.protected_args + ctx.args

    while args:
        command = ctx.command

        if isinstance(command, click.MultiCommand):
            if not command.chain:
                # print(f'from multicommand {vars(command)}')
                name, cmd, args = ProxyCommand(command).resolve_command(ctx, args)

                if cmd is None:
                    return ctx

                ctx = cmd.make_context(name, args, parent=ctx, resilient_parsing=True)
                args = ctx.protected_args + ctx.args
            else:
                while args:
                    # print(f'from command {vars(command)}')
                    name, cmd, args = ProxyCommand(command).resolve_command(ctx, args)

                    if cmd is None:
                        return ctx

                    sub_ctx = cmd.make_context(
                        name,
                        args,
                        parent=ctx,
                        allow_extra_args=True,
                        allow_interspersed_args=False,
                        resilient_parsing=True,
                    )
                    args = sub_ctx.args

                ctx = sub_ctx
                args = sub_ctx.protected_args + sub_ctx.args
        else:
            break

    return ctx


def get_info_dict(
    obj: "Union[Context, Command, Parameter, click.ParamType]",
) -> "Dict[str, Any]":
    if isinstance(obj, click.Command):
        ctx = click.Context(obj)

    if HAS_CLICK8:
        if isinstance(obj, click.Command):
            return obj.to_info_dict(ctx)  # type: ignore[no-any-return]

        return obj.to_info_dict()  # type: ignore[no-any-return]

    info_dict: "Dict[str, Any]" = {}

    if isinstance(obj, click.Context):
        return {
            "command": get_info_dict(obj.command),
            "info_name": obj.info_name,
            "allow_extra_args": obj.allow_extra_args,
            "allow_interspersed_args": obj.allow_interspersed_args,
            "ignore_unknown_options": obj.ignore_unknown_options,
            "auto_envvar_prefix": obj.auto_envvar_prefix,
        }

    if isinstance(obj, click.Command):
        info_dict.update(
            name=obj.name,
            params=[get_info_dict(param) for param in obj.get_params(ctx)],
            help=obj.help,
            epilog=obj.epilog,
            short_help=obj.short_help,
            hidden=obj.hidden,
            deprecated=obj.deprecated,
        )

        if isinstance(obj, click.MultiCommand):
            commands = {}

            for name in obj.list_commands(ctx):
                command = obj.get_command(ctx, name)

                if command is None:
                    continue

                # sub_ctx = ctx._make_sub_context(command)

                # with sub_ctx.scope(cleanup=False):
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
            default=obj.default,
            envvar=obj.envvar,
        )

        if isinstance(obj, click.Option):
            info_dict.update(
                help=obj.help,
                prompt=obj.prompt,
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
            info_dict["case_sensitive"] = getattr(obj, "case_sensitive", True)

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
            info_dict["types"] = [get_info_dict(t) for t in obj.types]

    return info_dict


@lru_cache(maxsize=3)
def _resolve_state(
    cli_ctx: "Context", document: str
) -> "Tuple[Context, Command, ArgsParsingState, Tuple[str, ...], str]":
    """Used in both completer class and validator class
    to execute once and use the cached result in the other
    """

    args, incomplete = get_args_and_incomplete_from_args(document)
    parsed_ctx = _resolve_context(cli_ctx, list(args))

    ctx_command = parsed_ctx.command
    state = currently_introspecting_args(cli_ctx, parsed_ctx, args)

    return parsed_ctx, ctx_command, state, args, incomplete
