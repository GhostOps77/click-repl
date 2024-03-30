"""
Exceptional classes required for the module.
"""

from __future__ import annotations

from typing import Any

from click import Argument, Command
from click.exceptions import Exit as ClickExit

__all__ = [
    "InternalCommandException",
    "ExitReplException",
    "ClickExit",
]


class InternalCommandException(Exception):
    """
    Base Class for all Exceptions raised by the
    :class:`~click_repl._internal_cmds.InternalCommandSystem`.

    This class is used to replace errors raised inside the
    :class:`~click_repl._internal_cmds.InternalCommandSystem`
    class in order to display their error messages separately in the REPL.
    """

    pass


class ParserError(Exception):
    """
    Exceptions that are raised when parsing given input of click objects.
    """

    pass


class PrefixNotFound(InternalCommandException):
    """
    Exception raised when the Internal Command's prefix is not found while
    trying to execute a query.
    """

    pass


class WrongType(InternalCommandException):
    """
    Exception raised when an object with an invalid type is passed to one of
    the methods in :class:`~click_repl._internal_cmds.InternalCommandSystem`.

    Parameters
    ----------
    var : Any
        The variable that has wrong/unexpected type.

    var_name : str
        The name of the variable passed through the `var` parameter.

    expected_type : str
        A string that describes the expected type.
    """

    def __init__(self, var: Any, var_name: str, expected_type: str) -> None:
        super().__init__(
            f"Expected '{var_name}' to be a {expected_type}, "
            f"but got {type(var).__name__}"
        )


class SamePrefix(InternalCommandException):
    """
    Exception raised when `click_repl._internal_cmds.InternalCommandSystem`
    assigns both `internal_command_prefix` and `system_command_prefix` as the same
    prefix string.

    Parameters
    ----------
    prefix_str : str
        The prefix string that is assigned to both `internal_command_prefix`
        and `system_command_prefix`.
    """

    def __init__(self, prefix_str: str) -> None:
        super().__init__(
            "Both internal_command_prefix and system_command_prefix can't have "
            f"the same Prefix string {prefix_str}."
        )


class ExitReplException(InternalCommandException):
    """Exception raised to stop the REPL of the click_repl app."""

    pass


class ArgumentPositionError(ParserError):
    """
    Exception raised when an argument with `nargs=-1` is not defined at the rightmost
    end of the parameter list.

    This exception indicates that the given command has an argument with `nargs=-1`
    defined within the other parameters. However, an argument with `nargs=-1` must
    be defined at the end of the parameter list. This is because an argument with
    `nargs=-1` consumes all the incoming values as the remaining values from the REPL
    prompt, and any other parameter defined after it will not receive any value.

    Parameters
    ----------
    command : click.Command
        The click command object that contains the argument.

    argument : click.Argument
        The click argument object that violates the position rule.

    position : int
        The index of the disarranged nargs=-1 argument in the parameter list of
        the given command.
    """

    def __init__(self, command: Command, argument: Argument, position: int) -> None:
        super().__init__(
            f"The argument '{argument.name}' with nargs=-1, in command "
            f"'{command.name}' must be defined at the end of the parameter list, "
            f"but found at position {position}"
        )
