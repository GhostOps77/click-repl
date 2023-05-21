import glob
import os

import click
import pytest
from prompt_toolkit.document import Document

from click_repl import ClickCompleter


@click.group()
def root_command():
    pass


@root_command.command()
@click.argument("path", type=click.Path())
def path_type_arg(path):
    pass


c = ClickCompleter(root_command, click.Context(root_command))


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("path-type-arg ", glob.glob("*")),
        ("path-type-arg tests/", glob.glob("tests/*")),
        ("path-type-arg src/*", []),
        ("path-type-arg src/**", []),
        ('path-type-arg "tests/testdir/test "', {"test file.txt", "test directory"}),
        (
            "path-type-arg tests/testdir/",
            glob.glob("tests/testdir/*"),
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