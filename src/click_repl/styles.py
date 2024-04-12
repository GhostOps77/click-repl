"""
Default tokens style configurations.
"""

from __future__ import annotations

DEFAULT_COMPLETION_STYLE_CONFIG = {
    # For Boolean type.
    "autocompletion-menu.parameter.type.bool.totrue": "fg:#44e80e",
    "autocompletion-menu.parameter.type.bool.tofalse": "fg:red",
}
"""
Default token style configuration for :class:`~click_repl.completer.ClickCompleter`

:meta hide-value:
"""


DEFAULT_COMPLETION_STYLE_CONFIG.update(
    dict.fromkeys(
        [
            # Command
            "autocompletion-menu.command.name",
            "autocompletion-menu.group.name",
            # Parameter types.
            "autocompletion-menu.parameter.argument.name",
            "autocompletion-menu.parameter.option.name",
            "autocompletion-menu.parameter.option.name.separator",
            # For Path types.
            "autocompletion-menu.parameter.type.path.directory",
            "autocompletion-menu.parameter.type.path.file",
            "autocompletion-menu.parameter.type.path",
            # For Boolean type.
            "autocompletion-menu.parameter.type.bool",
            # For Range types.
            "autocompletion-menu.parameter.type.range.integer",
            "autocompletion-menu.parameter.type.range.float",
            # Internal Command
            "autocompletion-menu.internalcommand.name",
            # Misc.
            "autocompletion-menu.symbol.bracket",
            "autocompletion-menu.space",
        ],
        "",
    )
)


DEFAULT_BOTTOMBAR_STYLE_CONFIG = {
    # Group
    "bottom-bar.group.name": "bold",
    "bottom-bar.group.type": "bold",
    # Command
    "bottom-bar.command.name": "bold",
    "bottom-bar.command.type": "bold",
    # Misc. for Parameter.
    "bottom-bar.parameter.nargs.counter": "fg:green",
    # Base Parameter
    "bottom-bar.parameter.usage.inuse": "bold underline",
    "bottom-bar.parameter.usage.used": "strike",
    # ParamType tokens especially for Tuple type.
    "bottom-bar.parameter.type.usage.inuse": "bold underline",
    "bottom-bar.parameter.type.usage.used": "strike",
    # For displaying Exceptions
    "bottom-bar.error": "fg:red",
    "bottom-bar.error.exception-class-name": "bold",
    "bottom-bar.error.message": "",
}
"""
Default token style configuration for :class:`~click_repl.bottom_bar.BottomBar`

:meta hide-value:
"""

DEFAULT_BOTTOMBAR_STYLE_CONFIG.update(
    dict.fromkeys(
        [
            # Group
            "bottom-bar.group.metavar",
            # Command
            "bottom-bar.command.metavar",
            # Primitive datatypes.
            "bottom-bar.parameter.type.string",
            "bottom-bar.parameter.type.integer",
            "bottom-bar.parameter.type.float",
            # Range types.
            "bottom-bar.parameter.type.range.integer",
            "bottom-bar.parameter.type.range.float",
            "bottom-bar.parameter.type.range.descriptor",
            # Path types.
            "bottom-bar.parameter.type.path",
            "bottom-bar.parameter.type.file",
            # For Boolean type options.
            "bottom-bar.parameter.type.bool",
            # Other arbitrary types.
            "bottom-bar.parameter.type.composite",
            "bottom-bar.parameter.type.choice",
            "bottom-bar.parameter.type.datetime",
            "bottom-bar.parameter.type.uuid",
            "bottom-bar.parameter.type.unprocessed",
            # Base Parameter
            "bottom-bar.parameter.name",
            "bottom-bar.parameter.type",
            # Parameter usage.
            "bottom-bar.parameter.usage.unused",
            # ParamType tokens especially for Tuple type.
            "bottom-bar.parameter.type.usage.unused",
            # Misc.
            "bottom-bar.space",
            "bottom-bar.ellipsis",
            "bottom-bar.symbol",
            "bottom-bar.symbol.bracket",
            # Misc. for Parameter.
            "bottom-bar.parameter.nargs",
            "bottom-bar.parameter.argument.name",
            "bottom-bar.parameter.option.name",
        ],
        "",
    )
)


DEFAULT_PROMPTSESSION_STYLE_CONFIG = {
    "bottom-toolbar": "fg:lightblue bg:default noreverse",
    "validation-toolbar": "bg:default #ff0000 noreverse",
}
"""
Default token style configuration for :class:`~prompt_toolkit.shortcuts.PromptSession`

:meta hide-value:
"""

DEFAULT_PROMPTSESSION_STYLE_CONFIG.update(DEFAULT_BOTTOMBAR_STYLE_CONFIG)
DEFAULT_PROMPTSESSION_STYLE_CONFIG.update(DEFAULT_COMPLETION_STYLE_CONFIG)
