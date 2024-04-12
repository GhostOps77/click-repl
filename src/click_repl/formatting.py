from __future__ import annotations

import click


def print_error(text: str) -> None:
    """Prints the given text to stderr, in red colour."""
    click.secho(text, color=True, err=True, fg="red")
