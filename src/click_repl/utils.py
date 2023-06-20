import click
import typing as t

from .parser import currently_introspecting_args, CustomOptionsParser

if t.TYPE_CHECKING:
    from typing import List, Tuple  # noqa: F401
    from .parser import ArgsParsingState  # noqa: F401
    from click import Context, Command  # noqa: F401

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


class Proxy(object):
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


def _resolve_context(ctx: "Context", args: "List[str]") -> "Context":
    """Produce the context hierarchy starting with the command and
    traversing the complete arguments. This only follows the commands,
    it doesn't trigger input prompts or callbacks.

    :param ctx: `~click.Context` object of the CLI group.
    :param args: List of complete args before the incomplete value.
    """

    ctx.resilient_parsing = True
    ctx.allow_extra_args = True

    while args:
        command = ctx.command

        if isinstance(command, click.MultiCommand):
            if not command.chain:
                name, cmd, args = ProxyCommand(command).resolve_command(ctx, args)

                if cmd is None:
                    return ctx

                ctx = cmd.make_context(name, args, parent=ctx, resilient_parsing=True)
                args = ctx.protected_args + ctx.args
            else:
                while args:
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


def get_parsed_ctx_and_state(
    cli_ctx: "Context", args: "List[str]"
) -> "Tuple[Context, Command, ArgsParsingState]":
    """Used in both completer class and validator class
    to execute once and use the cached result in the other
    """
    parsed_ctx = _resolve_context(cli_ctx, args)

    ctx_command = parsed_ctx.command
    state = currently_introspecting_args(
        cli_ctx.command, parsed_ctx, args  # type: ignore[arg-type]
    )

    return parsed_ctx, ctx_command, state
