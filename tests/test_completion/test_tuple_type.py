from __future__ import annotations

from pathlib import Path

import click
import pytest
from prompt_toolkit.document import Document

from click_repl.completer import ClickCompleter
from tests import DummyInternalCommandSystem


@click.group()
def main():
    pass


@main.command()
@click.option(
    "-t",
    "--tuple-opt",
    type=click.Tuple([click.types.FuncParamType(int), click.File(), click.Path()]),
)
def tuple_arg_cmd():
    pass


ctx = click.Context(main)

c = ClickCompleter(ctx, DummyInternalCommandSystem(), show_only_unused_opts=True)

current_dir_list = {str(p) for p in Path().iterdir()}


@pytest.mark.parametrize(
    "test_input, expected",
    [
        ("tuple-arg-cmd --tuple-opt ", set()),
        ("tuple-arg-cmd --tuple-opt 123 ", current_dir_list),
        ("tuple-arg-cmd --tuple-opt 123 .click-repl-err.log ", current_dir_list),
        ("tuple-arg-cmd --tuple-opt 123 .click-repl-err.log /some/path/ ", set()),
    ],
)
def test_tuple_type(test_input, expected):
    completions = c.get_completions(Document(test_input))
    assert {i.text for i in completions} == expected
