from __future__ import annotations

from gettext import gettext as _
from typing import Any, Sequence

from click import Argument as CoreArgument
from click import Context
from click.exceptions import BadOptionUsage, NoSuchOption

from .._compat import (
    OptionParser,
    ParsingState,
    _Argument,
    _Option,
    normalize_opt,
    split_opt,
)
from ..globals_ import IS_CLICK_GE_8

_flag_needs_value = object()


def get_option_flags_sep(option_names: list[str]) -> str:
    """
    Returns the character to separate the given list of option names.

    Parameters
    ----------
    option_names
        List of option names

    Returns
    -------
    str
        Character that separates the option names
    """
    any_prefix_is_slash = any(split_opt(opt)[0] == "/" for opt in option_names)
    return ";" if any_prefix_is_slash else "/"


def order_option_names(option_names: Sequence[str]) -> list[str]:
    """
    Orders all the option names based on the length of their prefixes.

    Parameters
    ----------
    option_names
        List of option names

    Returns
    -------
    list[str]
        List of option names, ordered based on their prefix length
    """
    return sorted(option_names, key=lambda opt: len(split_opt(opt)[0]))


class ArgumentParamParser(_Argument):
    def process(
        self,
        value: str | Sequence[str | None] | None,
        state: ParsingState,
    ) -> None:
        if self.nargs > 1 and value is not None:
            holes = value.count(None)
            if holes == len(value):
                value = None  # responsible for adding None value if arg is empty

        state.opts[self.dest] = value  # type: ignore[index]
        state.order.append(self.obj)


class ReplOptionParser(OptionParser):
    """
    Subclass of :class:`~click.parser.OptionParser`, modified to
    fill in ``None`` values for empty values for parameters with
    ``nargs != 1``.

    Parameters
    ----------
    ctx
        The current click context object, constructed from the text currently
        in the prompt

    Reference
    ---------
    :class:`~click.parser.OptionParser`
    """

    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)

        for opt in ctx.command.params:
            opt.add_to_parser(self, ctx)

    def add_argument(self, obj: CoreArgument, dest: str | None, nargs: int = 1) -> None:
        self._args.append(ArgumentParamParser(obj=obj, dest=dest, nargs=nargs))

    def _process_args_for_options(self, state: ParsingState) -> None:
        while state.rargs:
            arg = state.rargs.pop(0)
            arglen = len(arg)

            # Double dashes always handled explicitly regardless of what
            # prefixes are valid.

            if arg == "--":
                # Dynamic attribute in click.Context object that helps to
                # denote to the completer class to stop generating
                # completions for option flags.
                self.ctx._double_dash_found = True  # type: ignore[union-attr]
                return

            elif arg[:1] in self._opt_prefixes and arglen > 1:
                self._process_opts(arg, state)

            elif self.allow_interspersed_args:
                state.largs.append(arg)

            else:
                state.rargs.insert(0, arg)
                return

    def _match_long_opt(
        self, opt: str, explicit_value: str | None, state: ParsingState
    ) -> None:
        if opt not in self._long_opt:
            from difflib import get_close_matches

            possibilities = get_close_matches(opt, self._long_opt)
            raise NoSuchOption(opt, possibilities=possibilities, ctx=self.ctx)

        option = self._long_opt[opt]
        if option.takes_value:
            if explicit_value is not None:
                state.rargs.insert(0, explicit_value)

            value = self._get_value_from_state(opt, option, state)

        elif explicit_value is not None:
            raise BadOptionUsage(opt, _(f"Option {opt!r} does not take a value."))

        else:
            value = None

        option.process(value, state)

    def _match_short_opt(self, arg: str, state: ParsingState) -> None:
        stop = False
        i = 1
        prefix = arg[0]
        unknown_options = []

        for ch in arg[1:]:
            opt = normalize_opt(f"{prefix}{ch}", self.ctx)
            option = self._short_opt.get(opt)
            i += 1

            if not option:
                if self.ignore_unknown_options:
                    unknown_options.append(ch)
                    continue

                raise NoSuchOption(opt, ctx=self.ctx)

            if option.takes_value:
                # Any characters left in arg?  Pretend they're the
                # next arg, and stop consuming characters of arg.
                if i < len(arg):
                    state.rargs.insert(0, arg[i:])
                    stop = True

                value = self._get_value_from_state(opt, option, state)

            else:
                value = None

            option.process(value, state)

            if stop:
                break

        if self.ignore_unknown_options and unknown_options:
            state.largs.append(f"{prefix}{''.join(unknown_options)}")

    def _get_value_from_state(
        self, option_name: str, option: _Option, state: ParsingState
    ) -> Any:
        nargs = option.nargs
        rargs_len = len(state.rargs)

        if rargs_len < nargs:
            if IS_CLICK_GE_8 and option.obj._flag_needs_value:
                # Option allows omitting the value.
                value = _flag_needs_value
            else:
                # Fills up missing values with None.
                if nargs == 1:
                    value = None
                else:
                    value = tuple(state.rargs + [None] * (nargs - rargs_len))
                state.rargs = []

        elif nargs == 1:
            next_rarg = state.rargs[0]

            if (
                IS_CLICK_GE_8
                and option.obj._flag_needs_value
                and isinstance(next_rarg, str)
                and next_rarg[:1] in self._opt_prefixes
                and len(next_rarg) > 1
            ):
                value = _flag_needs_value
            else:
                value = state.rargs.pop(0)
        else:
            value = tuple(state.rargs[:nargs])
            del state.rargs[:nargs]

        return value
