from __future__ import annotations

import click
import pytest

from click_repl.parser import _resolve_state


@click.group()
def root_command():
    pass


ctx = click.Context(root_command)


@root_command.command()
@click.argument("arg", nargs=5, type=int)
def nargs_more_than_one_cmd(arg):
    pass


@pytest.mark.parametrize(
    "test_input, current_param, expected_val",
    [
        ("nargs-more-than-one-cmd ", "arg", None),
        ("nargs-more-than-one-cmd 1 ", "arg", (1,)),
        ("nargs-more-than-one-cmd 1 2 3 ", "arg", (1, 2, 3)),
        ("nargs-more-than-one-cmd 1 2 3 4 5 ", None, (1, 2, 3, 4, 5)),
    ],
)
def test_nargs_more_than_one_auto_completion(test_input, current_param, expected_val):
    current_ctx, state, _ = _resolve_state(ctx, test_input)

    _current_param = state.current_param

    if _current_param is None and current_param is None:
        current_ctx.params["arg"] == expected_val
        return

    assert state.current_param.name == current_param

    if state.current_param.name == "arg":
        current_ctx.params["arg"] == expected_val


@root_command.command()
@click.option("-o", "--opt")
def option_cmd(opt):
    pass


@pytest.mark.parametrize("test_input", ["option-cmd -a ", "option-cmd --hi "])
def test_unknown_option_names(test_input):
    with pytest.raises(click.NoSuchOption):
        _resolve_state(ctx, test_input)
