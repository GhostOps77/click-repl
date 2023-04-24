#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os
import sys
import click
from functools import lru_cache
from glob import iglob

if sys.version_info >= (3, 6):
    from shlex import shlex
else:
    from .shlex2 import shlex  # type: ignore[attr-defined]

from prompt_toolkit.completion import Completion
from .exceptions import CommandLineParserError
from ._globals import text_type

# typing module introduced in Python 3.5
if sys.version_info >= (3, 5):
    import typing as t

    if t.TYPE_CHECKING:
        from typing import Optional, Dict, Union, List, Tuple, NoReturn  # noqa: F401
        from click import Command, Context, Parameter  # noqa: F401


IS_WINDOWS = os.name == "nt"


# Handle backwards compatibility for click<=8
try:
    import click.shell_completion  # noqa: F401

    HAS_CLICK_V8 = True
    AUTO_COMPLETION_PARAM = "shell_complete"
except ImportError:
    import click._bashcomplete  # type: ignore[import]

    HAS_CLICK_V8 = False
    AUTO_COMPLETION_PARAM = "autocompletion"


def split_arg_string(string, posix=True):
    # type: (str, bool) -> "List[str]"
    """Split an argument string as with :func:`shlex.split`, but don't
    fail if the string is incomplete. Ignores a missing closing quote or
    incomplete escape sequence and uses the partial token as-is.
    .. code-block:: python
        split_arg_string("example 'my file")
        ["example", "my file"]
        split_arg_string("example my\\")
        ["example", "my"]
    :param string: String to split.
    """

    lex = shlex(string, posix=posix, punctuation_chars=True)
    lex.whitespace_split = True
    lex.commenters = ""
    out = []  # type: List[str]

    try:
        for token in lex:
            out.append(token)
    except ValueError:
        # Raised when end-of-string is reached in an invalid state. Use
        # the partial token as-is. The quote or escape character is in
        # lex.state, not lex.token.
        out.append(lex.token)

    return out


# @lru_cache(maxsize=3)
def get_ctx_for_args(cmd, parsed_args, group_args):
    # type: (Command, List[str], List[str]) -> Tuple[Command, Context]

    # Resolve context based on click version
    if HAS_CLICK_V8:
        parsed_ctx = click.shell_completion._resolve_context(
            cmd, {}, "", group_args + parsed_args
        )
    else:
        parsed_ctx = click._bashcomplete.resolve_ctx(
            cmd, "", group_args + parsed_args
        )

    ctx_command = parsed_ctx.command
    # opt_parser = OptionsParser(ctx_command, parsed_ctx)

    return ctx_command, parsed_ctx


@lru_cache(maxsize=3)
def _split_args(document_text):
    # type: (str) -> Optional[Tuple[List[str], str]]
    if document_text.startswith(("!", ":")):
        return None

    # try:
    args = split_arg_string(document_text, posix=False)
    # except ValueError:
    #     # Invalid command, perhaps caused by missing closing quotation.
    #     return

    cursor_within_command = (
        document_text.rstrip() == document_text
    )

    if args and cursor_within_command:
        # We've entered some text and no space, give completions for the
        # current word.
        incomplete = args.pop()
    else:
        # We've not entered anything, either at all or for the current
        # command, so give all relevant completions for this context.
        incomplete = ""

    return args, incomplete


class CompletionParser:
    """Provides Completion items based on the given parameters
    along with the styles provided to it.

    Keyword arguments:
    :param:`styles` -- Dictionary of styles in the way of prompt-toolkit module,
    for arguments, options, etc.
    """

    __slots__ = ("styles", )

    def __init__(self, styles):
        # type: (Dict[str, str]) -> None
        self.styles = styles

    def _get_completion_from_autocompletion_functions(
        self, param, autocomplete_ctx, args, incomplete,
    ):
        # type: (Parameter, Context, List[str], str) -> List[Completion]
        param_choices = []

        if HAS_CLICK_V8:
            autocompletions = param.shell_complete(autocomplete_ctx, incomplete)
        else:
            autocompletions = param.autocompletion(  # type: ignore[attr-defined]
                autocomplete_ctx, args, incomplete
            )

        for autocomplete in autocompletions:
            if isinstance(autocomplete, tuple):
                param_choices.append(
                    Completion(
                        text_type(autocomplete[0]),
                        -len(incomplete),
                        display_meta=autocomplete[1],
                    )
                )

            elif HAS_CLICK_V8 and isinstance(
                autocomplete, click.shell_completion.CompletionItem
            ):
                param_choices.append(
                    Completion(text_type(autocomplete.value), -len(incomplete))
                )

            elif isinstance(autocomplete, Completion):
                param_choices.append(autocomplete)

            else:
                param_choices.append(
                    Completion(text_type(autocomplete), -len(incomplete))
                )

        return param_choices

    def _get_completion_from_choices_click_le_7(self, param_type, incomplete):
        # type: (click.Choice, str) -> List[Completion]

        if not getattr(param_type, "case_sensitive", True):
            incomplete = incomplete.lower()
            return [
                Completion(
                    text_type(choice),
                    -len(incomplete),
                    style=self.styles["argument"],
                    display=text_type(repr(choice) if " " in choice else choice),
                )
                for choice in param_type.choices
                if choice.lower().startswith(incomplete)
            ]

        else:
            return [
                Completion(
                    text_type(choice),
                    -len(incomplete),
                    style=self.styles["argument"],
                    display=text_type(repr(choice) if " " in choice else choice),
                )
                for choice in param_type.choices
                if choice.startswith(incomplete)
            ]

    def _get_completion_for_Path_types(self, incomplete):
        # type: (str) -> List[Completion]

        if "*" in incomplete:
            return []

        choices = []
        _incomplete = os.path.expandvars(incomplete)
        search_pattern = _incomplete.strip("'\"").replace("\\\\", "\\") + "*"
        quote = ""

        if " " in _incomplete:
            for i in incomplete:
                if i in ("'", '"'):
                    quote = i
                    break

        for path in iglob(search_pattern):
            if " " in path:
                if quote:
                    path = quote + path
                else:
                    if IS_WINDOWS:
                        path = repr(path).replace("\\\\", "\\")
            else:
                if IS_WINDOWS:
                    path = path.replace("\\", "\\\\")

            choices.append(
                Completion(
                    text_type(path),
                    -len(incomplete),
                    display=text_type(os.path.basename(path.strip("'\""))),
                )
            )

        return choices

    def _get_completion_for_Boolean_type(self, incomplete):
        # type: (str) -> List[Completion]
        return [
            Completion(
                text_type(k), -len(incomplete), display_meta=text_type("/".join(v))
            )
            for k, v in {
                "true": ("1", "true", "t", "yes", "y", "on"),
                "false": ("0", "false", "f", "no", "n", "off"),
            }.items()
            if any(i.startswith(incomplete) for i in v)
        ]

    def _get_completion_for_Range_types(self, param_type, incomplete):
        # type: (Union[click.IntRange, click.FloatRange], str) -> List[Completion]
        clamp = " clamped" if param_type.clamp else ""
        display_meta = "{}{}".format(param_type._describe_range(), clamp)

        return [Completion('-', display_meta=display_meta)]

    def _get_completion_from_params(self, autocomplete_ctx, args, param, incomplete):
        # type: (Context, List[str], Parameter, str) -> List[Completion]

        choices = []  # type: List[Completion]
        param_type = param.type  # type: click.ParamType

        if isinstance(param_type, (click.IntRange, click.FloatRange)):
            return self._get_completion_for_Range_types(param_type, incomplete)

        elif isinstance(param_type, click.Tuple):
            return [
                Completion('', display=text_type(_type.name))
                for _type in param_type.types
            ]

        # shell_complete method for click.Choice is intorduced in click-v8
        elif not HAS_CLICK_V8 and isinstance(param_type, click.Choice):
            choices.extend(
                self._get_completion_from_choices_click_le_7(param_type, incomplete)
            )

        elif isinstance(param_type, click.types.BoolParamType):
            choices.extend(self._get_completion_for_Boolean_type(incomplete))

        elif isinstance(param_type, (click.Path, click.File)):
            choices.extend(self._get_completion_for_Path_types(incomplete))

        elif getattr(param, AUTO_COMPLETION_PARAM, None) is not None:
            choices.extend(
                self._get_completion_from_autocompletion_functions(
                    param,
                    autocomplete_ctx,
                    args,
                    incomplete,
                )
            )

        return choices

    def _get_completion_for_cmd_args(
        self,
        ctx_command,  # type: Command
        incomplete,  # type: str
        autocomplete_ctx,  # type: Context
        args,  # type: List[str]
    ):
        # type: (...) -> Union[List[Completion], NoReturn]

        choices = []
        param_called = False
        params_list = ctx_command.params
        for index, param in enumerate(params_list):
            if param.nargs == -1:
                params_list.append(params_list.pop(index))

        # print("Currently introspecting argument:", autocomplete_ctx.info_name)
        for param in params_list:
            # print(f'{vars(param) = }')
            for attr in ("hidden", "hide_input"):
                if getattr(param, attr, False):
                    raise CommandLineParserError(
                        "Click Repl cannot parse a '{}' parameter".format(attr)
                    )

            if isinstance(param, click.Option):
                options_name_list = param.opts + param.secondary_opts
                if param.is_bool_flag and any(i in args for i in options_name_list):
                    continue

                for option in options_name_list:
                    # print(f'{option = }')
                    # We want to make sure if this parameter was called
                    # If we are inside a parameter that was called, we want to show only
                    # relevant choices
                    # print(f'{args[param.nargs * -1 :] = } {incomplete = !r}')
                    if (
                        option in args[param.nargs * -1:]
                        and not param.count
                       ):

                        param_called = True
                        # print(f"param called by {param.name}")
                        break

                    # elif option in args and not (param.multiple or param.count):
                    #     break

                    elif option.startswith(incomplete):
                        # print(f'{option} startswith ({incomplete})\n')
                        choices.append(
                            Completion(
                                text_type(option),
                                -len(incomplete),
                                display_meta=text_type(
                                    param.help or "") + '[Default={}]'.format(
                                    param.default) if param.default else '',
                                style=self.styles["option"],
                            )
                        )

                # If we are inside a parameter that was called, we want to show only
                # relevant choices
                # print(f'{param.name = } {param_called = }')
                if param_called and not (param.is_bool_flag or param.count):
                    choices = self._get_completion_from_params(
                        autocomplete_ctx, args, param, incomplete
                    )
                    break

            elif isinstance(param, click.Argument):
                if (
                    autocomplete_ctx.params.get(
                        param.name) is None  # type: ignore[arg-type]
                    or param.nargs == -1
                ):
                    choices.extend(
                        self._get_completion_from_params(
                            autocomplete_ctx, args, param, incomplete
                        )
                    )
                    break

        return choices
