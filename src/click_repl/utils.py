import click
import typing as t
from functools import lru_cache

from .parser import currently_introspecting_args

if t.TYPE_CHECKING:
    from typing import List, Tuple  # noqa: F401
    from .parser import ParsingState  # noqa: F401
    from click import Context, Command  # noqa: F401


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


def _resolve_context(args: "List[str]", ctx: "Context") -> "Context":
    """Produce the context hierarchy starting with the command and
    traversing the complete arguments. This only follows the commands,
    it doesn't trigger input prompts or callbacks.

    :param args: List of complete args before the incomplete value.
    :param ctx: `~click.Context` object of the CLI group.
    """

    while args:
        command = ctx.command

        if isinstance(command, click.MultiCommand):
            if not command.chain:
                name, cmd, args = command.resolve_command(ctx, args)

                if cmd is None:
                    return ctx

                ctx = cmd.make_context(name, args, parent=ctx, resilient_parsing=True)
                args = ctx.protected_args + ctx.args
            else:
                while args:
                    name, cmd, args = command.resolve_command(ctx, args)

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
                args = [*sub_ctx.protected_args, *sub_ctx.args]
        else:
            break

    return ctx


@lru_cache(maxsize=3)
def get_parsed_ctx_and_state(
    cli_ctx: "Context", args: "Tuple[str]"
) -> "Tuple[Context, Command, ParsingState]":
    """Used in both completer class and validator class
    to execute once and use the cached result in the other
    """
    parsed_ctx = _resolve_context(list(args), cli_ctx)

    ctx_command = parsed_ctx.command
    state = currently_introspecting_args(
        cli_ctx.command, parsed_ctx, args  # type: ignore[arg-type]
    )

    return parsed_ctx, ctx_command, state
