"""
Proxy objects to modify the parsing method of click objects.
"""

from __future__ import annotations

import typing as t
from typing import Any

import click
from click import Argument, Command, Context, Group, Option, Parameter
from typing_extensions import Self

from .click_custom.parser import ReplOptionParser
from .globals_ import IS_CLICK_GE_8

T = t.TypeVar("T")


@t.overload
def _create_proxy_command(obj: Command) -> ProxyCommand: ...


@t.overload
def _create_proxy_command(obj: Group) -> ProxyGroup:  # type:ignore[misc]
    ...


def _create_proxy_command(obj: Command | Group) -> ProxyCommand | ProxyGroup:
    """
    Wraps the given :class:`~click.Command` object within a proxy object.

    Parameters
    ----------
    obj
        Command object that needs to be wrapped in a proxy object.

    Returns
    -------
    ProxyCommand
        Proxy wrapper for the :class:`~click.Command` objects.
    """
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


def _create_proxy_param(obj: Parameter) -> ProxyParameter:
    """
    Wraps the given :class:`~click.Parameter` object within a proxy object.

    Parameters
    ----------
    obj
        Parameter object that needs to be wrapped in a proxy object.

    Returns
    -------
    ProxyParameter
        Proxy wrapper for the :class:`~click.Parameter` objects.
    """
    if isinstance(obj, Option):
        return ProxyOption(obj)

    elif isinstance(obj, Argument):
        return ProxyArgument(obj)

    return ProxyParameter(obj)


class Proxy:
    """
    Base class for creating proxy objects that customize
    attribute access behavior.

    Parameters
    ----------
    obj
        Object to which attribute access is delegated.
    """

    def __init__(self, obj: T) -> None:
        """
        Initializes a `Proxy` object.
        """
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
        Any
            The underlying object to which attribute access is delegated.
        """
        return self.proxy_getattr("_obj")

    def proxy_getattr(self, name: str) -> Any:
        """
        Proxy attribute access for internal use.

        Parameters
        ----------
        name
            The name of the attribute to access.

        Returns
        -------
        Any
            The value of the accessed attribute.
        """
        return object.__getattribute__(self, name)

    def proxy_setattr(self, name: str, value: Any) -> None:
        """
        Proxy attribute assignment for internal use.

        Parameters
        ----------
        name
            The name of the attribute to assign.

        value
            The value to assign to the attribute.
        """
        object.__setattr__(self, name, value)

    def proxy_delattr(self, name: str) -> None:
        """
        Proxy attribute deletion for internal use.

        Parameters
        ----------
        name
            The name of the attribute to delete.
        """
        object.__delattr__(self, name)


class ProxyCommand(Proxy, Command):
    """
    Proxy class for :class:`~click.Command` objects that modifies their options parser.

    This class overrides the :meth:`~click.Command.make_parser` method to use the custom
    parser implementation provided by :class:`~click_repl.click_custom.parser.ReplOptionParser`.

    Parameters
    ----------
    obj
        The :class:`~click.Command` object that needs to be proxied.
    """

    def __init__(self, obj: Command) -> None:
        """
        Initializes a `ProxyCommand` object.
        """
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


class ProxyGroup(ProxyCommand, Group):
    """
    Proxy class for :class:`~click.Group` objects that modifies their options parser.

    This class overrides the :meth:`~click.Group.make_parser` method to use the custom
    parser implementation provided by :class:`~click_repl.click_custom.parser.ReplOptionParser`.

    Parameters
    ----------
    obj
        The :class:`~click.Group` object that needs to be proxied.
    """

    def __init__(self, obj: Group) -> None:
        """
        Initialize the `ProxyGroup` class.
        """
        super().__init__(obj)
        self.proxy_setattr(
            "_no_args_is_help_bkp", self.no_args_is_help  # type:ignore[has-type]
        )
        self.no_args_is_help = False

    def revoke_changes(self) -> None:
        super().revoke_changes()
        self.no_args_is_help = self.proxy_getattr("_no_args_is_help_bkp")


class ProxyParameter(Proxy, Parameter):
    """
    A generic proxy class for :class:`~click.Parameter` objects that
    modifies it's behavior for missing values.

    This class overrides the :meth:`~click.Parameter.process_value` method to
    return missing values as they are, even if they are incomplete or not provided.

    Parameters
    ----------
    obj
        The :class:`click.Parameter` object that needs to be proxied.
    """

    def __init__(self, obj: Parameter) -> None:
        """
        Initializes the `ProxyParameter` class.
        """
        super().__init__(obj)

    def full_process_value(self, ctx: Context, value: Any) -> Any:
        # click v7 has 'full_process_value' while click v8 has 'process_value'.
        # Therefore, for backwards compatibility with click v7,
        # 'process_value' method is called within this method.
        return self.process_value(ctx, value)

    def consume_value(
        self, ctx: Context, opts: t.Mapping[str, t.Any]
    ) -> tuple[t.Any, click.core.ParameterSource] | t.Any:

        value = opts.get(self.name, None)  # type:ignore[arg-type]

        if IS_CLICK_GE_8:
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
    Proxy class for :class:`~click.Argument` objects, allowing modification
    of their behavior during the processing of values based on their type.

    Parameters
    ----------
    obj
        The :class:`~click.Argument` object that needs to be proxied.
    """

    def __init__(self, obj: Argument) -> None:
        """
        Initiailizes the `ProxyArgument` class.
        """
        super().__init__(obj)


class ProxyOption(ProxyParameter, Option):
    """
    Proxy class for :class:`~click.Option` objects, allowing modification
    of their behavior during the processing of values based on their type.

    Parameters
    ----------
    obj
        The :class:`click.Option` object that needs to be proxied.
    """

    def __init__(self, obj: Option) -> None:
        """
        Initiailizes the `ProxyOption` class.
        """
        super().__init__(obj)

    def prompt_for_value(self, ctx: Context) -> Any:
        return
