from __future__ import annotations

import click
import pytest
from prompt_toolkit.document import Document

from click_repl.completer import ClickCompleter
from tests import DummyInternalCommandSystem


@click.group()
def root_command():
    pass


c = ClickCompleter(click.Context(root_command), DummyInternalCommandSystem())


@pytest.mark.skipif(
    int(click.__version__[0]) != 7,
    reason="click-v7 old autocomplete function is not available, so skipped",
)
def test_click7_autocomplete_arg():
    def shell_complete_func(ctx, args, incomplete):
        return [name for name in ("foo", "bar") if name.startswith(incomplete)]

    @root_command.command()
    @click.argument("handler", autocompletion=shell_complete_func)
    def autocompletion_arg_cmd2(handler):
        pass

    completions = c.get_completions(Document("autocompletion-arg-cmd2 "))
    assert {x.text for x in completions} == {"foo", "bar"}
