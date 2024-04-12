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


@root_command.command()
@click.option("--handler", type=click.Choice(("foo", "bar")))
@click.option("--wrong", type=click.Choice(("bogged", "bogus")))
def option_choices(handler):
    pass


@pytest.mark.parametrize(
    "test_input, expected",
    [
        ("option-choices --handler ", {"foo", "bar"}),
        ("option-choices --wrong ", {"bogged", "bogus"}),
    ],
)
def test_option_choices(test_input, expected):
    completions = c.get_completions(Document(test_input))
    assert {x.text for x in completions} == expected


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
@click.option("--handler", "-h", type=click.Choice(("foo", "bar")))
def option_cmd(handler):
    pass


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("option-cmd ", {"--handler", "-h"}),
        ("option-cmd -h", {"-h"}),
        ("option-cmd -h ", {"foo", "bar"}),
        ("option-cmd --h", {"--handler"}),
    ],
)
def test_option_completion(test_input, expected):
    completions = c.get_completions(Document(test_input))
    assert {x.text for x in completions} == expected


@pytest.mark.parametrize(
    "test_input, expected", [("option-cmd -hf", {"foo"}), ("option-cmd -hb", {"bar"})]
)
def test_extra_chars_in_short_opt_names(test_input, expected):
    completions = c.get_completions(Document(test_input))
    assert {x.text for x in completions} == expected


@root_command.command()
@click.option("--foo", "-f", is_flag=True)
@click.option("-b", "--bar", is_flag=True)
@click.option("--foobar", is_flag=True)
def shortest_only(foo, bar, foobar):
    pass


c1 = ClickCompleter(
    click.Context(root_command),
    DummyInternalCommandSystem(),
    shortest_option_names_only=True,
)


@pytest.mark.parametrize(
    "test_input, expected",
    [
        ("shortest-only ", {"-f", "-b", "--foobar"}),
        ("shortest-only -", {"-f", "--foo", "-b", "--bar", "--foobar"}),
        ("shortest-only --f", {"--foo", "--foobar"}),
    ],
)
def test_shortest_only_true_mode(test_input, expected):
    completions = c1.get_completions(Document(test_input))
    assert {x.text for x in completions} == expected


c2 = ClickCompleter(
    click.Context(root_command),
    DummyInternalCommandSystem(),
    show_only_unused_options=True,
)


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


@pytest.mark.parametrize(
    "test_input, expected",
    [
        ("multiple-option ", {"--non-multiple", "--multiple"}),
        ("multiple-option -- ", set()),
    ],
)
def test_double_dash_arg(test_input, expected):
    completions = c.get_completions(Document(test_input))
    assert {i.text for i in completions} == expected


@pytest.mark.parametrize(
    "test_input",
    [
        "option-cmd -h=",
        "option-cmd --handler=",
    ],
)
def test_equal_sign_for_opt_and_explicit_value(test_input):
    completions = c.get_completions(Document(test_input))
    assert {i.text for i in completions} == {"foo", "bar"}
