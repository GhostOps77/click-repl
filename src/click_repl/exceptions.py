"""
Exceptional classes required for the module.
"""

from __future__ import annotations

from typing import Any

import click


class InternalCommandException(Exception):
    """
    Base Class for all exceptions raised by the
    :class:`~click_repl.internal_commands.InternalCommandSystem`.

    This class is used to replace errors raised inside the
    :class:`~click_repl.internal_commands.InternalCommandSystem`
    class in order to display their error messages separately in the REPL.
    """

    pass


class ParserError(Exception):
    """
    Exception raised when parsing given input for click objects fails.
    """

    pass


class InternalCommandNotFound(InternalCommandException):
    """
    Exception raised when the given command name is not an internal command.
    """

    pass


class PrefixNotFound(InternalCommandException):
    """
    Exception raised when the prefix of an internal command is not found while
    attempting to execute a query.
    """

    pass


class WrongType(InternalCommandException):
    """
    Exception raised when an object with an invalid type is passed to one of
    the methods in :class:`~click_repl.internal_commands.InternalCommandSystem`.

    Parameters
    ----------
    var
        The variable that has wrong or unexpected type.

    var_name
        The name of the variable passed through the ``var`` parameter.

    expected_type
        A string that describes the expected type.
    """

    def __init__(self, var: Any, var_name: str, expected_type: str) -> None:
        super().__init__(
            f"Expected {var_name!r} to be a {expected_type}, "
            f"but got {type(var).__name__}"
        )


class SamePrefix(InternalCommandException):
    """
    Exception raised when both
    :attr:`~click_repl.internal_commands.InternalCommandSystem.internal_command_prefix
    and :attr:`~click_repl.internal_commands.InternalCommandSystem.system_command_prefix` in
    :class:`~click_repl.internal_commands.InternalCommandSystem` are assigned as the same
    prefix string.

    Parameters
    ----------
    prefix_str
        The prefix string that is assigned to both
        :attr:`~.internal_commands.InternalCommandSystem.internal_command_prefix`
        and :attr:`~.internal_commands.InternalCommandSystem.system_command_prefix`.
    """

    def __init__(self, prefix_str: str) -> None:
        super().__init__(
            "Both internal_command_prefix and system_command_prefix cannot have "
            f"the same prefix string {prefix_str!r}."
        )


class ExitReplException(InternalCommandException):
    """Exception raised to stop the REPL of the click_repl app."""

    pass


class ArgumentPositionError(ParserError):
    """
    Exception raised when an :class:`~click.Argument` with
    :attr:`~click.Argument.nargs` = -1 is not defined at the rightmost
    end of the parameter list.

    This exception indicates that the given command has an argument with ``nargs=-1``
    defined within the other parameters. However, an argument with ``nargs=-1`` must
    be defined at the end of the parameter list. This is because an argument with
    ``nargs=-1`` consumes all the incoming values as the remaining values from the REPL
    prompt, and any other parameter defined after it will not receive any value.

    Parameters
    ----------
    command
        The click command object that contains the argument.

    argument
        The click argument object that violates the position rule.

    position
        The index of the disarranged ``nargs=-1`` argument in the parameter list of
        the given command.
    """

    def __init__(
        self, command: click.Command, argument: click.Argument, position: int
    ) -> None:
        super().__init__(
            f"The argument {argument.name!r} with nargs=-1, in command "
            f"{command.name!r} must be defined at the end of the parameter list, "
            f"but found at position {position}"
        )
