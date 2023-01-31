import click
import pytest

from click_repl import ClickCompleter
from tests import TestDocument


@click.group()
def root_command():
    pass


c = ClickCompleter(click.Context(root_command))

with pytest.importorskip(
    "click.shell_complete.CompletionItem",
    minversion="8.0.0",
    reason="click-v8 built-in shell complete is not available, so skipped",
) as CompletionItem:

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
        def autocompletion_arg_cmd(handler):
            pass

        completions = c.get_completions(TestDocument("autocompletion-cmd "))
        assert {x.text for x in completions} == {"foo", "bar"}


with pytest.importorskip(
    "click.shell_complete.CompletionItem",
    minversion="8.0.0",
    reason="click-v8 built-in shell complete is not available, so skipped",
) as CompletionItem:

    def test_shell_complete_arg_v8_func_type():
        def shell_complete_func(ctx, param, incomplete):
            return [
                CompletionItem(name)
                for name in ("foo", "bar")
                if name.startswith(incomplete)
            ]

        @root_command.command()
        @click.argument("handler", shell_complete=shell_complete_func)
        def autocompletion_cmd2(handler):
            pass

        completions = c.get_completions(TestDocument("autocompletion-cmd2 "))
        assert {x.text for x in completions} == {"foo", "bar"}


def return_type_tuple_shell_complete(ctx, param, incomplete):
    return [
        i
        for i in [
            ("Hi", "hi"),
            ("Please", "please"),
            ("Hey", "hey"),
            ("Aye", "aye"),
        ]
        if i[1].startswith(incomplete)
    ]


with pytest.importorskip(
    "click.shell_complete.CompletionItem",
    minversion="8.0.0",
    reason="click-v8 built-in shell complete is not available, so skipped",
):

    @root_command.command()
    @click.argument("foo", shell_complete=return_type_tuple_shell_complete)
    def tuple_type_autocompletion_cmd(foo):
        pass

    @pytest.mark.parameterize(
        "test_input, expected",
        [
            ("tuple-type-autocompletion-cmd ", {"Hi", "Please", "Hey", "Aye"}),
            ("tuple-type-autocompletion-cmd h", {"Hi", "Hey"}),
        ],
    )
    def test_tuple_return_type_shell_complete_func(test_input, expected):
        completions = list(c.get_completions(TestDocument(test_input)))
        assert {x.text for x in completions} == expected and {
            x.display_meta[0][-1] for x in completions
        } == {i.lower() for i in expected}


@root_command.command()
@click.argument("choice", type=click.Choice(("FOO", "Bar"), case_sensitive=False))
def case_insensitive_choices(choice):
    pass


@pytest.mark.skipif(
    click.__version__[0] != "8",
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
    completions = c.get_completions(TestDocument(test_input))
    assert {x.text for x in completions} == expected
