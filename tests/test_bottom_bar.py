from __future__ import annotations

import click
import pytest

from click_repl.bottom_bar import BottomBar
from click_repl.parser import _resolve_state


@click.group()
def main():
    pass


@main.command()
@click.argument("str-arg", nargs=2)
@click.argument(expose_value=False)
@click.argument("func-arg", type=click.types.FuncParamType(int))
@click.argument("choice-arg", type=click.Choice(["a", "b"]))
@click.argument("bool-arg", type=click.BOOL)
@click.argument("intrange-arg", type=click.IntRange(1, 10))
@click.argument("floatrange-arg", type=click.FloatRange(1.1, 10.5))
@click.option(
    "-t",
    "--tuple-opt",
    type=click.Tuple([str, click.types.FuncParamType(int), click.File(), click.Path()]),
)
@click.argument("nargs-opt", type=float, nargs=-1)
def cmd():
    pass


ctx = click.Context(main)
bottombar = BottomBar()


@pytest.mark.parametrize(
    "test_input, expected",
    [
        ("", "Group main: COMMAND [ARGS]..."),
        (
            "cmd ",
            "Command cmd: str-arg (0/2) ... func-arg choice-arg bool-arg intrange-arg "
            "floatrange-arg tuple-opt nargs-opt",
        ),
        (
            "cmd hi ",
            "Command cmd: str-arg (1/2) ... func-arg choice-arg bool-arg intrange-arg "
            "floatrange-arg tuple-opt nargs-opt",
        ),
        (
            "cmd hi hii ",
            "Command cmd: str-arg ... func-arg <int> choice-arg bool-arg intrange-arg "
            "floatrange-arg tuple-opt nargs-opt",
        ),
        (
            "cmd hi hii hello 123 ",
            "Command cmd: str-arg ... func-arg choice-arg <choice> bool-arg intrange-arg "
            "floatrange-arg tuple-opt nargs-opt",
        ),
        (
            "cmd hi hii hello 123 a ",
            "Command cmd: str-arg ... func-arg choice-arg bool-arg <boolean>"
            " intrange-arg floatrange-arg tuple-opt nargs-opt",
        ),
        (
            "cmd hi hii hello 123 a true ",
            "Command cmd: str-arg ... func-arg choice-arg bool-arg intrange-arg "
            "<integer range 1<=x<=10> floatrange-arg tuple-opt nargs-opt",
        ),
        (
            "cmd hi hii hello 123 a true 5 ",
            "Command cmd: str-arg ... func-arg choice-arg bool-arg intrange-arg "
            "floatrange-arg <float range 1.1<=x<=10.5> tuple-opt nargs-opt",
        ),
        (
            "cmd hi hii hello 123 a true 5 6.5 ",
            "Command cmd: str-arg ... func-arg choice-arg bool-arg intrange-arg "
            "floatrange-arg tuple-opt nargs-opt <float> ...",
        ),
        (
            "cmd hi hii hello 123 a true 5 6.5 1.0 ",
            "Command cmd: str-arg ... func-arg choice-arg bool-arg intrange-arg "
            "floatrange-arg tuple-opt nargs-opt <float> ...",
        ),
        (
            "cmd hi hii hello 123 a true 5 6.5 1.0 2.0 3.0 ",
            "Command cmd: str-arg ... func-arg choice-arg bool-arg intrange-arg "
            "floatrange-arg tuple-opt nargs-opt <float> ...",
        ),
        (
            "cmd hi hii hello 123 a true 5 6.5 --tuple-opt=",
            "Command cmd: str-arg ... func-arg choice-arg bool-arg intrange-arg "
            "floatrange-arg tuple-opt(<text> <int> <filename> <path>) nargs-opt",
        ),
        (
            "cmd --tuple-opt ",
            "Command cmd: str-arg ... func-arg choice-arg bool-arg intrange-arg "
            "floatrange-arg tuple-opt(<text> <int> <filename> <path>) nargs-opt",
        ),
        (
            "cmd --tuple-opt hi ",
            "Command cmd: str-arg ... func-arg choice-arg bool-arg intrange-arg "
            "floatrange-arg tuple-opt(<text> <int> <filename> <path>) nargs-opt",
        ),
        (
            "cmd --tuple-opt hi 123 ",
            "Command cmd: str-arg ... func-arg choice-arg bool-arg intrange-arg "
            "floatrange-arg tuple-opt(<text> <int> <filename> <path>) nargs-opt",
        ),
        (
            "cmd --tuple-opt hi 123 tests/test_repl.py ",
            "Command cmd: str-arg ... func-arg choice-arg bool-arg intrange-arg "
            "floatrange-arg tuple-opt(<text> <int> <filename> <path>) nargs-opt",
        ),
        (
            "cmd --tuple-opt hi 123 tests/test_repl.py /some/path/ ",
            "Command cmd: str-arg (0/2) ... func-arg choice-arg bool-arg intrange-arg "
            "floatrange-arg tuple-opt nargs-opt",
        ),
    ],
)
def test_bottom_bar_(test_input, expected):
    _, state, _ = _resolve_state(ctx, test_input)
    bottombar.state = state
    marquee = bottombar.make_formatted_text()

    text = marquee.prefix.get_text() + marquee.text.get_text()
    assert text == expected


@click.group(chain=True)
def chainned_group():
    pass


@chainned_group.command(name=None)
def cmd2():
    pass


@chainned_group.command(name=None)
@click.argument("arg")
def cmd3(arg):
    pass


ctx2 = click.Context(chainned_group)


@pytest.mark.parametrize(
    "test_input, expected",
    [
        ("", "Group chainned-group: COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]..."),
        ("cmd2 ", "Group chainned-group: COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]..."),
        ("cmd3 ", "Command cmd3: arg"),
    ],
)
def test_chained_group_metavar(test_input, expected):
    _, state, _ = _resolve_state(ctx2, test_input)
    bottombar.state = state
    marquee = bottombar.make_formatted_text()

    text = marquee.prefix.get_text() + marquee.text.get_text()
    assert text == expected


@click.group()
def no_subcommand_group():
    pass


ctx3 = click.Context(no_subcommand_group)


def test_no_subcommand_group_metavar():
    _, state, _ = _resolve_state(ctx3, "")
    bottombar.state = state
    marquee = bottombar.make_formatted_text()

    text = marquee.prefix.get_text() + marquee.text.get_text()
    assert text == "Group no-subcommand-group"
