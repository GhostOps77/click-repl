import os
import re
import typing as t
from functools import lru_cache

from pathlib import Path
from shlex import shlex

import click
from prompt_toolkit.completion import Completion

# from .exceptions import CommandLineParserError

if t.TYPE_CHECKING:
    from typing import Dict, Generator, List, Tuple, Union, Optional, Iterable

    from click import Command, Context, Parameter, MultiCommand  # noqa: F401


EQUAL_SIGNED_OPTION = re.compile(r"^(\W{1,2}[a-z][a-z-]*)=", re.I)
IS_WINDOWS = os.name == "nt"

# Float Range is introduced after IntRange, in click v7
try:
    from click import FloatRange

    _Range_types = (click.IntRange, FloatRange)
except ImportError:
    _Range_types = (click.IntRange,)  # type: ignore[assignment]


# Handle backwards compatibility for click<=8
try:
    import click.shell_completion  # noqa: F401

    HAS_CLICK_V8 = True
    AUTO_COMPLETION_PARAM = "shell_complete"
except ImportError:
    import click._bashcomplete  # type: ignore[import]

    HAS_CLICK_V8 = False
    AUTO_COMPLETION_PARAM = "autocompletion"


def quotes(text: str) -> str:
    if " " in text:
        return f'"{text}"'
    return text


def shlex_split(string: str, posix: bool = True) -> "List[str]":
    """Split an argument string as with :func:`shlex.split`, but don't
    fail if the string is incomplete. Ignores a missing closing quote or
    incomplete escape sequence and uses the partial token as-is.
    .. code-block:: python
        shlex_split("example 'my file")
        ["example", "my file"]
        shlex_split("example my\\")
        ["example", "my"]

    :param `string`: String to split.
    :param `posix`: Split string in posix style (default: True)

    Return: A list that contains the splitted string
    """

    lex = shlex(string, posix=posix, punctuation_chars=True)
    lex.whitespace_split = True
    lex.commenters = ""
    lex.escape = ""
    out: "List[str]" = []
    # remaining_token: str = ""

    try:
        out.extend(lex)
    except ValueError:
        # Raised when end-of-string is reached in an invalid state. Use
        # the partial token as-is. The quote or escape character is in
        # lex.state, not lex.token.
        # remaining_token = lex.token
        out.append(lex.token)

    # To get the actual text passed in through REPL cmd line
    # irrespective of quotes
    # last_val = ""
    # if out and remaining_token == "" and not string[-1].isspace():
    #     remaining_token = out[-1]

    #     tmp = ""
    #     for i in reversed(string.split()):
    #         last_val = f"{i} {tmp}".strip()
    #         if last_val.replace("'", "").replace('"', "") == remaining_token:
    #             break
    #         else:
    #             tmp = last_val

    #     if out and last_val == out[-1]:
    #         last_val = ""

    return out  # , last_val


def split_arg_string(string: str) -> "List[str]":
    args = shlex_split(string)
    # out = []
    # for i in args:
    #     match = EQUAL_SIGNED_OPTION.match(i)
    #     if match:
    #         out.append(match[1])
    #         out.append(match[2])
    #     else:
    #         out.append(i)

    return args


@lru_cache(maxsize=3)
def get_args_and_incomplete_from_args(document_text: str) -> "Tuple[List[str], str]":
    args = shlex_split(document_text)
    cursor_within_command = not document_text[-1:].isspace()
    # cursor_within_command = (
    #     document_text.rstrip() == document_text
    # )

    if args and cursor_within_command:  # and not remaining_token:
        # We've entered some text and no space, give completions for the
        # current word.
        incomplete = args.pop()
    else:
        # We've not entered anything, either at all or for the current
        # command, so give all relevant completions for this context.
        incomplete = ""  # remaining_token

    match = EQUAL_SIGNED_OPTION.split(incomplete, 1)
    if len(match) > 1:
        opt, incomplete = match[1], match[2]
        args.append(opt)

    incomplete = os.path.expandvars(os.path.expanduser(incomplete))

    return args, incomplete


class ParsingState:
    """Custom class to parse the list of args"""

    __slots__ = (
        "cli",
        "ctx",
        "args",
        "current_group",
        "current_cmd",
        "current_param",
        "cmd_params",
        # 'parsed_params',
        "remaining_params",
    )

    def __init__(self, cli: "MultiCommand", ctx: "Context", args: "List[str]") -> None:
        self.cli = cli
        self.ctx = ctx
        self.args = args

        self.current_group: "Optional[MultiCommand]" = None
        self.current_cmd: "Optional[Command]" = None
        self.current_param: "Optional[Parameter]" = None

        self.cmd_params: "List[Parameter]" = []
        # self.current_cmd_or_group_params = None
        self.remaining_params: "List[Parameter]" = []

        self.parse_cmd(ctx)
        self.get_params_to_parse(ctx)
        self.parse_params(ctx, args)

    def __str__(self) -> str:
        res = getattr(self.current_group, 'name', 'None')

        cmd = getattr(self.current_cmd, "name", None)
        if cmd is not None:
            res += f" > {cmd}"

        param = getattr(self.current_param, "name", None)
        if param is not None:
            res += f" > {param}"

        return res

    def __repr__(self) -> str:
        return f'"{str(self)}"'

    def parse_cmd(self, ctx: "Context") -> None:
        ctx_cmd = ctx.command
        parent_group = ctx_cmd
        if ctx.parent is not None:
            parent_group = ctx.parent.command

        self.current_group = parent_group  # type: ignore[assignment]
        is_cli = ctx_cmd == self.cli

        # All the required arguments are assigned with values
        all_args_val = all(
            ctx.params.get(i.name, None) is not None  # type: ignore[arg-type]
            for i in ctx_cmd.params
            if isinstance(i, click.Argument)
        )

        if isinstance(ctx_cmd, click.MultiCommand) and (is_cli or all_args_val):
            self.current_group = ctx_cmd

        elif isinstance(ctx_cmd, click.Command) and not (
            getattr(parent_group, "chain", False) and all_args_val
        ):
            self.current_cmd = ctx_cmd

        else:
            self.current_cmd = ctx_cmd  # type: ignore[unreachable]

        # if not (
        #     getattr(self.current_group, 'chain', False)
        #     and self.remaining_params
        #     and any(isinstance(i, click.Argument) for i in self.remaining_params)
        # ):
        #     ...

    def get_params_to_parse(self, ctx: "Context") -> None:
        if self.current_cmd is None:
            return

        minus_one_args = []
        minus_one_opts = []
        option_args = []

        for param in self.current_cmd.params:
            if isinstance(param, click.Option):
                if param.nargs == -1:
                    minus_one_opts.append(param)

                else:
                    option_args.append(param)

            elif isinstance(param, click.Argument):
                if (
                    param.nargs == -1
                    and ctx.params.get(param, None)  # type: ignore[call-overload]
                    is not None
                ):
                    minus_one_args.append(param)

                elif ctx.params.get(param.name, None) is None:  # type: ignore[arg-type]
                    self.remaining_params.append(param)

        self.remaining_params.extend(option_args)
        self.remaining_params.extend(minus_one_args)

        self.cmd_params = sorted(
            self.current_cmd.params,
            key=lambda x: isinstance(x, click.Option) and x.nargs != -1,
        )
        # print(f"{self.cmd_params = }")

    def parse_params(self, ctx: "Context", args: "List[str]") -> None:
        for param in self.cmd_params:
            if isinstance(param, click.Option) and not ctx.args and "--" not in args:
                options_name_list = param.opts + param.secondary_opts

                if param.is_bool_flag and any(i in args for i in options_name_list):
                    continue

                for option in options_name_list:
                    # We want to make sure if this parameter was called
                    # If we are inside a parameter that was called, we want to show only
                    # relevant choices
                    if (
                        option in args[param.nargs * -1 :]  # noqa: E203
                        and not param.count
                    ):
                        self.current_param = param
                        return

            elif (
                isinstance(param, click.Argument)
                and param in self.remaining_params
                # and not skip_arguments
                and (
                    ctx.params.get(param.name) is None  # type: ignore[arg-type]
                    or param.nargs == -1
                )
            ):
                # The current param will get updated
                self.current_param = param
                return


# @lru_cache(maxsize=3)
def currently_introspecting_args(
    cli: "MultiCommand", ctx: "Context", args: "List[str]"
) -> ParsingState:
    return ParsingState(cli, ctx, args)


class CompletionsProvider:
    """Provides Completion items based on the given parameters
    along with the styles provided to it.

    Keyword arguments:
    :param:`cli` - Group Repl CLI
    :param:`styles` - Dictionary of styles in the way of prompt-toolkit module,
        for arguments, options, etc.
    """

    __slots__ = (
        "cli",
        "styles",
    )

    def __init__(self, cli: "MultiCommand", styles: "Dict[str, str]") -> None:
        self.cli = cli
        self.styles = styles

    def get_completion_from_autocompletion_functions(
        self,
        param: "Parameter",
        autocomplete_ctx: "Context",
        args: "Iterable[str]",
        incomplete: str,
    ) -> "Generator[Completion, None, None]":
        if HAS_CLICK_V8:
            autocompletions = param.shell_complete(autocomplete_ctx, incomplete)
        else:
            autocompletions = param.autocompletion(  # type: ignore[attr-defined]
                autocomplete_ctx, args, incomplete
            )

        for autocomplete in autocompletions:
            if isinstance(autocomplete, tuple):
                yield Completion(
                    quotes(autocomplete[0]),
                    -len(incomplete),
                    display_meta=autocomplete[1],
                )

            elif HAS_CLICK_V8 and isinstance(
                autocomplete, click.shell_completion.CompletionItem
            ):
                yield Completion(quotes(autocomplete.value), -len(incomplete))

            elif isinstance(autocomplete, Completion):
                yield autocomplete

            else:
                yield Completion(quotes(str(autocomplete)), -len(incomplete))

    def get_completion_from_choices_click_le_7(
        self, param_type: "click.Choice", incomplete: str
    ) -> "Generator[Completion, None, None]":
        case_insensitive = not getattr(param_type, "case_sensitive", True)

        if case_insensitive:
            incomplete = incomplete.lower()

        for choice in param_type.choices:
            if case_insensitive:
                choice = choice.lower()

            if choice.startswith(incomplete):
                yield Completion(
                    quotes(choice),
                    -len(incomplete),
                    style=self.styles["argument"],
                    display=choice,
                )

    def get_completion_for_Path_types(
        self, incomplete: str
    ) -> "Generator[Completion, None, None]":

        if "*" in incomplete:
            return []  # type: ignore[return-value]

        # print(f'\n{incomplete = }')

        has_space = " " in incomplete
        # quoted = incomplete.count('"') % 2

        # print(f"\n{has_space = } {quoted = } {incomplete = }")

        search_pattern = incomplete.strip("\"'") + "*"
        # if has_space and not quoted:
        #     incomplete = f'"{incomplete}'

        temp_path_obj = Path(search_pattern)

        # quote = ""  # Quote thats used to surround the path in shell

        # if " " in incomplete:
        #     for i in incomplete:
        #         if i in ("'", '"'):
        #             quote = i
        #             break

        completion_txt_len = -len(incomplete) - has_space * 2  # + quoted * 2

        # print(f"{temp_path_obj = }")
        for path in temp_path_obj.parent.glob(temp_path_obj.name):
            #     if " " in path:
            #         if quote:
            #             path = quote + path
            #         else:
            #             if IS_WINDOWS:
            #                 path = repr(path).replace("\\\\", "\\")
            #     else:
            #         if IS_WINDOWS:
            #             path = path.replace("\\", "\\\\")

            path_str = str(path)

            if IS_WINDOWS:
                path_str = path_str.replace("\\\\", "\\")

            if " " in path_str:
                path_str = f'"{path_str}"'

                # if quoted:
                #     path_str = f'"{path_str}'
                # else:
                #     path_str = f'"{path_str}"'

                # completion_txt_len -= 1

            yield Completion(
                path_str,
                completion_txt_len,
                display=path.name,
            )

    def get_completion_for_Boolean_type(
        self, incomplete: str
    ) -> "Generator[Completion, None, None]":
        boolean_mapping = {
            "true": ("1", "true", "t", "yes", "y", "on"),
            "false": ("0", "false", "f", "no", "n", "off"),
        }

        for value, aliases in boolean_mapping.items():
            if any(alias.startswith(incomplete) for alias in aliases):
                yield Completion(
                    quotes(value), -len(incomplete), display_meta="/".join(aliases)
                )

    def get_completion_for_Range_types(
        self, param_type: "Union[click.IntRange, click.FloatRange]"
    ) -> "List[Completion]":
        clamp = " clamped" if param_type.clamp else ""
        display_meta = f"{param_type._describe_range()}{clamp}"

        return [Completion("-", display_meta=display_meta)]

    def get_completion_from_params(
        self,
        ctx: "Context",
        param: "Parameter",
        args: "Iterable[str]",
        incomplete: str,
    ) -> "List[Completion]":

        choices: "List[Completion]" = []
        param_type: "click.ParamType" = param.type

        if isinstance(param_type, _Range_types):
            return self.get_completion_for_Range_types(param_type)

        elif isinstance(param_type, click.Tuple):
            return [Completion("-", display=_type.name) for _type in param_type.types]

        # shell_complete method for click.Choice is intorduced in click-v8
        elif not HAS_CLICK_V8 and isinstance(param_type, click.Choice):
            choices.extend(
                self.get_completion_from_choices_click_le_7(param_type, incomplete)
            )

        elif isinstance(param_type, click.types.BoolParamType):
            choices.extend(self.get_completion_for_Boolean_type(incomplete))

        elif isinstance(param_type, (click.Path, click.File)):
            choices.extend(self.get_completion_for_Path_types(incomplete))

        elif getattr(param, AUTO_COMPLETION_PARAM, None) is not None:
            choices.extend(
                self.get_completion_from_autocompletion_functions(
                    param,
                    ctx,
                    args,
                    incomplete,
                )
            )

        return choices

    def get_completion_for_cmd_args(
        self,
        ctx: "Context",
        state: "ParsingState",
        args: "Iterable[str]",
        incomplete: "str",
    ) -> "Generator[Completion, None, None]":

        opt_aliases = []
        for param in state.current_cmd.params:  # type: ignore[union-attr]
            if (
                isinstance(param, click.Option) and not param.hidden
            ):  # type: ignore[union-attr]
                options_name_list = param.opts + param.secondary_opts

                if param.is_bool_flag and any(i in args for i in options_name_list):
                    continue

                for option in options_name_list:
                    if option.startswith(incomplete):
                        display_meta = ""

                        if param.default is not None:
                            display_meta += f" [Default={param.default}]"

                        if param.metavar is not None:
                            display = param.metavar
                        else:
                            display = option

                        opt_aliases.append(
                            Completion(
                                option,
                                -len(incomplete),
                                display=display,
                                display_meta=display_meta,
                                style=self.styles["option"],
                            )
                        )

        curr_param = state.current_param
        # print(f'{curr_param = }')

        if curr_param is not None:
            if isinstance(curr_param, click.Argument):
                yield from opt_aliases

            if not getattr(curr_param, "hidden", False):
                yield from self.get_completion_from_params(
                    ctx, curr_param, args, incomplete
                )

        else:
            yield from opt_aliases

        # a = curr_param is None
        # if not a or isinstance(curr_param, click.Argument):
        #   yield from lst1
        # if a and not getattr(curr_param, "hidden", False):
        #   yield from lst2

    def get_completions_for_command(
        self,
        ctx: "Context",
        state: "ParsingState",
        args: "Iterable[str]",
        incomplete: str,
    ) -> "Generator[Completion, None, None]":

        curr_group = state.current_group
        curr_cmd_exists = state.current_cmd is not None
        is_chain = getattr(curr_group, "chain", False)

        if curr_group is not None:
            if curr_cmd_exists:
                yield from self.get_completion_for_cmd_args(ctx, state, args, incomplete)

            if (not state.remaining_params and is_chain) or not curr_cmd_exists:
                for name in curr_group.list_commands(ctx):
                    command = curr_group.get_command(ctx, name)
                    if command.hidden:  # type: ignore[union-attr]
                        continue

                    elif name.startswith(incomplete):
                        yield Completion(
                            name,
                            -len(incomplete),
                            display_meta=getattr(command, "short_help", ""),
                        )
