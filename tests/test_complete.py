import click
from click_repl import ClickCompleter
from prompt_toolkit.document import Document
import pytest


@click.group()
def root_command():
    pass


c = ClickCompleter(root_command)


def test_shell_complete_arg_v8_class_type():
    with pytest.importorskip(
        "click.shell_complete.CompletionItem",
        minversion="8.0.0",
        reason="click-v8 built-in shell complete is not available, so skipped",
    ) as CompletionItem:

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

        completions = list(c.get_completions(Document("autocompletion-cmd ")))
        assert {x.text for x in completions} == {"foo", "bar"}


def test_shell_complete_option_v8_class_type():
    with pytest.importorskip(
        "click.shell_complete.CompletionItem",
        minversion="8.0.0",
        reason="click-v8 built-in shell complete is not available, so skipped",
    ) as CompletionItem:

        class MyVar(click.ParamType):
            name = "myvar"

            def shell_complete(self, ctx, param, incomplete):
                return [
                    CompletionItem(name)
                    for name in ("foo", "bar")
                    if name.startswith(incomplete)
                ]

        @root_command.command()
        @click.option("--handler", "-h", type=MyVar())
        def autocompletion_opt_cmd(handler):
            pass

        completions = list(c.get_completions(Document("autocompletion-opt-cmd ")))
        assert {x.text for x in completions} == {"--handler", "bar"}


def test_shell_complete_arg_v8_func_type():
    with pytest.importorskip(
        "click.shell_complete.CompletionItem",
        minversion="8.0.0",
        reason="click-v8 built-in shell complete is not available, so skipped",
    ) as CompletionItem:

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

        completions = list(c.get_completions(Document("autocompletion-cmd2 ")))
        assert {x.text for x in completions} == {"foo", "bar"}


def test_shell_complete_option_v8_func_type():
    with pytest.importorskip(
        "click.shell_complete.CompletionItem",
        minversion="8.0.0",
        reason="click-v8 built-in shell complete is not available, so skipped",
    ):

        def shell_complete_func(ctx, param, incomplete):
            return [name for name in ("foo", "bar") if name.startswith(incomplete)]

        @root_command.command()
        @click.option("--handler", shell_complete=shell_complete_func)
        def autocompletion_opt_cmd(handler):
            pass

        completions = list(
            c.get_completions(Document("autocompletion-opt-cmd --handler "))
        )
        assert {x.text for x in completions} == {"foo", "bar"}


@pytest.mark.skipif(
    click.__version__[0] > '7',
    reason="click-v7 old autocomplete function is not available, so skipped",
)
def test_click7_autocomplete_arg():
    def shell_complete_func(ctx, args, incomplete):
        return [name for name in ("foo", "bar") if name.startswith(incomplete)]

    @root_command.command()
    @click.argument("handler", autocompletion=shell_complete_func)
    def autocompletion_arg_cmd2(handler):
        pass

    completions = list(c.get_completions(Document("autocompletion-arg-cmd2 ")))
    assert {x.text for x in completions} == {"foo", "bar"}


@pytest.mark.skipif(
    click.__version__[0] > '7',
    reason="click-v7 old autocomplete function is not available, so skipped",
)
def test_click7_autocomplete_option():
    def shell_complete_func(ctx, args, incomplete):
        return [name for name in ("foo", "bar") if name.startswith(incomplete)]

    @root_command.command()
    @click.option("--handler", autocompletion=shell_complete_func)
    def autocompletion_opt_cmd2(handler):
        pass

    completions = list(
        c.get_completions(Document("autocompletion-opt-cmd2 --handler "))
    )
    assert {x.text for x in completions} == {"foo", "bar"}


def test_arg_choices():
    @root_command.command()
    @click.argument("handler", type=click.Choice(("foo", "bar")))
    def arg_choices(handler):
        pass

    completions = list(c.get_completions(Document("arg-choices ")))
    assert {x.text for x in completions} == {"foo", "bar"}


def test_option_choices():
    @root_command.command()
    @click.option("--handler", type=click.Choice(("foo", "bar")))
    def option_choices(handler):
        pass

    completions = list(c.get_completions(Document("option-choices --handler ")))
    assert {x.text for x in completions} == {"foo", "bar"}


def test_hidden_command_completions():
    @root_command.command(hidden=True)
    @click.option("--handler", type=click.Choice(("foo", "bar")))
    def option_choices_hidden_cmd(handler):
        pass

    completions = list(
        c.get_completions(Document("option-choices-hidden-cmd --handler "))
    )
    assert {x.text for x in completions} == set()


def test_boolean_arg():
    @root_command.command()
    @click.argument("foo", type=click.BOOL)
    def bool_arg(foo):
        pass

    completions = list(
        c.get_completions(Document("bool-arg "))
    )
    assert {x.text for x in completions} == {'true', 'false'}

    completions = list(
        c.get_completions(Document("bool-arg t"))
    )
    assert {x.text for x in completions} == {'true'}


def test_boolean_option():
    @root_command.command()
    @click.option("--foo", type=click.BOOL)
    def bool_option(foo):
        pass

    completions = list(
        c.get_completions(Document("bool-option --foo "))
    )
    assert {x.text for x in completions} == {'true', 'false'}

    completions = list(
        c.get_completions(Document("bool-option --foo t"))
    )
    assert {x.text for x in completions} == {'true'}


def test_tuple_return_type_shell_complete_func():
    def return_type_tuple_shell_complete(ctx, param, incomplete):
        return [
            ("Hi", "hi"),
            ("Please", "please"),
            ("Hey", "hey"),
            ('Aye', 'aye')
        ]


    @root_command.command()
    @click.argument("foo", shell_complete=return_type_tuple_shell_complete)
    def tuple_type_autocompletion_cmd(foo):
        pass

    completions = list(
        c.get_completions(Document("tuple-type-autocompletion-cmd "))
    )
    assert {x.text for x in completions} == {'Hi', 'Please', 'Hey', 'Aye'}

    completions = list(
        c.get_completions(Document("tuple-type-autocompletion-cmd h"))
    )
    assert {x.text for x in completions} == {'Hi', 'Please', 'Hey', 'Aye'}


@pytest.mark.skipif(
    click.__version__[0] > '7',
    reason="click-v7 old autocomplete function is not available, so skipped",
)
def test_tuple_return_type_shell_complete_func_click7():
    def return_type_tuple_shell_complete(ctx, args, incomplete):
        return [
            ("Hi", "hi"),
            ("Please", "please"),
            ("Hey", "hey"),
            ('Aye', 'aye')
        ]


    @root_command.command()
    @click.argument("foo", autocompletion=return_type_tuple_shell_complete)
    def tuple_type_autocompletion_cmd(foo):
        pass

    completions = list(
        c.get_completions(Document("tuple-type-autocompletion-cmd "))
    )
    assert (
        {x.text for x in completions} == {'Hi', 'Please', 'Hey', 'Aye'}
        and {x.display_meta[0][-1] for x in completions} == {'hi', 'please', 'hey', 'aye'}
    )

    completions = list(
        c.get_completions(Document("tuple-type-autocompletion-cmd h"))
    )
    assert {x.text for x in completions} == {'Hi', 'Please', 'Hey', 'Aye'}
