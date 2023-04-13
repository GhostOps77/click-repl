#!/usr/bin/python
# -*- coding: ascii -*-

from __future__ import unicode_literals

import os
import sys
from glob import iglob

import click
from prompt_toolkit.completion import Completion, Completer

from .utils import split_arg_string

__all__ = ["ClickCompleter"]


IS_WINDOWS = os.name == "nt"

# typing module introduced in Python 3.5
if sys.version_info >= (3, 5):
    import typing as t

    if t.TYPE_CHECKING:
        from typing import Any, Generator, Optional, Union, Dict, List  # noqa: F401

        from click import Command, Context, Group, Parameter  # noqa: F401
        from prompt_toolkit.completion import CompleteEvent  # noqa: F401
        from prompt_toolkit.document import Document  # noqa: F401


# Handle backwards compatibility between Click<=7.0 and >=8.0
try:
    import click.shell_completion

    HAS_CLICK_V8 = True
    AUTO_COMPLETION_PARAM = "shell_complete"
except (ImportError, ModuleNotFoundError):
    import click._bashcomplete  # type: ignore[import]

    HAS_CLICK_V8 = False
    AUTO_COMPLETION_PARAM = "autocompletion"


def text_type(text):
    # type: (Any) -> str
    # fmt: off
    return u"{}".format(text)
    # fmt: on


class ClickCompleter(Completer):
    __slots__ = ("cli", "ctx", "styles")

    def __init__(self, cli, ctx=None, styles=None):
        # type: (Group, Optional[Context], Optional[Dict[str, str]]) -> None

        self.cli = cli  # type: Command
        self.ctx = ctx  # type: Optional[Context]
        if styles is not None:
            self.styles = styles  # type: Dict[str, str]
        else:
            self.styles = dict.fromkeys(["command", "argument", "option"], "")

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

            else:
                param_choices.append(
                    Completion(text_type(autocomplete), -len(incomplete))
                )

        return param_choices

    def _get_completion_from_choices_click_le_7(self, param, incomplete):
        # type: (Parameter, str) -> List[Completion]

        if not getattr(param.type, "case_sensitive", True):
            incomplete = incomplete.lower()
            return [
                Completion(
                    text_type(choice),
                    -len(incomplete),
                    style=self.styles["argument"],
                    display=text_type(repr(choice) if " " in choice else choice),
                )
                for choice in param.type.choices  # type: ignore[attr-defined]
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
                for choice in param.type.choices  # type: ignore[attr-defined]
                if choice.startswith(incomplete)
            ]

    def _get_completion_for_Path_types(self, param, args, incomplete):
        # type: (Parameter, List[str], str) -> List[Completion]

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

    def _get_completion_for_Boolean_type(self, param, incomplete):
        # type: (Union[Parameter, click.Option], str) -> List[Completion]
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

    def _get_completion_from_params(self, autocomplete_ctx, args, param, incomplete):
        # type: (Context, List[str], Parameter, str) -> List[Completion]
        choices = []  # type: List[Completion]
        param_type = param.type  # type: click.ParamType

        if isinstance(param_type, click.types.UnprocessedParamType):
            return []

        elif isinstance(param_type, (click.IntRange, click.FloatRange)):
            left_exclusive = '='*(not param_type.min_open or not param_type.clamp)
            right_exclusive = '='*(not param_type.max_open or not param_type.clamp)

            min_val = param_type.min if param_type.min is not None else '-∞'
            max_val = param_type.max if param_type.max is not None else '∞'
            display_meta = '{} <{} x <{} {}'.format(
                min_val, left_exclusive, right_exclusive, max_val
            )

            return [Completion('-', display='clamps input', display_meta=display_meta)]

        # shell_complete method for click.Choice is intorduced in click-v8
        elif not HAS_CLICK_V8 and isinstance(param_type, click.Choice):
            choices.extend(
                self._get_completion_from_choices_click_le_7(param, incomplete)
            )

        elif isinstance(param_type, click.types.BoolParamType):
            choices.extend(self._get_completion_for_Boolean_type(param, incomplete))

        elif isinstance(param_type, (click.Path, click.File)):
            choices.extend(self._get_completion_for_Path_types(param, args, incomplete))

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
        # type: (...) -> List[Completion]

        choices = []
        param_called = False
        params_list = ctx_command.params
        for index, param in enumerate(params_list):
            if param.nargs == -1:
                params_list.append(params_list.pop(index))

        # print("Currently introspecting argument:", autocomplete_ctx.info_name)
        for param in params_list:
            # print(f'{vars(param) = }')
            if getattr(param, "hidden", False) or getattr(param, "hide_input", False):
                continue

            elif isinstance(param, click.Option):
                options_name_list = param.opts + param.secondary_opts

                if param.is_bool_flag and any(i in args for i in options_name_list):
                    continue

                for option in options_name_list:
                    # print(f'{option = }')
                    # We want to make sure if this parameter was called
                    # If we are inside a parameter that was called, we want to show only
                    # relevant choices
                    # print(f'{args[param.nargs * -1 :] = } {incomplete = !r}')
                    if option in args[param.nargs * -1 :]:  # noqa: E203
                        param_called = True
                        # print(f"param called by {param.name}")
                        break

                    elif option in args and not (param.multiple or param.count):
                        # print('option in args and not (param.multiple or param.count)')
                        break

                    elif option.startswith(incomplete):
                        # print(f'{option} startswith ({incomplete})')
                        choices.append(
                            Completion(
                                text_type(option),
                                -len(incomplete),
                                display_meta=text_type(param.help or ""),
                                style=self.styles["option"],
                            )
                        )

                # If we are inside a parameter that was called, we want to show only
                # relevant choices
                # print(f'{param.name = } {param_called = }')
                if param_called and not param.is_bool_flag:
                    choices = self._get_completion_from_params(
                        autocomplete_ctx, args, param, incomplete
                    )
                    break

            elif isinstance(param, click.Argument):
                if autocomplete_ctx.params.get(
                    param.name  # type: ignore[arg-type]
                ) is None:
                    choices.extend(
                        self._get_completion_from_params(
                            autocomplete_ctx, args, param, incomplete
                        )
                    )
                    break

        return choices

    def get_completions(self, document, complete_event=None):
        # type: (Document, Optional[CompleteEvent]) -> Generator[Completion, None, None]

        # Code analogous to click._bashcomplete.do_complete

        document_text_before_cursor = document.text_before_cursor

        if document_text_before_cursor.startswith(("!", ":")):
            return

        # try:
        args = split_arg_string(document_text_before_cursor, posix=False)
        # except ValueError:
        #     # Invalid command, perhaps caused by missing closing quotation.
        #     return

        choices = []  # type: List[Completion]
        cursor_within_command = (
            document_text_before_cursor.rstrip() == document_text_before_cursor
        )

        if args and cursor_within_command:
            # We've entered some text and no space, give completions for the
            # current word.
            incomplete = args.pop()
        else:
            # We've not entered anything, either at all or for the current
            # command, so give all relevant completions for this context.
            incomplete = ""

        # Resolve context based on click version
        if HAS_CLICK_V8:
            ctx = click.shell_completion._resolve_context(self.cli, {}, "", args)
        else:
            ctx = click._bashcomplete.resolve_ctx(self.cli, "", args)

        autocomplete_ctx = self.ctx or ctx
        ctx_command = ctx.command

        # print(f'(from get_completions) {vars(ctx) = }\n')
        # print(f'(from get_completions) {vars(autocomplete_ctx) = }\n')

        if getattr(ctx_command, "hidden", False):
            return

        try:
            # choices.extend(
            #     self._get_completion_for_cmd_args(
            #         ctx_command, incomplete, autocomplete_ctx, args
            #     )
            # )
            if isinstance(ctx_command, click.MultiCommand):
                for name in ctx_command.list_commands(ctx):
                    command = ctx_command.get_command(ctx, name)
                    if getattr(command, "hidden", False):
                        continue

                    elif name.startswith(incomplete):
                        choices.append(
                            Completion(
                                text_type(name),
                                -len(incomplete),
                                display_meta=getattr(command, "short_help", ""),
                            )
                        )

            else:
                choices.extend(
                    self._get_completion_for_cmd_args(
                        ctx_command,
                        incomplete,
                        autocomplete_ctx,  # type: ignore[arg-type]
                        args
                    )
                )

        except Exception as e:
            click.echo("{}: {}".format(type(e).__name__, str(e)))

        for item in choices:
            yield item
