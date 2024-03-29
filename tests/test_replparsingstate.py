from __future__ import annotations

import click
import pytest

from click_repl.utils import _resolve_state


@click.group()
def main():
    pass


@main.command()
@click.argument("arg", type=click.IntRange(max=100))
@click.argument("choice-arg", type=click.Choice(["1", "2", "3"]))
@click.argument(expose_value=False)  # None as parameter name
@click.option("-f", "--file-opt", type=click.File())
@click.option("-p", "--path-opt", type=click.Path())
@click.option(
    "-t",
    "--tuple-opt",
    type=click.Tuple([click.types.FuncParamType(int), click.DateTime()]),
)
def cmd():
    pass


ctx = click.Context(main)


@pytest.mark.parametrize(
    "test_input",
    [
        "cmd 98 ",
        "cmd 98 3 ",
        "cmd 98 3 hi ",
        "cmd 98 3 hi --file-opt=",
        "cmd 98 3 hi --file-opt=.click-repl-err.log ",
        "cmd 98 3 hi --file-opt=.click-repl-err.log -p ",
        "cmd 98 3 hi --file-opt=.click-repl-err.log -p /some/random/path/ --tuple-opt ",
    ],
)
def test_state_objs_with_same_values_have_same_hashes(test_input):
    _, state1, _ = _resolve_state(ctx, test_input)
    _resolve_state.cache_clear()

    _, state2, _ = _resolve_state(ctx, test_input)

    assert state1 == state2


def test_state_objs_with_different_values_have_different_hashes():
    _, state1, _ = _resolve_state(
        ctx,
        "cmd 98 3 --file-opt .click-repl-err.log "
        "--path-opt /some/random/path/ "
        "--tuple-opt 10087967 2023-12-25 ",
    )
    _resolve_state.cache_clear()

    _, state2, _ = _resolve_state(ctx, "cmd 98 3 --file-opt .click-repl-err.log ")

    assert state1 != state2
