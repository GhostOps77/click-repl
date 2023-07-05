import typing as t
from gettext import ngettext

import click
from click.core import iter_params_for_processing

from .parser import CustomOptionsParser


if t.TYPE_CHECKING:
    from typing import List, NoReturn, Union
    from click import Command, Context, Group

    V = t.TypeVar("V")


def create_proxy_object(
    obj: "Union[Command, Group]",
) -> "Union[ProxyCommand, ProxyGroup]":
    """
    Provides the appropriate proxy object based on the given click object.

    Parameters
    ----------
    obj : click.Command or click.Group.
       A `click.Command` or `click.Group` object for which a proxy needs to be created.

    Returns
    -------
    ProxyCommand
        if the given object is an instance of `click.Command` class.

    ProxyGroup
        if the given object is an instance of `click.Group` class.
    """

    if isinstance(obj, click.Group):
        return ProxyGroup(obj)
    return ProxyCommand(obj)


def parse_args(
    cmd: "Union[ProxyCommand, ProxyGroup]", ctx: "Context", args: "List[str]"
) -> "Union[List[str], NoReturn]":
    # if not args and cmd.no_args_is_help and not ctx.resilient_parsing:
    #     click.echo(ctx.get_help(), color=ctx.color)
    #     ctx.exit()

    parser = CustomOptionsParser(ctx)
    opts, args, param_order = parser.parse_args(args=args)

    for param in iter_params_for_processing(param_order, cmd.get_params(ctx)):
        value, args = ProxyParameter(param).handle_parse_result(ctx, opts, args)

    if args and not ctx.allow_extra_args and not ctx.resilient_parsing:
        ctx.fail(
            ngettext(
                "Got unexpected extra argument ({args})",
                "Got unexpected extra arguments ({args})",
                len(args),
            ).format(args=" ".join(args))
        )

    ctx.args = args
    ctx._opt_prefixes.update(parser._opt_prefixes)
    return args


class Proxy:
    """
    A generic proxy class that delegates attribute access to the underlying object.

    This class provides a simple mechanism to proxy attribute access to another object.
    It allows accessing attributes, setting attributes, and deleting attributes on the
    underlying object.

    Parameters
    ----------
    obj
        The object to which attribute access is delegated.

    Notes
    -----
    This class is used as a base class for creating proxy objects that customize
    attribute access behavior.
    """

    def __init__(self, obj: "V") -> None:
        """Initialize the Proxy object with the underlying object."""
        object.__setattr__(self, "_obj", obj)

    def __getattr__(self, name: str) -> "t.Any":
        """Delegate attribute access to the underlying object."""
        return getattr(object.__getattribute__(self, "_obj"), name)

    def __setattr__(self, name: str, value: "t.Any") -> None:
        """Delegate attribute assignment to the underlying object."""
        setattr(object.__getattribute__(self, "_obj"), name, value)

    def __delattr__(self, name: str) -> None:
        """Delegate attribute assignment to the underlying object."""
        delattr(object.__getattribute__(self, "_obj"), name)


class ProxyCommand(Proxy, click.Command):
    """
    A proxy class for `click.Command` class that changes its parser to
    `click_repl.parser.CustomOptionParser` in the `parse_args` method.

    This class overrides the `parse_args` method to use the custom
    parser implementation provided by `click_repl.parser.CustomOptionParser`.
    """

    def parse_args(self, ctx: "Context", args: "List[str]") -> "List[str]":
        return parse_args(self, ctx, args)


class ProxyGroup(Proxy, click.Group):
    """
    A proxy class for `click.Group` that changes its parser to
    `click_repl.parser.CustomOptionParser` in the `parse_args` method.

    This class overrides the `parse_args` method to use the custom parser
    implementation provided by `click_repl.parser.CustomOptionParser`.
    """

    def parse_args(self, ctx: "Context", args: "List[str]") -> "List[str]":
        rest = parse_args(self, ctx, args)

        if self.chain:
            ctx.protected_args = rest
            ctx.args = []
        elif rest:
            ctx.protected_args, ctx.args = rest[:1], rest[1:]

        return ctx.args  # type: ignore[no-any-return]


class ProxyParameter(Proxy, click.Parameter):
    """
    A proxy class for `click.Parameter` that modifies its behavior
    for missing values.

    This class overrides the `process_value` method to return missing
    values as they are, even if they are incomplete or not provided.
    """

    def process_value(self, ctx: "Context", value: "t.Any") -> "t.Any":
        value = self.type_cast_value(ctx, value)

        # if self.required and self.value_is_missing(value):
        #     raise MissingParameter(ctx=ctx, param=self)

        if self.callback is not None:
            value = self.callback(ctx, self, value)

        return value
