"""
Provdies objects that's declared specifically
for every click version with breaking changes.
"""

from __future__ import annotations

from typing import Union

import click
from typing_extensions import TypeAlias

from .globals_ import HAS_CLICK_GE_8, HAS_CLICK_GE_8_2

RANGE_TYPES: TypeAlias = Union[click.IntRange, click.FloatRange]
"""Range types that are used as a :class:`~click.Parameter`'s type in :mod:`~click`.

   :class:`~click.types._NumberRangeBase` class is defined in click v8.
   Therefore, this tuple is used to check for the
   range type :class:`~click.types.ParamType` objects.
"""

RANGE_TYPES_TUPLE = (click.IntRange, click.FloatRange)
"""Same thing, but this is used for :py:func:`isinstance` checks."""

PARAM_TYPES_WITH_METAVAR: TypeAlias = Union[click.Choice, click.DateTime]
"""The only :class:`~click.types.ParamType` classes that have their
   :meth:`~click.types.ParamType.get_metavar` method's functionality defined."""

PATH_TYPES: TypeAlias = Union[click.Path, click.File]
""":class:`~click.types.ParamType` classes that expect path as values."""

PATH_TYPES_TUPLE = (click.Path, click.File)
"""Same thing, but this is used for :py:func:`isinstance` checks."""

AUTO_COMPLETION_FUNC_ATTR = (
    "_custom_shell_complete" if HAS_CLICK_GE_8 else "autocompletion"
)
"""The attribute name of the custom autocompletion function for a
   :class:`~click.Parameter` is different in ``click <= 7`` and ``click >= 8``.
"""

# Several things are deprecated in click v8.2
# Therefore, we're importing them based on their new name.
if HAS_CLICK_GE_8_2:
    from click.core import Group as MultiCommand  # type:ignore
    from click.parser import _Argument  # type:ignore
    from click.parser import _Option  # type:ignore
    from click.parser import _normalize_opt as normalize_opt  # type:ignore
    from click.parser import _OptionParser as OptionParser  # type:ignore
    from click.parser import _ParsingState as ParsingState  # type:ignore
    from click.parser import _split_opt as split_opt  # type:ignore
    from click.shell_completion import split_arg_string

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

    if HAS_CLICK_GE_8:
        RANGE_TYPES = click.types._NumberRangeBase  # type:ignore
        RANGE_TYPES_TUPLE = (click.types._NumberRangeBase,)  # type:ignore


__all__ = [
    "RANGE_TYPES",
    "RANGE_TYPES_TUPLE",
    "PARAM_TYPES_WITH_METAVAR",
    "PATH_TYPES",
    "PATH_TYPES_TUPLE",
    "AUTO_COMPLETION_FUNC_ATTR",
    "MultiCommand",
    "OptionParser",
    "ParsingState",
    "_Argument",
    "_Option",
    "normalize_opt",
    "split_opt",
    "split_arg_string",
]
