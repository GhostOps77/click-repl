from __future__ import annotations

import pytest

from click_repl.exceptions import PrefixNotFound, SamePrefix, WrongType
from click_repl.internal_commands import InternalCommandSystem
from click_repl.internal_commands import repl_exit as repl_exit

ics = InternalCommandSystem()


@pytest.mark.parametrize("test_input", [";", "'", ",", "hi "])
def test_other_valid_internal_command_prefixes(test_input):
    ics.internal_command_prefix = test_input


@pytest.mark.parametrize("test_input", [";", "'", ","])
def test_other_valid_system_command_prefixes(test_input):
    ics.system_command_prefix = test_input


def test_system_command_same_prefix_error():
    ics.internal_command_prefix = ":"

    with pytest.raises(SamePrefix):
        ics.system_command_prefix = ":"


def test_internal_command_same_prefix_error():
    ics.system_command_prefix = "!"

    with pytest.raises(SamePrefix):
        ics.internal_command_prefix = "!"


@pytest.mark.parametrize(
    "test_input, exception",
    [
        ("", ValueError),
        (123, WrongType),
        ([], WrongType),
    ],
)
def test_incorrect_value_for_prefixes(test_input, exception):
    with pytest.raises(exception):
        ics.validate_prefix(test_input, "var name")


@pytest.mark.parametrize("test_prefix", ["a", "s", "d", "f"])
def test_prefix_not_found_error(test_prefix):
    with pytest.raises(PrefixNotFound):
        ics.execute(f"{test_prefix}cmd")
