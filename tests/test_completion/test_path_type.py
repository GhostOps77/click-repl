from pathlib import Path
import os

import click
import pytest
from prompt_toolkit.document import Document

from click_repl import ClickCompleter


@click.group()
def root_command():
    pass


@root_command.command("pathTypeArg")
@click.argument("path", type=click.Path())
def pathTypeArg(path):
    pass


c = ClickCompleter(click.Context(root_command))


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("pathTypeArg ", Path(".").glob("*")),
        ("pathTypeArg tests/", Path(".").glob("tests/*")),
        ("pathTypeArg src/*", []),
        ("pathTypeArg src/**", []),
        (
            "pathTypeArg tests/testdir/",
            Path(".").glob("tests/testdir/*"),
        ),
    ],
)
def test_path_type_arg(test_input, expected):
    completions = c.get_completions(Document(test_input))
    assert {x.display[0][1] for x in completions} == {
        os.path.basename(i) for i in expected
    }


# @pytest.mark.skipif(os.name != 'nt', reason='This is a test for Windows OS')
# def test_win_path_env_expanders():
#     completions = c.get_completions(Document('path-type-arg %LocalAppData%'))
#     assert {x.display[0][1] for x in completions} == {'Local', 'LocalLow'}


# @pytest.mark.skipif(os.name != 'posix', reason='This is a test for Linux OS')
# def test_posix_path_env_expanders():
#     completions = c.get_completions(Document('path-type-arg $USER'))
#     assert {x.display[0][1] for x in completions} == {os.path.expandvars("$USER")}
