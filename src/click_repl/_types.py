from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Dict, ItemsView, List, Optional, Tuple

from click import Context
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import OneStyleAndTextTuple as Token
from prompt_toolkit.formatted_text import StyleAndTextTuples as ListOfTokens
from typing_extensions import Literal, TypeAlias, TypedDict

if TYPE_CHECKING:
    from ._internal_cmds import InternalCommandSystem
    from .bottom_bar import BottomBar
    from .core import ReplContext
    from .parser import ReplParsingState


InfoDict: TypeAlias = Dict[str, Any]

_CompletionStyleDictKeys = Literal[
    "internal-command", "command", "group", "argument", "option", "parameter"
]


CallableNone: TypeAlias = Callable[[], None]
InternalCommandDict: TypeAlias = Dict[str, Tuple[CallableNone, str]]
InfoTable: TypeAlias = Dict[Tuple[CallableNone, str], List[str]]

_PromptSession: TypeAlias = PromptSession[Dict[str, Any]]

_REPL_PARSING_STATE_KEY: TypeAlias = Tuple[
    Optional[InfoDict], Optional[InfoDict], Optional[InfoDict], Tuple[InfoDict, ...]
]


class ReplContextInfoDict(TypedDict):
    group_ctx: Context
    prompt_kwargs: dict[str, Any]
    session: _PromptSession | None
    internal_command_system: InternalCommandSystem
    parent: ReplContext | None
    _history: list[str]
    current_state: ReplParsingState | None
    bottombar: BottomBar | None


class ParamInfo(TypedDict):
    name: Token
    type_info: ListOfTokens
    nargs_info: ListOfTokens


@dataclass
class CompletionDisplayStyleDict:
    completion_style: str = ""
    selected_style: str = ""


CompletionStyleDict: TypeAlias = Dict[
    _CompletionStyleDictKeys, CompletionDisplayStyleDict
]


@dataclass
class PrefixTable:
    internal: str | None
    system: str | None

    def items(self) -> ItemsView[str, str | None]:
        return self.__dict__.items()


__all__ = [
    "Token",
    "ListOfTokens",
    "InfoDict",
    "_CompletionStyleDictKeys",
    "CallableNone",
    "InternalCommandDict",
    "InfoTable",
    "ParamInfo",
    "CompletionDisplayStyleDict",
    "CompletionStyleDict",
    "PrefixTable",
]
