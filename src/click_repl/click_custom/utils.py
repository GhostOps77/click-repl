from __future__ import annotations

from click import FloatRange, IntRange

from ..globals_ import IS_CLICK_GE_8


def _describe_click_range_param_type(param_type: IntRange | FloatRange) -> str:
    """
    Returns the metavar of the range-type :class:`~click.types.ParamType` type objects.

    Parameter
    ---------
    param_type
        :class:`~click.types.ParamType` object, whose metavar should be generated.

    Returns
    -------
    str
        Metavar that describes about the given range-like
        :class:`~click.types.ParamType` object.
    """

    if IS_CLICK_GE_8:
        res = param_type._describe_range()

    elif param_type.min is None:
        res = f"x<={param_type.max}"

    elif param_type.max is None:
        res = f"x>={param_type.min}"

    else:
        res = f"{param_type.min}<=x<={param_type.max}"

    clamp = " clamped" if param_type.clamp else ""
    return res + clamp  # type:ignore[no-any-return]
