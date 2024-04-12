from __future__ import annotations

import click

from ._compat import split_opt


def print_error(text: str) -> None:
    """Prints the given text to stderr, in red colour."""
    click.secho(text, color=True, err=True, fg="red")


def get_option_flag_sep(option_names: list[str]) -> str:
    any_prefix_is_slash = any(split_opt(opt)[0] == "/" for opt in option_names)
    return ";" if any_prefix_is_slash else "/"


def join_options(options: list[str]) -> tuple[list[str], str]:
    """
    Same implementation as :meth:`~click.formatting.join_options`, but much simpler.

    Parameters
    ----------
    options
        List of option flags that needs to be joined together.

    References
    ----------
    :meth:`~click.formatting.join_options`
    """
    return sorted(options, key=len), get_option_flag_sep(options)
