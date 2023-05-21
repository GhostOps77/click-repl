import click
import typing as t

if t.TYPE_CHECKING:
    from typing import List  # noqa: F401

    from click import Context  # noqa: F401


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


def _resolve_context(
    args: "List[str]",
    ctx: "Context",
) -> "Context":
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
