import typing as t
from functools import lru_cache

import click
from click.parser import split_opt

from .parser import currently_introspecting_args
from .parser import CustomOptionsParser
from .parser import get_args_and_incomplete_from_args

if t.TYPE_CHECKING:
    from typing import List, Tuple
    from click import Command, Context
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
