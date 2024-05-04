from __future__ import annotations

import os
import re
from functools import lru_cache
from glob import glob
from typing import Any, Iterable

from click import Command, Context, Group

from ..proxies import create_proxy_command


def _expand_args(args: Iterable[str]) -> list[str]:
    """
    Expands Environmental variables in the text in given ``args``.

    Parameter
    ---------
    args
        List of strings received and parsed from the prompt.

    Returns
    -------
    list[str]
        List of strings with expanded environmental variables.
    """
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
    parent_ctx: Context,
    args: tuple[str, ...],
    proxy: bool = False,
    **ctx_kwargs: dict[str, Any],
) -> tuple[Context, Command | None]:
    """
    Generates the next :class:`~click.Context` object with the given set of
    ``args`` and ``parent_ctx``.

    Parameters
    ----------
    parent_ctx
        The click context object of the parent group.

    args
        List of arguments for the parent group from the REPL prompt.

    proxy
        Determines whether to use :class:`~click_repl.proxies.ProxyCommand`
        class to parse the ``args``.

    **ctx_kwargs
        Extra keyword arguments for :meth:`~click.Command.make_context` method.

    Returns
    -------
    tuple[Context,Command | None]
        A tuple containing:
            - Next click context object, parsed from the ``args``
            - Command of this next context object if exists, else :obj:`None`.
    """

    if not args:
        return parent_ctx, None

    group: Group = parent_ctx.command  # type:ignore[assignment]

    name, cmd, args = group.resolve_command(parent_ctx, args)  # type:ignore

    if cmd is None:
        return parent_ctx, None

    _args = list(args)

    if proxy:
        # When using click.parser.OptionParser.parse_args, incomplete
        # string arguments that do not meet the nargs requirement of
        # the current parameter are normally ignored. However, in our
        # case, we want to handle these incomplete arguments. To
        # achieve this, we use a proxy command object to modify
        # the command parsing behavior in click.
        with create_proxy_command(cmd) as _command:
            ctx = _command.make_context(name, _args, parent=parent_ctx, **ctx_kwargs)

    else:
        ctx = cmd.make_context(name, _args, parent=parent_ctx, **ctx_kwargs)

    return ctx, cmd


@lru_cache(maxsize=3)
def _resolve_context(ctx: Context, args: tuple[str, ...], proxy: bool = True) -> Context:
    """
    Parses the ``args`` into latest click context. Customized to use
    :class:`~click_repl.proxies.ProxyCommand` class to parse the ``args``.

    Parameters
    ----------
    ctx
        The click context object of the parent group.

    args
        List of arguments for the parent group from the REPL prompt.

    proxy
        Determines whether to use :class:`~click_repl.proxies.ProxyCommand`
        class to parse the ``args``.

    Returns
    -------
    click.Context
        Context object for the latest command the user has requested in
        the prompt, along with its parameters parsed along with it.

    Reference
    ---------
    :func:`~click.shell_completion._resolve_context`
    """

    while args:
        command = ctx.command

        if isinstance(command, Group):
            if not command.chain:
                ctx, cmd = _generate_next_click_ctx(ctx, args, proxy=proxy)

                if cmd is None:
                    return ctx

            else:
                while args:
                    sub_ctx, cmd = _generate_next_click_ctx(
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
