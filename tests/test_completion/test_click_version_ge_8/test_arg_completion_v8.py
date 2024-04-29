from __future__ import annotations

import click
import pytest
from prompt_toolkit.completion import Completion
from prompt_toolkit.document import Document

from click_repl.completer import ClickCompleter
from click_repl.globals_ import IS_CLICK_GE_8
from tests import DummyInternalCommandSystem

if IS_CLICK_GE_8:
    from click.shell_completion import CompletionItem


@click.group()
def root_command():
    pass


c = ClickCompleter(click.Context(root_command), DummyInternalCommandSystem())

# with pytest.importorskip(
#     "click.shell_complete.CompletionItem",
#     minversion="8.0.0",
#     reason="click-v8 built-in shell complete is not available, so skipped",
# ) as CompletionItem:


@pytest.mark.skipif(
    not IS_CLICK_GE_8,
    reason="click-v8 shell complete function is not available, so skipped",
)
def test_shell_complete_arg_v8_class_type():
    class MyVar(click.ParamType):
        name = "myvar"

        def shell_complete(self, ctx, param, incomplete):
            return [
                CompletionItem(name)
                for name in ("foo", "bar")
                if name.startswith(incomplete)
            ]

    @root_command.command()
    @click.argument("handler", type=MyVar())
    def autocompletion_cmd(handler):
        pass

    completions = c.get_completions(Document("autocompletion-cmd "))
    assert {x.text for x in completions} == {"foo", "bar"}


@pytest.mark.skipif(
    not IS_CLICK_GE_8,
    reason="click-v8 shell complete function is not available, so skipped",
)
def test_shell_complete_arg_v8_func_completionitem_return_type():
    def shell_complete_func(ctx, param, incomplete):
        return [
            CompletionItem(name) for name in ("foo", "bar") if name.startswith(incomplete)
        ]

    @root_command.command()
    @click.argument("handler", shell_complete=shell_complete_func)
    def autocompletion_cmd2(handler):
        pass

    completions = c.get_completions(Document("autocompletion-cmd2 "))
    assert {x.text for x in completions} == {"foo", "bar"}


@pytest.mark.skipif(
    not IS_CLICK_GE_8,
    reason="click-v8 shell complete function is not available, so skipped",
)
def test_shell_complete_arg_v8_func_completion_return_type():
    def shell_complete_func(ctx, param, incomplete):
        return [
            Completion(name) for name in ("foo", "bar") if name.startswith(incomplete)
        ]

    @root_command.command()
    @click.argument("handler", shell_complete=shell_complete_func)
    def autocompletion_cmd2(handler):
        pass

    completions = c.get_completions(Document("autocompletion-cmd2 "))
    assert {x.text for x in completions} == {"foo", "bar"}


@root_command.command()
@click.argument("choice", type=click.Choice(("FOO", "Bar"), case_sensitive=False))
def case_insensitive_choices(choice):
    pass


@pytest.mark.skipif(
    not IS_CLICK_GE_8,
    reason="""Test skipped as click v8 is not available
case_sensitive attribute is introduced in click.Choice in click v8""",
)
@pytest.mark.parametrize(
    "test_input, expected",
    [
        ("case-insensitive-choices ", {"FOO", "Bar"}),
        ("case-insensitive-choices f", {"FOO"}),
        ("case-insensitive-choices bA", {"Bar"}),
    ],
)
def test_case_insensitive_choice_type(test_input, expected):
    completions = c.get_completions(Document(test_input))
    assert {x.text for x in completions} == expected
