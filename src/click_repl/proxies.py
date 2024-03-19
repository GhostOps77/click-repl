"""
`click_repl.proxies`

Proxy objects to modify the parsing method of click objects.
"""

from __future__ import annotations

import typing as t
from typing import Any

import click
from click import Argument
from click import Command
from click import CommandCollection
from click import Context
from click import Group
from click import MultiCommand
from click import Option
from click import Parameter
from typing_extensions import Self

from ._globals import HAS_CLICK_GE_8
from .parser import ReplOptionParser

T = t.TypeVar("T")


@t.overload
def _create_proxy_command(obj: Group) -> ProxyGroup: ...


@t.overload
def _create_proxy_command(obj: Command) -> ProxyCommand:  # type:ignore[misc]
    ...


def _create_proxy_command(obj: Command | Group) -> ProxyCommand | ProxyGroup:
    if isinstance(obj, Group):
        return ProxyGroup(obj)
    return ProxyCommand(obj)


@t.overload
def _create_proxy_param(obj: Parameter) -> Parameter: ...


@t.overload
def _create_proxy_param(obj: Option) -> ProxyOption:  # type:ignore[misc]
    ...


@t.overload
def _create_proxy_param(obj: Argument) -> ProxyArgument:  # type:ignore[misc]
    ...


def _create_proxy_param(obj: Parameter) -> Parameter:
    if isinstance(obj, Option):
        return ProxyOption(obj)

    elif isinstance(obj, Argument):
        return ProxyArgument(obj)

    return ProxyParameter(obj)


class Proxy:
    """
    An abstract generic proxy class that delegates attribute access
    to the underlying object.

    This class provides a simple mechanism to proxy attribute access to another object.
    It allows accessing attributes, setting attributes, and deleting attributes on the
    underlying object.

    Parameters
    ----------
    obj : Any
        Object to which attribute access is delegated.

    Notes
    -----
    This class is used as a base class for creating proxy objects that customize
    attribute access behavior.
    """

    def __init__(self, obj: T) -> None:
        self.proxy_setattr("_obj", obj)

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to the underlying object."""
        return getattr(self.get_obj(), name)

    def __setattr__(self, name: str, value: Any) -> None:
        """Delegate attribute assignment to the underlying object."""
        setattr(self.get_obj(), name, value)

    def __delattr__(self, name: str) -> None:
        """Delegate attribute assignment to the underlying object."""
        delattr(self.get_obj(), name)

    def revoke_changes(self) -> None:
        """
        Revoke any changes made to the underlying object.

        Raises
        ------
        NotImplementedError
            This method is meant to be overridden by subclasses.
        """
        raise NotImplementedError()

    def get_obj(self) -> Any:
        """
        Gets the underlying object.

        Returns
        -------
        The underlying object to which attribute access is delegated.
        """
        return self.proxy_getattr("_obj")

    def proxy_getattr(self, name: str) -> Any:
        """
        Proxy attribute access for internal use.

        Parameters
        ----------
        name : str
            The name of the attribute to access.

        Returns
        -------
        The value of the accessed attribute.
        """
        return object.__getattribute__(self, name)

    def proxy_setattr(self, name: str, value: Any) -> None:
        """
        Proxy attribute assignment for internal use.

        Parameters
        ----------
        name : str
            The name of the attribute to assign.

        value : Any
            The value to assign to the attribute.
        """
        object.__setattr__(self, name, value)

    def proxy_delattr(self, name: str) -> None:
        """
        Proxy attribute deletion for internal use.

        Parameters
        ----------
        name : str
            The name of the attribute to delete.
        """
        object.__delattr__(self, name)


class ProxyCommand(Proxy, Command):
    """
    A proxy class for `click.Command` objects to modify their
    options parser, by overriding its `make_parser` method to
    use the custom parser implementation provided by
    `click_repl.parser.ReplOptionParser`.

    Parameters
    ----------
    obj : `click.Command`
        The click command object that has to be proxied.
    """

    def __init__(self, obj: Command) -> None:
        # Changing the Parameter types to their proxies.
        super().__init__(obj)
        self.params = [_create_proxy_param(param) for param in obj.params]

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: Any) -> None:
        self.revoke_changes()

    def revoke_changes(self) -> None:
        self.params = [
            param.get_obj() if isinstance(param, ProxyParameter) else param
            for param in self.params
        ]

    def make_parser(self, ctx: Context) -> ReplOptionParser:
        return ReplOptionParser(ctx)


class ProxyMultiCommand(ProxyCommand, MultiCommand):
    """
    A proxy class for `click.MultiCommand` objects that changes its parser to
    `click_repl.parser.ReplOptionParser` in the `make_parser` method.

    Parameters
    ----------
    obj : `click.MultiCommand`
        The click multicommand object that has to be proxied.
    """

    def __init__(self, obj: MultiCommand) -> None:
        super().__init__(obj)
        self.proxy_setattr(
            "_no_args_is_help_bkp", self.no_args_is_help  # type:ignore[has-type]
        )
        self.no_args_is_help = False

    def revoke_changes(self) -> None:
        super().revoke_changes()
        self.no_args_is_help = self.proxy_getattr("_no_args_is_help_bkp")


class ProxyGroup(ProxyMultiCommand, Group):
    pass


class ProxyCommandCollection(ProxyMultiCommand, CommandCollection):
    pass


class ProxyParameter(Proxy, Parameter):
    """
    A generic proxy class for `click.Parameter` objects that modifies
    its behavior for missing values.

    This class overrides the `process_value` method to return missing
    values as they are, even if they are incomplete or not provided.

    Parameters
    ----------
    obj : `click.Parameter`
        The click parameter object that has to be proxied.
    """

    def full_process_value(self, ctx: Context, value: Any) -> Any:
        # click v7 has 'full_process_value' instead of 'process_value'.
        # Therefore, for backwards compatibility with click v7,
        # 'process_value' method is called within this method.
        return self.process_value(ctx, value)

    def consume_value(
        self, ctx: Context, opts: t.Mapping[str, t.Any]
    ) -> tuple[t.Any, click.core.ParameterSource] | t.Any:

        value = opts.get(self.name, None)  # type:ignore[arg-type]

        if HAS_CLICK_GE_8:
            from click.core import ParameterSource

            return value, ParameterSource.COMMANDLINE

        return value

    def process_value(self, ctx: Context, value: Any) -> Any:
        if value is not None:
            value = self.type_cast_value(ctx, value)

        if self.callback is not None:
            value = self.callback(ctx, self, value)

        return value


class ProxyArgument(ProxyParameter, Argument):
    """
    A proxy class for `click.Argument` objects, allowing modification of their behavior
    during the processing of values based on their type.

    Parameters
    ----------
    obj : `click.Argument`
        The click argument object that has to be proxied.
    """

    pass


class ProxyOption(ProxyParameter, Option):
    """
    A proxy class for `click.Option` objects, allowing modification of their behavior
    during the processing of values based on their type.

    Parameters
    ----------
    obj : `click.Option`
        The click option object that has to be proxied.
    """

    def prompt_for_value(self, ctx: Context) -> Any:
        return

    # pass
