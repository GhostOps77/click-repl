from __future__ import annotations

import click
import pytest
from prompt_toolkit.document import Document
from prompt_toolkit.validation import ValidationError

from click_repl._globals import HAS_CLICK_GE_8
from click_repl.internal_commands import InternalCommandSystem
from click_repl.validator import ClickValidator
from tests import DummyInternalCommandSystem


@click.group()
def main():
    pass


def click_err_callback(ctx, param, incomplete):
    raise click.ClickException("sample click error")


def standard_err_callback(ctx, param, incomplete):
    raise Exception("sample standard error")


@main.command()
@click.option("--opt1", callback=click_err_callback)
@click.option("--opt2", callback=standard_err_callback)
def command(opt1, opt2):
    pass


validator = ClickValidator(click.Context(main), InternalCommandSystem())


@pytest.mark.parametrize("test_input", ["!echo hi", ":cls"])
def test_validator_ignores_internal_commands(test_input):
    assert validator.validate(Document(test_input)) is None


@pytest.mark.parametrize(
    "test_input, expected_err",
    [
        ("command --hi ", "No such option: --hi"),
        ("command --opt1 ", "sample click error"),
        ("command --opt2 ", "sample standard error"),
    ],
)
def test_default_validator(test_input, expected_err):
    if not HAS_CLICK_GE_8:
        expected_err = expected_err.lower()

    with pytest.raises(ValidationError, match=expected_err):
        validator.validate(Document(test_input))


validator_dont_show_all_errors = ClickValidator(
    click.Context(main), DummyInternalCommandSystem(), display_all_errors=False
)


@pytest.mark.parametrize(
    "test_input, expected_err",
    [
        ("command --hi ", "No such option: --hi"),
        ("command --opt1 ", "sample click error"),
    ],
)
def test_display_all_errors_false_no_change_on_click_exc(test_input, expected_err):
    if not HAS_CLICK_GE_8:
        expected_err = expected_err.lower()

    with pytest.raises(ValidationError, match=expected_err):
        validator_dont_show_all_errors.validate(Document(test_input))


def test_dont_show_all_errors_hides_other_exc():
    CLICK_REPL_DEV_ENV = True

    validator_dont_show_all_errors.validate(Document("command --opt2 "))

    with open(".click-repl-err.log") as log_file:
        assert log_file.readlines()[-1].strip() == "Exception: sample standard error"

    CLICK_REPL_DEV_ENV = False  # noqa: F841
