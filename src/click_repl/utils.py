import typing as t
from functools import lru_cache

import click
from click.parser import split_opt

from . import bottom_bar
from ._globals import _RANGE_TYPES
from ._globals import HAS_CLICK8
from .parser import currently_introspecting_args
from .parser import get_args_and_incomplete_from_args
from .proxies import create_proxy_object

if t.TYPE_CHECKING:
    from typing import Any, Dict, Optional, Tuple, Union

    from click import Command, Context, Parameter

    from .parser import ArgsParsingState


# def flatten_click_tuple(tuple_type: "click.Tuple") -> "Generator[Any, None, None]":
#     """Unpacks types provided through `click.Tuple` into a single list

#     Keyword arguments:
#     :param `tuple_type`: `click.Tuple` type that has collection
#         of other types
#     Yield: Each type inside the Tuple
#     """

#     for val in tuple_type.types:
#         if isinstance(val, click.Tuple):
#             for item in flatten_click_tuple(val):
#                 yield item
#         else:
#             yield val


def is_param_value_incomplete(ctx: "Context", param_name: "Optional[str]") -> bool:
    """
    Checks whether the given value of the parameter contains `None` values.

    Parameters
    ----------
    ctx : click.Context
        The click context object from which the value of the parameter should be checked.

    param_name : str or None.
        The name of the parameter to check for its value in the
        `click.Context.params` dictionary.

        If its None, then the parameter don't want to expose itself.

    Returns
    -------
    bool
        A boolean value indicating the presence of `None` in the given `value`
        of the parameter.
    """

    if param_name is None:
        return False

    value = ctx.params.get(param_name, None)  # type: ignore[arg-type]
    return value in (None, ()) or (isinstance(value, tuple) and None in value)


def join_options(options: "t.List[str]") -> "t.Tuple[t.List[str], str]":
    """
    Joins a list of option strings and returns them in the form
    `(formatted_string, any_prefix_is_slash)` where the second
    item in the tuple is a flag that indicates if any of the
    option prefixes was a slash.

    Parameters
    ----------
    options : list of strings.
        A list containing all the flags of an option.

    Returns
    -------
    A Tuple containing:
      - list of strings
            Sorted list of the option flags.
      - str
          The separator used to specify the flags for the option separately.
    """

    any_prefix_is_slash = any(split_opt(opt)[0] == "/" for opt in options)
    options.sort(key=len)

    return options, ";" if any_prefix_is_slash else "/"


def get_group_ctx(ctx: "Context") -> "Context":
    """
    Returns the parent/CLI Group context object by obtaining
    it from the given `click.Context` object.

    Parameters
    ----------
    ctx : click.Context
        A `click.Context` object to obtain the root/parent
        context object from.

    Returns
    -------
    click.Context
        The click context object that belongs to the root/parent/CLI Group.
    """

    # If there's a parent context object and its command type is click.MultiCommand,
    # we return its parent context object. A parent context object should be
    # available most of the time. If not, then we return the original context object.

    if ctx.parent is not None and not isinstance(ctx.command, click.MultiCommand):
        return ctx.parent

    return ctx


@lru_cache(maxsize=3)
def _resolve_context(ctx: "Context", _args: "Tuple[str, ...]") -> "Context":
    """
    Produce the context hierarchy starting with the command and
    traversing the complete arguments. This only follows the commands,
    it doesn't trigger input prompts or callbacks.

    Code analogues to `click.shell_completion._resolve_context` if
    click >= v8 is available, else `click._bashcomplete.resolve_ctx`.

    Parameters
    ----------
    ctx : click.Context
        The `click.Context` object of the CLI group.

    args : tuple of strings.
        A tuple of completed string arguments before the incomplete string value.

    Returns
    -------
    click.Context
        A click context object that contains information about the current command
        and parameter based on the input provided in the prompt.
    """

    # Since the resolve_command method only accepts string arguments in a
    # list format, we explicitly convert _args into a list.

    args = list(_args)

    while args:
        command = ctx.command

        if isinstance(command, click.MultiCommand):
            if not command.chain:
                name, cmd, args = command.resolve_command(ctx, args)

                if cmd is None:
                    return ctx

                # When using click.parser.OptionParser.parse_args, incomplete
                # string arguments that do not meet the nargs requirement of
                # the current parameter are normally ignored. However, in our
                # case, we want to handle these incomplete arguments. To
                # achieve this, we use a proxy command object to modify
                # the command parsing behavior in click.

                ctx = create_proxy_object(cmd).make_context(
                    name, args, parent=ctx  # , resilient_parsing=True
                )

                args = ctx.protected_args + ctx.args

            else:
                while args:
                    name, cmd, args = command.resolve_command(ctx, args)

                    if cmd is None:
                        return ctx

                    # Similarly to the previous case, we modify the behavior
                    # of the parse_args method for the cmd variable used to
                    # call the make_context method here.

                    sub_ctx = create_proxy_object(cmd).make_context(
                        name,
                        args,
                        parent=ctx,
                        allow_extra_args=True,
                        allow_interspersed_args=False,
                        # resilient_parsing=True
                    )
                    args = sub_ctx.args

                ctx = sub_ctx
                args = sub_ctx.protected_args + sub_ctx.args
        else:
            break

    return ctx


def get_info_dict(
    obj: "Union[Context, Command, Parameter, click.ParamType]",
) -> "Dict[str, Any]":
    """
    Retrieves information about the given click object.

    This function retrieves information about the provided click objects.
    The `to_info_dict` method was introduced in click v8, but to ensure
    compatibility with earlier versions, this code implements the logic
    manually.

    If the current click version is >=8, the `to_info_dict` method is used
    to obtain the information.

    Parameters
    ----------
    obj : click.Context, click.Command, click.Parameter, or click.ParamType
        The click object from which to retrieve the data.

    Returns
    -------
    A dictionary containing the data about the given object `obj`.
    """

    if isinstance(obj, click.Command):
        ctx = click.Context(obj)

    if HAS_CLICK8:
        if isinstance(obj, click.Command):
            return obj.to_info_dict(ctx)  # type: ignore[no-any-return]

        return obj.to_info_dict()  # type: ignore[no-any-return]

    # Following code contains the manual implementation of the
    # 'to_info_dict' method.
    info_dict: "Dict[str, Any]" = {}

    if isinstance(obj, click.Context):
        return {
            "command": get_info_dict(obj.command),
            "info_name": obj.info_name,
            "allow_extra_args": obj.allow_extra_args,
            "allow_interspersed_args": obj.allow_interspersed_args,
            "ignore_unknown_options": obj.ignore_unknown_options,
            "auto_envvar_prefix": obj.auto_envvar_prefix,
        }

    if isinstance(obj, click.Command):
        info_dict.update(
            name=obj.name,
            params=[get_info_dict(param) for param in obj.get_params(ctx)],
            help=obj.help,
            epilog=obj.epilog,
            short_help=obj.short_help,
            hidden=obj.hidden,
            deprecated=obj.deprecated,
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
            default=obj.default,
            envvar=obj.envvar,
        )

        if isinstance(obj, click.Option):
            info_dict.update(
                help=obj.help,
                prompt=obj.prompt,
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
            info_dict["case_sensitive"] = getattr(obj, "case_sensitive", True)

        elif isinstance(obj, click.DateTime):
            info_dict["formats"] = obj.formats

        elif isinstance(obj, _RANGE_TYPES):
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
            info_dict["types"] = [get_info_dict(t) for t in obj.types]

    return info_dict


@lru_cache(maxsize=3)
def _resolve_state(
    ctx: "Context", document_text: str
) -> "Tuple[Context, ArgsParsingState, str]":
    """
    Resolves the parsing state of the arguments in the REPL prompt.

    Used in both the `click_repl.completer.ClickCompleter` class
    and `click_repl.validator.ClickValidator` class to execute once
    and use the cached result of the currently parsing state of the
    arguments in the other class.

    Parameters
    ----------
    ctx : click.Context
        A `click.Context` of the parent/CLI Group.

    document_text : str
        The string that is currently in the REPL prompt.

    Returns
    -------
    A Tuple containing the following elements:
      - click.Context
          A `click.Context` object that contains information about the
          current command and its parameters based on the input in the REPL prompt.

      - click_repl.parser.ArgsParsingState
          A `click_repl.parser.ArgsParsingState` object that contains information
          about the parsing state of the parameters of the current command.

      - str
          An unfinished string in the REPL prompt that requires further input
          or completion.

    Raises
    ------
    click.exceptions.ClickException
        If an error occurs during command line argument parsing.
    """

    args, incomplete = get_args_and_incomplete_from_args(document_text)
    parsed_ctx = _resolve_context(ctx, args)

    state = currently_introspecting_args(ctx, parsed_ctx, args)

    bottom_bar.BOTTOMBAR.update_state(state)

    return parsed_ctx, state, incomplete
