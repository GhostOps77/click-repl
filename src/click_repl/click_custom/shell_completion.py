from __future__ import annotations

import os
import re
from functools import lru_cache
from glob import glob
from typing import Any, Iterable

from click import Command, Context, Group

from ..proxies import _create_proxy_command


def _expand_args(args: Iterable[str]) -> list[str]:
    out = []

    for arg in args:
        arg = os.path.expandvars(os.path.expanduser(arg))

        try:
            matches = glob(arg, recursive=True)
        except re.error:
            matches = []

        if not matches:
            out.append(arg)
        else:
            out.extend(matches)

    return out


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


    Reference
    ---------
    :func:`~click.shell_completion._resolve_context`
    """
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
