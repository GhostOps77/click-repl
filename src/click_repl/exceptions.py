__all__ = [
    "InternalCommandException",
    "ExitReplException",
    "InvalidGroupFormat",
    "ClickExit",
]


class InternalCommandException(Exception):
    pass


class ExitReplException(InternalCommandException):
    pass


class InvalidGroupFormat(Exception):
    pass


# Handle click.exceptions.Exit introduced in Click 7.0
try:
    from click.exceptions import Exit as ClickExit
except ImportError:
    from click.exceptions import Abort as ClickExit  # type: ignore[assignment]
