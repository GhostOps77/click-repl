__all__ = [
    "InternalCommandException",
    "ExitReplException",
    "ClickExit",
]


import typing as t
from click.exceptions import Exit as ClickExit


class InternalCommandException(Exception):
    """
    Base Class for all Exceptions raised by the
    `click_repl._internal_cmds.InternalCommandSystem`.

    This class is used to replace errors raised inside the
    `click_repl._internal_cmds.InternalCommandSystem`
    class in order to display their error messages separately
    in the REPL.
    """

    pass


class WrongType(InternalCommandException):
    """
    Exception raised when an object with an invalid type is passed to one of
    the methods in `click_repl._internal_cmds.InternalCommandSystem`.

    Parameters
    ----------
    var : Any
        The variable that has wrong/unexpected type.
    var_name : str
        The name of the variable passed through the `var` parameter.
    expected_type : str
        A string that describes the expected type.
    """

    def __init__(self, var: "t.Any", var_name: str, expected_type: str) -> None:
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
        super().__init__(
            f"Both internal_command_prefix and system_command_prefix can't have "
            f"the same Prefix string {prefix_str}."
        )


class ExitReplException(InternalCommandException):
    """Exception raised to exit the click_repl app."""

    pass


class InvalidGroupFormat(Exception):
    """
    Exception raised when a Group has nonrequired arguments don't have
    value assigned to them.

    This exception indicates an invalid format in a Group context object
    where nonrequired arguments are missing values. It typically occurs
    when attempting to parse command-line input that does not conform
    to the expected format.
    """

    pass
