import click
import typing as t

if t.TYPE_CHECKING:
    from typing import Any, Generator  # noqa: F401


def flatten_click_tuple(tuple_type: 'click.Tuple') -> 'Generator[Any, None, None]':
    for val in tuple_type.types:
        if isinstance(val, click.Tuple):
            for item in flatten_click_tuple(val):
                yield item
        else:
            yield val
