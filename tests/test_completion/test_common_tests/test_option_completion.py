import click
import pytest
from prompt_toolkit.document import Document

from click_repl import ClickCompleter


@click.group()
def root_command():
    pass


c = ClickCompleter(click.Context(root_command))


def test_option_choices():
    @root_command.command()
    @click.option("--handler", type=click.Choice(("foo", "bar")))
    @click.option("--wrong", type=click.Choice(("bogged", "bogus")))
    def option_choices(handler):
        pass

    completions = list(c.get_completions(Document("option-choices --handler ")))
    assert {x.text for x in completions} == {"foo", "bar"}

    completions = list(c.get_completions(Document("option-choices --wrong ")))
    assert {x.text for x in completions} == {"bogged", "bogus"}


@root_command.command()
@click.option("--foo", type=click.BOOL)
def bool_option(foo):
    pass


@pytest.mark.parametrize(
    "test_input, expected",
    [
        ("bool-option --foo ", {"true", "false"}),
        ("bool-option --foo t", {"true"}),
    ],
)
def test_boolean_option(test_input, expected):
    completions = c.get_completions(Document(test_input))
    assert {x.text for x in completions} == expected


@root_command.command()
@click.option("--handler", "-h", type=click.Choice(("foo", "bar")), help="Demo option")
def option_cmd(handler):
    pass


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("option-cmd ", {"--handler", "-h"}),
        ("option-cmd -h", {"-h"}),
        ("option-cmd --h", {"--handler"}),
    ],
)
def test_option_completion(test_input, expected):
    completions = c.get_completions(Document(test_input))
    assert {x.text for x in completions} == expected


@root_command.command()
@click.option("--foo", "-f", is_flag=True)
@click.option("-b", "--bar", is_flag=True)
@click.option("--foobar", is_flag=True)
def shortest_only(foo, bar, foobar):
    pass


c1 = ClickCompleter(click.Context(root_command), shortest_opts_only=True)


@pytest.mark.parametrize(
    "test_input, expected",
    [
        ("shortest-only ", {"-f", "-b", "--foobar"}),
        ("shortest-only -", {"-f", "-b", "--foobar"}),
        ("shortest-only --f", {"--foo", "--foobar"}),
    ],
)
def test_shortest_only_true_mode(test_input, expected):
    completions = c1.get_completions(Document(test_input))
    assert {x.text for x in completions} == expected


c2 = ClickCompleter(click.Context(root_command), show_only_unused_opts=True)


@root_command.command()
@click.option("--non-multiple", type=click.BOOL)
@click.option("--multiple", type=click.BOOL, multiple=True)
def multiple_option(u):
    pass


@pytest.mark.parametrize(
    "test_input, expected",
    [
        ("multiple-option ", {"--non-multiple", "--multiple"}),
        ("multiple-option --non-multiple t ", {"--multiple"}),
        ("multiple-option --non-multiple t --multiple t ", {"--multiple"}),
        ("multiple-option --multiple t ", {"--non-multiple", "--multiple"}),
    ],
)
def test_only_unused_with_multiple_option(test_input, expected):
    completions = list(c2.get_completions(Document(test_input)))
    assert {x.text for x in completions} == expected
