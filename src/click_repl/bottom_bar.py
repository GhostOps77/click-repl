"""
Utility for the Bottom bar of the REPL.
"""

from __future__ import annotations

import typing as t

import click
from click import Parameter
from click.types import FloatRange, IntRange, ParamType
from prompt_toolkit.formatted_text import OneStyleAndTextTuple as Token
from prompt_toolkit.formatted_text import StyleAndTextTuples as ListOfTokens
from typing_extensions import TypedDict

from ._formatting import Marquee, TokenizedFormattedText
from ._globals import HAS_CLICK_GE_8, ISATTY, RANGE_TYPES
from .parser import ReplParsingState
from .utils import append_classname_to_all_tokens, is_param_value_incomplete

if t.TYPE_CHECKING:
    from .core import ReplContext


__all__ = ["BottomBar"]


class ParamInfo(TypedDict):
    name: Token
    type_info: ListOfTokens
    nargs_info: ListOfTokens


def _describe_click_range_paramtype(param_type: IntRange | FloatRange) -> str:
    """
    Returns the metavar of the range-type :class:`~click.types.ParamType` type objects.

    Parameter
    ---------
    param_type
        :class:`~click.types.ParamType` object, whose metavar should be generated.

    Returns
    -------
    str
        Metavar that describes about the given range-like
        :class:`~click.types.ParamType` object.
    """

    if HAS_CLICK_GE_8:
        res = param_type._describe_range()

    elif param_type.min is None:
        res = f"x<={param_type.max}"

    elif param_type.max is None:
        res = f"x>={param_type.min}"

    else:
        res = f"{param_type.min}<=x<={param_type.max}"

    clamp = " clamped" if param_type.clamp else ""
    return res + clamp  # type:ignore[no-any-return]


class BottomBar:
    """
    Toolbar class to manage the text in the bottom toolbar.

    Parameters
    ----------
    show_hidden_params
        Determines whether to display hidden params at bottom bar.
    """

    def __init__(
        self,
        show_hidden_params: bool = False,
    ) -> None:
        """
        Initialize the `BottomBar` class.
        """

        self.state: ReplParsingState | None = None
        """Current Repl parsing state object."""

        self._recent_formatted_text: ListOfTokens | Marquee = []
        """Stores recently generated text for bottom bar as cache."""

        self.show_hidden_params = show_hidden_params
        """Flag that determines whether to display hidden params at bottom bar"""

        self.current_repl_ctx: ReplContext | None = None
        """Context object of the current Repl session."""

        self.parent_token_class_name: str = "bottom-bar"
        """
        Parent class name for tokens that are related to :class:`~.BottomBar`."""

    def __call__(self) -> ListOfTokens:
        return self.get_formatted_text()

    def clear(self) -> None:
        """Clears the bottom bar's content."""
        self._recent_formatted_text = []

    def get_formatted_text(self) -> ListOfTokens:
        """
        Gives the next chunk of text that's sliced from :attr:`~.Marquee.text` object
        that needs to be displayed in bottom bar.

        Returns
        -------
        ListOfTokens
            Next chunk of text that should be displayed in bottom bar.
        """
        if isinstance(self._recent_formatted_text, Marquee):
            return self._recent_formatted_text.get_current_text_chunk()

        return self._recent_formatted_text

    def reset_state(self) -> None:
        """Reset the current parsing state object and content in bottom bar."""
        self.state = None
        self.clear()

    def update_state(self, state: ReplParsingState) -> None:
        """
        Updates the current Repl parsing state object in :class:`.BottomBar`.

        Parameters
        ----------
        state
            Current parsing state of the prompt.
        """
        if not ISATTY or state is None or state == self.state:
            return

        self.state = state
        self._recent_formatted_text = self.make_formatted_text()

    def get_group_metavar_template(self) -> Marquee:
        """
        Gets the metavar to describe the CLI Group, indicating whether
        it is a :class:`~click.Group` or a :class:`~click.Command`.

        Returns
        -------
        :class:`.Marquee`
            Pre-defined set of metavar tokens for both :attr:`.Marquee.prefix`
            and :attr:`.Marquee.text` attributes.
        """

        state = self.state
        assert state is not None, "state cannot be None"

        current_group = state.current_group

        current_group_name = current_group.name
        if current_group_name is None:
            current_group_name = "..."

        prefix: ListOfTokens = [
            ("multicommand.type", "Group"),
            ("space", " "),
            ("multicommand.name", current_group_name),
            ("symbol", ":"),
            ("space", " "),
        ]

        if not current_group.list_commands(state.current_ctx):
            # Empty string if there are no subcommands.
            return Marquee([], prefix)

        content: ListOfTokens = []

        if getattr(current_group, "chain", False):
            # Metavar for chained group.
            content = [
                ("multicommand.metavar", "COMMAND1"),
                ("space", " "),
                ("symbol.bracket", "["),
                ("multicommand.metavar", "ARGS"),
                ("symbol.bracket", "]"),
                ("symbol.ellipsis", "..."),
                ("space", " "),
                ("symbol.bracket", "["),
                ("multicommand.metavar", "COMMAND2"),
                ("space", " "),
                ("symbol.bracket", "["),
                ("multicommand.metavar", "ARGS"),
                ("symbol.bracket", "]"),
                ("symbol.ellipsis", "..."),
                ("symbol.bracket", "]"),
                ("symbol.ellipsis", "..."),
            ]

        else:
            # Metavar for non-chained group.
            content = [
                ("multicommand.metavar", "COMMAND"),
                ("space", " "),
                ("symbol.bracket", "["),
                ("multicommand.metavar", "ARGS"),
                ("symbol.bracket", "]"),
                ("symbol.ellipsis", "..."),
            ]

        return Marquee(
            TokenizedFormattedText(content, self.parent_token_class_name),
            TokenizedFormattedText(prefix, self.parent_token_class_name),
        )

    def get_param_usage_state_token(self, param: Parameter) -> str:
        """
        Returns a token class name that describes the usage state of a
        parameter in the context of a REPL.

        Parameters
        ----------
        param
            The parameter for which to determine it's usage state.

        Returns
        -------
        str
            The string describing the given ``param``'s usage state.
        """
        state = self.state
        assert state is not None, "state cannot be None"

        if param == state.current_param:
            usage_state = "inuse"

        elif not is_param_value_incomplete(state.current_ctx, param):
            usage_state = "used"

        else:
            usage_state = "unused"

        if (
            any(getattr(param, attr, False) for attr in ("count", "multiple"))
            # or param in state.remaining_params
        ):
            # Counters, and Multiple-type Options can be supplied multiple times.
            # So they're displayed without special formatting.
            # # Same goes for Parameters awaiting for values.
            usage_state = "unused"

        return "parameter." + usage_state

    def get_param_name_token(self, param: Parameter) -> Token:
        """
        Returns the token name accordingly to the given ``param``'s type.

        Parameters
        ----------
        param
            The parameter for which to determine it's usage state.

        Returns
        -------
        Token
            Token that represents the given ``param``'s name.
        """
        if isinstance(param, click.Argument):
            token_name = "parameter.argument.name"

        elif isinstance(param, click.Option):
            token_name = "parameter.option.name"

        else:
            token_name = f"parameter.{type(param).__name__.lower()}.name"

        param_name = param.name

        if param_name is None:
            param_name = "..."

        return (
            f"{token_name},{self.get_param_usage_state_token(param)}",
            param_name.replace("_", "-"),
        )

    def get_param_tuple_type_info_tokens(self, param: Parameter) -> ListOfTokens:
        assert self.state is not None, "state cannot be None"

        if param.name is None:
            return []

        param_type: click.Tuple = param.type  # type:ignore[assignment]
        param_values: tuple[str | None, ...] = self.state.current_ctx.params[param.name]

        found_current_type_in_tuple = False
        type_info_tokens: ListOfTokens = []

        for type_, value_in_ctx in zip(param_type.types, param_values):
            res = self.get_param_type_info_tokens(param, type_)

            if not res:
                res = [
                    ("symbol.bracket", "<"),
                    ("parameter.type.string", "text"),
                    ("symbol.bracket", ">"),
                ]

            if value_in_ctx is not None:
                usage_state = "parameter.type.used"

            elif not found_current_type_in_tuple:
                usage_state = "parameter.type.inuse"
                found_current_type_in_tuple = True

            else:
                usage_state = "parameter.type.unused"

            type_info_tokens += [
                (f"{token.rsplit(',', 1)[0]},{usage_state}", val, *_)
                for token, val, *_ in res
            ]
            type_info_tokens.append(("space", " "))

        type_info_tokens.pop()
        return type_info_tokens

    def get_param_type_info_tokens(
        self, param: Parameter, param_type: ParamType
    ) -> ListOfTokens:
        """

        Parameters
        ----------
        param
            The parameter for which to determine it's usage state.

        param_type
            The :class:`~click.types.ParamType` of the given ``param``.

        Returns
        -------
        ListOfTokens
            Tokens that represents the given ``param``'s type.
        """
        assert self.state is not None, "state cannot be None"

        type_info_tokens: ListOfTokens = []

        if isinstance(param_type, click.Tuple):
            return self.get_param_tuple_type_info_tokens(param)

        if not is_param_value_incomplete(self.state.current_ctx, param):
            usage_state = "parameter.type.used"

        else:
            usage_state = "parameter.type.inuse"

        if isinstance(param_type, RANGE_TYPES):
            range_num_type = (
                "integer" if isinstance(param_type, click.IntRange) else "float"
            )

            type_info_tokens += [
                (f"parameter.type.range.{range_num_type}", param_type.name),
                ("space", " "),
                (
                    "parameter.type.range.descriptor",
                    _describe_click_range_paramtype(param_type),
                ),
            ]

        elif param_type not in (click.STRING, click.UNPROCESSED):
            param_type_name = param_type.name or type(param_type).__name__.lower()

            type_info_tokens.append(
                (f"parameter.type.{param_type_name}", param_type.name or f"{param_type}")
            )

        if type_info_tokens:
            type_info_tokens = [
                ("symbol.bracket", "<"),
                *type_info_tokens,
                ("symbol.bracket", ">"),
            ]

            type_info_tokens = append_classname_to_all_tokens(
                type_info_tokens, [usage_state]
            )

        return type_info_tokens

    def get_param_nargs_info_tokens(
        self, param: Parameter, param_info: ParamInfo
    ) -> ListOfTokens:
        type_info = param_info["type_info"]

        if param.nargs == 1:
            return type_info

        usage_state = self.get_param_usage_state_token(param)

        if isinstance(param.type, click.Tuple):
            nargs_info = [("symbol.bracket", "("), *type_info, ("symbol.bracket", ")")]

        elif param.nargs == -1:
            nargs_info = type_info.copy()

            if nargs_info:
                nargs_info.append((f"space,{usage_state}", " "))

            nargs_info.append((f"ellipsis,{usage_state}", "..."))

        elif param.nargs > 1:
            assert self.state is not None, "state cannot be None"

            # Calculate the number of non-None values received for the parameter.
            param_values: list[str] = (
                self.state.current_ctx.params[param.name] or []  # type:ignore[index]
            )

            no_of_values_received = sum(1 for i in param_values if i is not None)

            nargs_info = [
                *type_info,
                (f"symbol,{usage_state}", "("),
                (f"parameter.nargs.counter,{usage_state}", f"{no_of_values_received}"),
                (f"symbol,{usage_state}", "/"),
                (f"parameter.nargs.counter,{usage_state}", f"{param.nargs}"),
                (f"symbol,{usage_state}", ")"),
            ]

        return nargs_info

    def format_metavar_tokens_for_param_with_nargs(
        self, param: Parameter, param_info: ParamInfo
    ) -> ListOfTokens:
        param_name = param_info["name"]
        nargs_info = param_info["nargs_info"]

        res: ListOfTokens = [param_name]

        if not nargs_info:
            return res

        usage_state = self.get_param_usage_state_token(param)

        if not isinstance(param.type, click.Tuple):
            res.append((f"space,{usage_state}", " "))

        res += nargs_info
        return res

    def get_param_info_tokens(self, param: Parameter) -> ListOfTokens:
        assert self.state is not None, "state cannot be None"

        param_info: ParamInfo = {
            "name": self.get_param_name_token(param),
            "type_info": [],
            "nargs_info": [],
        }

        if self.state.current_param == param:
            # Displaying detailed information only for the current parameter
            # in the bottom bar, to save space.

            param_info["type_info"] = self.get_param_type_info_tokens(param, param.type)
            param_info["nargs_info"] = self.get_param_nargs_info_tokens(param, param_info)

        return self.format_metavar_tokens_for_param_with_nargs(param, param_info)

    def make_formatted_text(self) -> Marquee:
        """
        Constructs tokens list to describe the current
        :class:`~click_repl.parser.ReplParsingState` of input in prompt.

        Returns
        -------
        click_repl._formatting.Marquee
            :class:`~click_repl._formatting.Marquee` object that needs to be display
            the updated info about the current
            :class:`~click_repl.parser.ReplParsingState`.
        """
        state = self.state

        if state is None:
            return []  # type:ignore[return-value]

        current_command = state.current_command

        if current_command is None:
            # If there is no command currently entered in the REPL,
            # the function returns the metavar template of the
            # parent/CLI/current Group.

            return self.get_group_metavar_template()

        if isinstance(current_command, click.Group):
            command_type = "multicommand"
            command_type_metavar = type(current_command).__name__

        else:
            command_type = "command"
            command_type_metavar = "Command"

        current_command_name = current_command.name
        if current_command_name is None:
            current_command_name = "..."

        prefix: ListOfTokens = [
            (f"{command_type}.type", command_type_metavar),
            ("space", " "),
            (f"{command_type}.name", current_command_name),
        ]

        formatted_params_info = []
        unique_params = {param.name: param for param in current_command.params}.values()

        for param in unique_params:
            if not getattr(param, "hidden", False) or (
                param == state.current_param and self.show_hidden_params
            ):
                # Display all the non-hidden parameters, except if the hidden param
                # is the current parameter.

                formatted_params_info += self.get_param_info_tokens(param)
                formatted_params_info.append(("space", " "))

        if formatted_params_info:
            formatted_params_info.pop()
            prefix += [
                ("symbol,misc.bold", ":"),
                ("space", " "),
            ]

        return Marquee(
            TokenizedFormattedText(formatted_params_info, self.parent_token_class_name),
            prefix=TokenizedFormattedText(prefix, self.parent_token_class_name),
        )

    def display_exception(self, exc: Exception) -> None:
        """
        Displays the given ``exc`` :class:`~Exception` object in the bottom bar.

        Parameters
        ----------
        exc
            The :class:`~Exception` object that needs to be displayed.
        """
        self._recent_formatted_text = Marquee(
            TokenizedFormattedText(
                [
                    ("error.exception-class-name", type(exc).__name__),
                    ("symbol,error", ":"),
                    ("space,error", " "),
                    ("error.message", str(exc)),
                ],
                self.parent_token_class_name,
            )
        )
