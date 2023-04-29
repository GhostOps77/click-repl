import click
import typing as t
from ._repl import repl, register_repl

if t.TYPE_CHECKING:
    from typing import Any, Generator  # noqa: F401


__all__ = [
    'repl',
    'register_repl',
    'flatten_click_tuple'
]


def flatten_click_tuple(tuple_type: 'click.Tuple') -> 'Generator[Any, None, None]':
    for val in tuple_type.types:
        if isinstance(val, click.Tuple):
            for item in flatten_click_tuple(val):
                yield item
        else:
            yield val
