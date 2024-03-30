"""
Utilities to facilitate the functionality of the module.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from difflib import get_close_matches
from functools import lru_cache
from typing import Any, Iterable

import click
from click import Command, Context, MultiCommand, Parameter
from click.parser import split_opt
from prompt_toolkit.formatted_text import StyleAndTextTuples
from typing_extensions import Literal

from ._globals import RANGE_TYPES  # , StyleAndTextTuples
from .parser import (
    Incomplete,
    InfoDict,
    ReplParsingState,
    _resolve_incomplete,
    _resolve_repl_parsing_state,
)
from .proxies import _create_proxy_command

CompletionStyleDictKeys = Literal[
    "internal-command", "command", "multicommand", "argument", "option", "parameter"
]


def append_classname_to_all_tokens(
    tokens_list: StyleAndTextTuples, classes: Iterable[str] = []
) -> StyleAndTextTuples:
    if not classes:
        return tokens_list

    res: StyleAndTextTuples = []

    for token, *_ in tokens_list:
        res.append((f"{token},{','.join(classes)}", *_))  # type:ignore[arg-type]

    return res


def options_flags_joiner(
    items: Iterable[str], item_token: str, sep_token: str, sep: str = " "
) -> StyleAndTextTuples:
    if not items:
        return []

    sep_elem = (sep_token, sep)
    iterator = iter(items)
    res: StyleAndTextTuples = [(item_token, next(iterator))]

    for item in iterator:
        res.append(sep_elem)
        res.append((item_token, item))

    return res


def get_token_type(obj: click.Command | click.Parameter) -> CompletionStyleDictKeys:
    if isinstance(obj, click.Parameter):
        if isinstance(obj, click.Argument):
            return "argument"

        elif isinstance(obj, click.Option):
            return "option"

        else:
            return "parameter"

    elif isinstance(obj, click.MultiCommand):
        return "multicommand"

    return "command"


def _quotes(text: str) -> str:
    if " " in text and text[0] != '"' != text[-1]:
        text = text.strip('"').replace('"', '\\"')
        return f'"{text}"'

    return text


def _expand_envvars(text: str) -> str:
    return os.path.expandvars(os.path.expanduser(text))


def _is_help_option(param: click.Option) -> bool:
    return (
        param.is_flag
        and not param.expose_value
        and param.is_eager
        and "--help" in param.opts
        and bool(
            get_close_matches(
                param.help or "", ["Show this message and exit."], cutoff=0.5
            )
        )
    )


def print_error(text: str) -> None:
    # Prints the given text to stderr, in red colour.
    click.secho(text, color=True, err=True, fg="red")


def is_param_value_incomplete(
    ctx: Context, param_name: str | None, check_if_tuple_has_none: bool = True
) -> bool:
    # Checks whether the given name of that parameter
    # doesn't recieve it's values completely.
    if param_name is None:
        return False

    value = ctx.params.get(param_name, None)
    return value in (None, ()) or (
        check_if_tuple_has_none and isinstance(value, tuple) and None in value
    )


def get_option_flag_sep(options: list[str]) -> str:
    any_prefix_is_slash = any(split_opt(opt)[0] == "/" for opt in options)
    return ";" if any_prefix_is_slash else "/"


def join_options(options: list[str]) -> tuple[list[str], str]:
    # Same implementation as click.formatting.join_options function, but much simpler.
    return sorted(options, key=len), get_option_flag_sep(options)


def _get_group_ctx(ctx: Context) -> Context:
    # If there's a parent context object and its command type is click.MultiCommand,
    # we return its parent context object. A parent context object should be
    # available most of the time. If not, then we return the original context object.

    if ctx.parent is not None and not isinstance(ctx.command, click.MultiCommand):
        ctx = ctx.parent

    ctx.protected_args = []
    return ctx


def _get_visible_subcommands(
    ctx: Context,
    multicommand: MultiCommand,
    incomplete: str,
    show_hidden_commands: bool = False,
) -> Generator[tuple[str, Command], None, None]:
    # Get all the subcommands whose name starts with the given
    # 'incomplete' prefix string.

    for command_name in multicommand.list_commands(ctx):
        if not command_name.startswith(incomplete):
            continue

        subcommand = multicommand.get_command(ctx, command_name)

        if subcommand is None or (subcommand.hidden and not show_hidden_commands):
            # We skip if there's no command found or it's a hidden command
            # and show_hidden_commands is False.
            continue

        yield command_name, subcommand


@lru_cache(maxsize=128)
def get_info_dict(
    obj: Context | Command | Parameter | click.ParamType,
) -> InfoDict:
    """
    Similar to the 'get_info_dict' method implementation in click objects,
    but it only retrieves the essential attributes required to
    differentiate between different 'ReplParsingState' objects.

    Parameters
    ----------
    obj : click.Context | click.Command | click.Parameter | click.ParamType
        Click object for which the info dict needs to be generated.

    Returns
    -------
    InfoDict
        Dictionary that holds crucial details about the given click object
        that can be used to uniquely identify it.
    """

    if isinstance(obj, click.Context):
        return {
            "command": get_info_dict(obj.command),
            "params": obj.params,
        }

    info_dict: InfoDict = {}

    if isinstance(obj, click.Command):
        ctx = click.Context(obj)

        info_dict.update(
            name=obj.name,
            params=tuple(get_info_dict(param) for param in obj.get_params(ctx)),
            callback=obj.callback,
        )

        if isinstance(obj, click.MultiCommand):
            commands = {}

            for name in obj.list_commands(ctx):
                command = obj.get_command(ctx, name)

                if command is None:
                    continue

                commands[name] = get_info_dict(command)

            info_dict.update(commands=commands, chain=obj.chain)

    elif isinstance(obj, click.Parameter):
        info_dict.update(
            name=obj.name,
            param_type_name=obj.param_type_name,
            opts=obj.opts,
            secondary_opts=obj.secondary_opts,
            type=get_info_dict(obj.type),
            required=obj.required,
            nargs=obj.nargs,
            multiple=obj.multiple,
        )

        if isinstance(obj, click.Option):
            info_dict.update(
                is_flag=obj.is_flag,
                flag_value=obj.flag_value,
                count=obj.count,
                hidden=obj.hidden,
            )

    elif isinstance(obj, click.ParamType):
        param_type = type(obj).__name__.partition("ParamType")[0]
        param_type = param_type.partition("ParameterType")[0]

        # Custom subclasses might not remember to set a name.
        name = getattr(obj, "name", param_type)
        info_dict.update(param_type=param_type, name=name)

        if isinstance(obj, click.types.FuncParamType):
            info_dict["func"] = obj.func

        elif isinstance(obj, click.Choice):
            info_dict["choices"] = obj.choices
            info_dict["case_sensitive"] = obj.case_sensitive

        elif isinstance(obj, click.DateTime):
            info_dict["formats"] = obj.formats

        elif isinstance(obj, RANGE_TYPES):
            info_dict.update(
                min=obj.min,
                max=obj.max,
                min_open=getattr(obj, "min_open", False),
                max_open=getattr(obj, "max_open", False),
                clamp=obj.clamp,
            )

        elif isinstance(obj, click.File):
            info_dict.update(mode=obj.mode, encoding=obj.encoding)

        elif isinstance(obj, click.Path):
            info_dict.update(
                exists=obj.exists,
                file_okay=obj.file_okay,
                dir_okay=obj.dir_okay,
                writable=obj.writable,
                readable=obj.readable,
                allow_dash=obj.allow_dash,
            )

        elif isinstance(obj, click.Tuple):
            info_dict["types"] = tuple(get_info_dict(t) for t in obj.types)

    return info_dict


@lru_cache(maxsize=3)
def _generate_next_click_ctx(
    multicommand: MultiCommand,
    parent_ctx: Context,
    args: tuple[str, ...],
    proxy: bool = False,
    **ctx_kwargs: dict[str, Any],
) -> tuple[Context, Command | None]:
    if not args:
        return parent_ctx, None

    # Since the resolve_command method only accepts string arguments in a
    # list format, we explicitly convert args into a list.
    _args = list(_expand_envvars(i) for i in args)

    name, cmd, _args = multicommand.resolve_command(parent_ctx, _args)

    if cmd is None:
        return parent_ctx, None

    if proxy:
        # When using click.parser.OptionParser.parse_args, incomplete
        # string arguments that do not meet the nargs requirement of
        # the current parameter are normally ignored. However, in our
        # case, we want to handle these incomplete arguments. To
        # achieve this, we use a proxy command object to modify
        # the command parsing behavior in click.
        with _create_proxy_command(cmd) as _cmd:
            ctx = _cmd.make_context(name, _args, parent=parent_ctx, **ctx_kwargs)

    else:
        ctx = cmd.make_context(name, _args, parent=parent_ctx, **ctx_kwargs)

    return ctx, cmd


@lru_cache(maxsize=3)
def _resolve_context(ctx: Context, args: tuple[str, ...], proxy: bool = False) -> Context:
    while args:
        command = ctx.command

        if isinstance(command, click.MultiCommand):
            if not command.chain:
                ctx, cmd = _generate_next_click_ctx(
                    command,
                    ctx,
                    args,
                    proxy=proxy,
                )

                if cmd is None:
                    return ctx

            else:
                while args:
                    sub_ctx, cmd = _generate_next_click_ctx(
                        command,
                        ctx,
                        args,
                        proxy=proxy,
                        allow_extra_args=True,
                        allow_interspersed_args=False,
                    )

                    if cmd is None:
                        return ctx

                    args = tuple(sub_ctx.args)
                ctx = sub_ctx
            args = tuple(ctx.protected_args + ctx.args)

        else:
            break

    return ctx


@lru_cache(maxsize=3)
def _resolve_state(
    ctx: Context, document_text: str
) -> tuple[Context, ReplParsingState, Incomplete]:
    """
    Resolves the parsing state of the arguments in the REPL prompt.

    Parameters
    ----------
    ctx : click.Context
        The current click context object of the parent group.

    document_text : str
        Text that's currently entered in the prompt.

    Returns
    -------
    tuple[Context, ReplParsingState, Incomplete]
        Returns the appropriate `click.Context` constructed from parsing
        the given input from prompt, current `ReplParsingState` object,
        and the `Incomplete` object that holds the incomplete data that
        requires suggestions.
    """
    args, incomplete = _resolve_incomplete(document_text)
    parsed_ctx = _resolve_context(ctx, args, proxy=True)
    state = _resolve_repl_parsing_state(ctx, parsed_ctx, args)

    return parsed_ctx, state, incomplete
