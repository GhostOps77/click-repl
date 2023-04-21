import click
from click_repl import ClickCompleter
from prompt_toolkit.document import Document
import pytest


@click.group()
def root_command():
    pass


c = ClickCompleter(root_command, click.Context(root_command))


@pytest.mark.skipif(
    int(click.__version__[0]) > 7,
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


def return_type_tuple_shell_complete(ctx, args, incomplete):
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


@pytest.mark.skipif(
    int(click.__version__[0]) > 7,
    reason="click-v7 old autocomplete function is not available, so skipped",
)
@pytest.mark.parametrize("test_input, expected", [
    ("tuple-type-autocompletion-cmd ", {"Hi", "Please", "Hey", "Aye"}),
    ("tuple-type-autocompletion-cmd h", {"Hi", "Hey"})
])
def test_tuple_return_type_shell_complete_func_click7(test_input, expected):
    @root_command.command()
    @click.argument("foo", autocompletion=return_type_tuple_shell_complete)
    def tuple_type_autocompletion_cmd(foo):
      pass

    completions = c.get_completions(Document(test_input))
    assert {x.text for x in completions} == expected
