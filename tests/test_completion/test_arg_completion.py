from __future__ import annotations

import click
import pytest
from click.shell_completion import CompletionItem
from prompt_toolkit.completion import Completion
from prompt_toolkit.document import Document

from click_repl.completer import ClickCompleter
from tests import DummyInternalCommandSystem


@click.group()
def root_command():
    pass


@root_command.command()
@click.argument("foo", type=click.BOOL)
def bool_arg(foo):
    pass


@root_command.command()
@click.argument("handler", type=click.Choice(("foo", "bar")))
def arg_choices(handler):
    pass


@root_command.command()
@click.argument("handler", type=click.Choice(("foo", "bar"), case_sensitive=False))
def arg_choices_case_insensitive(handler):
    pass


c = ClickCompleter(click.Context(root_command), DummyInternalCommandSystem())


@pytest.mark.parametrize(
    "test_input, expected",
    [
        ("bool-arg ", {"true", "false"}),
        ("bool-arg t", {"true"}),
        ("bool-arg true ", set()),
    ],
)
def test_boolean_arg(test_input, expected):
    completions = c.get_completions(Document(test_input))
    assert {x.text for x in completions} == expected


@pytest.mark.parametrize(
    "test_input, expected",
    [
        ("arg-choices ", {"foo", "bar"}),
        ("arg-choices f", {"foo"}),
        ("arg-choices foo ", set()),
    ],
)
def test_arg_choices(test_input, expected):
    completions = c.get_completions(Document(test_input))
    assert {x.text for x in completions} == expected


@pytest.mark.parametrize(
    "test_input, expected",
    [
        ("arg-choices-case-insensitive ", {"foo", "bar"}),
        ("arg-choices-case-insensitive F", {"foo"}),
        ("arg-choices-case-insensitive fO", {"foo"}),
        ("arg-choices-case-insensitive B", {"bar"}),
        ("arg-choices-case-insensitive Bar ", set()),
    ],
)
def test_arg_choices_case_insensitive(test_input, expected):
    completions = c.get_completions(Document(test_input))
    assert {x.text for x in completions} == expected


def test_shell_complete_arg_class_type():
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


def test_shell_complete_arg_func_completionitem_return_type():
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


def test_shell_complete_arg_func_completion_return_type():
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
