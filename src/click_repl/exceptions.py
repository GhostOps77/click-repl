import typing as t

from click.exceptions import Exit as ClickExit

if t.TYPE_CHECKING:
    from click import Argument, Command, Group


__all__ = [
    "InternalCommandException",
    "ExitReplException",
    "ClickExit",
]


class InternalCommandException(Exception):
    """
    Base Class for all Exceptions raised by the
    `click_repl._internal_cmds.InternalCommandSystem`.

    This class is used to replace errors raised inside the
    `click_repl._internal_cmds.InternalCommandSystem`
    class in order to display their error messages separately
    in the REPL.
    """


class ParserError(Exception):
    """
    Exceptions that are raised when parsing given input of click objects.
    """


class WrongType(InternalCommandException):
    """
    Exception raised when an object with an invalid type is passed to one of
    the methods in `click_repl._internal_cmds.InternalCommandSystem`.
    """

    def __init__(self, var: "t.Any", var_name: str, expected_type: str) -> None:
        """
        Initializes the `WrongType` class.

        Parameters
        ----------
        var : Any
            The variable that has wrong/unexpected type.
        var_name : str
            The name of the variable passed through the `var` parameter.
        expected_type : str
            A string that describes the expected type.
        """
        super().__init__(
            f"Expected '{var_name}' to be a {expected_type}, "
            f"but got {type(var).__name__}"
        )


class SamePrefixError(InternalCommandException):
    """
    Exception raised when `click_repl._internal_cmds.InternalCommandSystem`
    assigns both `internal_command_prefix` and `system_command_prefix` as the same
    prefix string.
    """

    def __init__(self, prefix_str: str) -> None:
        """
        Initialize a SamePrefixError exception.

        Parameters
        ----------
        prefix_str : str
            The prefix string that is assigned to both `internal_command_prefix`
            and `system_command_prefix`.
        """
        super().__init__(
            "Both internal_command_prefix and system_command_prefix can't have "
            f"the same Prefix string {prefix_str}."
        )


class ExitReplException(InternalCommandException):
    """Exception raised to exit the click_repl app."""


class InvalidGroupFormat(ParserError):
    """
    Exception raised when a Group has non-required arguments don't have
    value assigned to them.

    This exception indicates an invalid format in a Group context object
    where nonrequired arguments are missing values. It typically occurs
    when attempting to parse command-line input that does not conform
    to the expected format.
    """

    def __init__(self, group: "Group", param: "Argument") -> None:
        """
        Initialize the `InvalidGroupFormat` exception.

        Parameters
        ----------
        group : click.Group
            The group object representing the group that has the invalid format.

        param : click.Argument
            The argument object representing the non-required argument
            that is missing a value.
        """

        super().__init__(
            f'Expected some value for the optional argument "{param.name}" of '
            f'Group "{group.name}" to invoke the REPL, but got None'
        )


class ArgumentPositionError(ParserError):
    """
    Exception raised when an argument with `nargs=-1` is not defined at the end
    of the parameter list.

    This exception indicates that the given command has an argument with `nargs=-1`
    defined within the other parameters. However, an argument with `nargs=-1` must
    be defined at the end of the parameter list. This is because an argument with
    `nargs=-1` consumes all the incoming values as the remaining values from the REPL
    prompt, and any other parameter defined after it will not receive any value.
    """

    def __init__(self, command: "Command", argument: "Argument") -> None:
        """
        Initialize the `ArgumentPositionError`.

        Parameters
        ----------
        command : click.Command
            The command object that contains the argument.

        argument : click.Argument
            The argument object that violates the position rule.
        """

        super().__init__(
            f"The argument '{argument.name}' with nargs=-1, in command "
            f"'{command.name}' must be defined at the end of the parameter list."
        )
