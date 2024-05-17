"""
Module for handling compatibility issues with different versions of Click.
"""

from __future__ import annotations

from typing import Union

import click
from typing_extensions import TypeAlias

from .globals_ import IS_CLICK_GE_8_2

RANGE_TYPES: TypeAlias = Union[click.IntRange, click.FloatRange]

RANGE_TYPES_TUPLE = (click.IntRange, click.FloatRange)
"""Same thing as :obj:`~click_repl._compat.RANGE_TYPES`, but this is used for :py:func:`isinstance` checks."""

PARAM_TYPES_WITH_METAVAR: TypeAlias = Union[click.Choice, click.DateTime]
""":class:`~click.types.ParamType` classes with
   :meth:`~click.types.ParamType.get_metavar` method defined.
"""

PATH_TYPES: TypeAlias = Union[click.Path, click.File]
""":class:`~click.types.ParamType` classes that expect path values."""

PATH_TYPES_TUPLE = (click.Path, click.File)
"""Same thing as :obj:`~click_repl._compat.PATH_TYPES`, but this is used for :py:func:`isinstance` checks."""


# Several things are deprecated in click v8.2
# Therefore, we're importing them based on their new name.
if IS_CLICK_GE_8_2:
    from click.core import _MultiCommand as MultiCommand  # type:ignore
    from click.parser import _Argument  # type:ignore
    from click.parser import _Option  # type:ignore
    from click.parser import _normalize_opt as normalize_opt  # type:ignore
    from click.parser import _OptionParser as OptionParser  # type:ignore
    from click.parser import _ParsingState as ParsingState  # type:ignore
    from click.parser import _split_opt as split_opt  # type:ignore
    from click.shell_completion import split_arg_string  # type:ignore

else:
    from click.core import MultiCommand  # type:ignore
    from click.parser import Argument as _Argument  # type:ignore
    from click.parser import Option as _Option  # type:ignore
    from click.parser import (
        OptionParser,
        ParsingState,
        normalize_opt,
        split_arg_string,
        split_opt,
    )

    RANGE_TYPES = click.types._NumberRangeBase  # type:ignore
    RANGE_TYPES_TUPLE = (click.types._NumberRangeBase,)  # type:ignore


__all__ = [
    "MultiCommand",
    "RANGE_TYPES",
    "RANGE_TYPES_TUPLE",
    "PARAM_TYPES_WITH_METAVAR",
    "PATH_TYPES",
    "PATH_TYPES_TUPLE",
    "OptionParser",
    "ParsingState",
    "_Argument",
    "_Option",
    "normalize_opt",
    "split_opt",
    "split_arg_string",
]
