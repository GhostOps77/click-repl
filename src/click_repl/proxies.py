"""
`click_repl.proxies`

Proxy objects to modify the parsing method of click objects.
"""
import typing as t

import click

from .parser import ReplOptionParser

if t.TYPE_CHECKING:
    from typing import Any
    from click import Command, Context, Parameter, Group

    V = t.TypeVar("V")


def _create_proxy_command(obj: "Command") -> "ProxyCommand":
    if isinstance(obj, click.Group):
        return ProxyGroup(obj)
    return ProxyCommand(obj)


def _create_proxy_param(obj: "Parameter") -> "ProxyParameter":
    if isinstance(obj, click.Option):
        return ProxyOption(obj)
    return ProxyArgument(obj)


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
        object.__setattr__(self, "_obj", obj)

    def __getattr__(self, name: str) -> "Any":
        """Delegate attribute access to the underlying object."""
        return getattr(object.__getattribute__(self, "_obj"), name)

    def __setattr__(self, name: str, value: "Any") -> None:
        """Delegate attribute assignment to the underlying object."""
        setattr(object.__getattribute__(self, "_obj"), name, value)

    def __delattr__(self, name: str) -> None:
        """Delegate attribute assignment to the underlying object."""
        delattr(object.__getattribute__(self, "_obj"), name)

    def revoke_changes(self) -> None:
        raise NotImplementedError()

    def get_obj(self) -> "Any":
        return self.proxy_getattr("_obj")

    def proxy_getattr(self, name: str) -> "Any":
        return object.__getattribute__(self, name)

    def proxy_setattr(self, name: str, value: "Any") -> "Any":
        return object.__setattr__(self, name, value)

    def proxy_delattr(self, name: str) -> "Any":
        return object.__delattr__(self, name)


class ProxyCommand(Proxy, click.Command):
    """
    A proxy class for `click.Command` objects to modify their
    options parser, by overriding its `make_parser` method to
    use the custom parser implementation provided by
    `click_repl.parser.ReplOptionParser`.

    Parameters
    ----------
    obj : click.Command
        The `click.Command` object to be proxied.
    """

    def __init__(self, obj: "Command") -> None:
        # Changing the Parameter types to their proxies.
        super().__init__(obj)
        self.params = [_create_proxy_param(param) for param in obj.params]

    def __enter__(self) -> "t.Self":
        return self

    def __exit__(self, *args: "Any") -> None:
        self.revoke_changes()

    def revoke_changes(self) -> None:
        self.params = [
            param.get_obj() for param in self.params  # type: ignore[attr-defined]
        ]

    def make_parser(self, ctx: "Context") -> "ReplOptionParser":
        return ReplOptionParser(ctx)


class ProxyGroup(ProxyCommand, click.Group):
    """
    A proxy class for `click.Group` objects that changes its parser to
    `click_repl.parser.ReplOptionParser` in the `make_parser` method.
    """

    def __init__(self, obj: "Group") -> None:
        super().__init__(obj)
        object.__setattr__(
            self, "_no_args_is_help", self.no_args_is_help  # type: ignore[has-type]
        )
        self.no_args_is_help = False

    def revoke_changes(self) -> None:
        super().revoke_changes()
        self.no_args_is_help = object.__getattribute__(self, "_no_args_is_help")


class ProxyParameter(Proxy, click.Parameter):
    """
    A generic proxy class for `click.Parameter` objects that modifies
    its behavior for missing values.

    This class overrides the `process_value` method to return missing
    values as they are, even if they are incomplete or not provided.
    """

    def full_process_value(self, ctx: "Context", value: "t.Any") -> "t.Any":
        # click v7 has 'full_process_value' instead of 'process_value'.
        # Therefore, for backwards compatibility with click v7,
        # 'process_value' method is called within this method.
        return self.process_value(ctx, value)

    def process_value(self, ctx: "Context", value: "t.Any") -> "t.Any":
        if value is not None:
            value = self.type_cast_value(ctx, value)

        if self.callback is not None:
            value = self.callback(ctx, self, value)

        return value


class ProxyArgument(ProxyParameter, click.Argument):
    """
    A proxy class for `click.Argument` objects, allowing modification of their behavior
    during the processing of values based on their type.
    """

    pass


class ProxyOption(ProxyParameter, click.Option):
    """
    A proxy class for `click.Option` objects, allowing modification of their behavior
    during the processing of values based on their type.
    """

    pass
