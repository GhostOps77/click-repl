"""
`click_repl._repl`

Core functionality of the REPL feature of this module.
"""
import sys
import traceback
import typing as t

import click
from prompt_toolkit.history import InMemoryHistory

from ._globals import get_current_repl_ctx
from ._globals import ISATTY
from ._internal_cmds import ErrorCodes
from ._internal_cmds import InternalCommandSystem
from .bottom_bar import BOTTOMBAR
from .completer import ClickCompleter
from .core import ReplContext
from .exceptions import ClickExit
from .exceptions import ExitReplException
from .exceptions import InternalCommandException
from .exceptions import InvalidGroupFormat
from .parser import split_arg_string
from .utils import get_group_ctx
from .validator import ClickValidator


if t.TYPE_CHECKING:
    from typing import Any, Callable, Dict, Optional, Type
    from prompt_toolkit.completion import Completer
    from prompt_toolkit.validation import Validator
    from click import Context, MultiCommand, Group


__all__ = ["Repl", "register_repl", "repl"]


class Repl:
    """
    Resposnsible for executing and maintaining the REPL
    (Read-Eval-Print-Loop) in the click_repl app.
    """

    def __init__(
        self,
        completer_cls: "Optional[Type[Completer]]" = None,
        validator_cls: "Optional[Type[Validator]]" = None,
        completer_kwargs: "Dict[str, Any]" = {},
        validator_kwargs: "Dict[str, Any]" = {},
        internal_command_prefix: "Optional[str]" = ":",
        system_command_prefix: "Optional[str]" = "!",
        prompt_kwargs: "Dict[str, Any]" = {},
    ):
        """
        Initialize the `Repl` class with the specified settings and configuration
        options.

        Parameters
        ----------
        completer_cls : prompt_toolkit.completion.Completer type class or None.
            `prompt_toolkit.completion.Completer` class to generate
            `prompt_toolkit.completion.Completion` objects for
            auto-completion.

        validator_cls : prompt_toolkit.validation.Validator type class or None.
            `prompt_toolkit.validation.Validator` class to display error
            messages in the bottom bar during auto-completion.

        completer_kwargs : Dictionary of str: Any pairs.
            Keyword arguments thats sent to the `completer_cls` class constructor.

        validator_kwargs : Dictionary of str: Any pairs.
            Keyword arguments thats sent to the `validator_cls` class constructor.

        internal_command_prefix : str or None.
            Prefix that triggers internal commands within the click_repl app.

        system_command_prefix : str or None.
            Prefix that triggers system commands within the click_repl app.

        prompt_kwargs : Dictionary of str: Any pairs.
            Keyword arguments to be passed to the `prompt_toolkit.PromptSession` class.
        """

        self.prompt_kwargs = prompt_kwargs

        # Completer setup.
        if completer_cls is None:
            completer_cls = ClickCompleter

        self.completer_cls = completer_cls
        self.completer_kwargs = completer_kwargs

        # Validator setup.
        if validator_cls is None:
            validator_cls = ClickValidator

        self.validator_cls = validator_cls
        self.validator_kwargs = validator_kwargs

        # Internal Command System setup.
        self.internal_commands_system = InternalCommandSystem(
            internal_command_prefix, system_command_prefix
        )

    def bootstrap_prompt(self) -> "Dict[str, Any]":
        """
        Generates bootstrap keyword arguments for initializing a
        `prompt_toolkit.PromptSession`object, either using default values
        or user-defined values, if available.

        Returns
        -------
        Dictionary of str: Any pairs.
            A dictionary that contains all the keyword arguments to be passed
            to the `prompt_toolkit.PromptSession` class.
        """

        if not ISATTY:
            # If the standard input is not a TTY device, there is no need
            # to generate any keyword arguments for rendering. In this case,
            # an empty dictionary is returned.

            return {}

        # Completer setup.
        default_completer_kwargs = {
            "ctx": self.group_ctx,
            "internal_commands_system": self.internal_commands_system,
        }

        default_completer_kwargs.update(self.completer_kwargs)

        # Validator setup.
        default_validator_kwargs = {
            "ctx": self.group_ctx,
            "internal_commands_system": self.internal_commands_system,
        }

        default_validator_kwargs.update(self.validator_kwargs)

        # Default Keyword arguments for PromptSession object.
        default_prompt_kwargs = {  # type: ignore[arg-type]
            "history": InMemoryHistory(),
            "message": "> ",
            "completer": self.completer_cls(
                **default_completer_kwargs  # type: ignore[arg-type]
            ),
            "validator": self.validator_cls(
                **default_validator_kwargs  # type: ignore[arg-type]
            ),
            "complete_in_thread": True,
            "complete_while_typing": True,
            "validate_while_typing": True,
            "mouse_support": True,
            "bottom_toolbar": BOTTOMBAR.get_formatted_text,
        }

        default_prompt_kwargs.update(self.prompt_kwargs)

        return default_prompt_kwargs

    def get_command_func(self) -> "Callable[[], str]":
        """
        Creates the function that recieves command string input either from user in
        interactive mode, or via stdin directly.

        Returns
        -------
        A function that accepts no arguments, and returns a string.
        """

        if ISATTY:
            # If stdin is a TTY, prompt the user for input using PromptSession.
            def get_command() -> str:
                return self.repl_ctx.session.prompt()  # type: ignore[no-any-return, return-value, union-attr]  # noqa: E501

        else:
            # If stdin is not a TTY, read input from stdin directly.
            def get_command() -> str:
                inp = sys.stdin.readline().strip()
                self.repl_ctx._history.append(inp)  # type: ignore[union-attr]
                return inp

        return get_command

    def repl_check(self) -> None:
        """
        Checks the CLI Group for empty optional arguments that can cause issues
        when executing commands in the REPL.

        Raises
        ------
        InvalidGroupFormat
            If there is an empty optional argument in the CLI Group.
        """

        # When a click.Argument(required=False) parameter in the CLI Group
        # does not have a value, it will consume the first few words from the REPL input.
        # This can cause issues in parsing and executing the command.

        for param in self.group.params:
            if (
                isinstance(param, click.Argument)
                and self.group_ctx.params[param.name] is None  # type: ignore[index]
                and not param.required
            ):
                raise InvalidGroupFormat(
                    f"Group '{self.group.name}' requires value for an "
                    f"optional argument '{param.name}' in REPL mode"
                )

    def execute_command(self, command: str) -> None:
        """
        Executes commands from the given command string received from the REPL.

        Parameters
        ----------
        command : str
            The command string that needs to be parsed and executed.
        """

        if (
            self.repl_ctx.internal_command_system.execute(command.lower())
            == ErrorCodes.NOT_FOUND
        ):
            # If the `InternalCommandSystem.execute()` method cannot find any
            # prefix to invoke the internal commands, the command string is
            # executed as a click command.
            self.execute_click_cmds(command)

    def execute_click_cmds(self, command: str) -> None:
        """
        Executes click commands by parsing the given command string.

        Parameters
        ----------
        command : str
            The command string that needs to be parsed and executed.
        """

        # Splits command text.
        args = split_arg_string(command)

        # The group command will dispatch based on args.
        # The context object can parse args from the
        # protected_args attribute.
        # To ensure correct parsing, we temporarily store the
        # previously available protected_args in a separate variable.

        old_protected_args = self.group_ctx.protected_args

        try:
            self.group_ctx.protected_args = args
            self.group.invoke(self.group_ctx)

        finally:
            # After the command invocation, we restore the
            # protected_args back to the group_ctx.

            self.group_ctx.protected_args = old_protected_args

    def setup_repl_ctx(self) -> None:
        """
        Creates the `click_repl.core.ReplContext` object to manage
        the state of the REPL.
        """

        # Generating prompt kwargs
        self.prompt_kwargs = self.bootstrap_prompt()

        # To assign the parent/previous repl context for the current repl context.
        self.repl_ctx = ReplContext(
            self.group_ctx,
            self.internal_commands_system,
            self.prompt_kwargs,
            parent=get_current_repl_ctx(silent=True),
        )

        # Creating and assigning the command input retrieval function.
        self.get_command: "Callable[[], str]" = self.get_command_func()

    def setup_repl(self, group_ctx: "Context") -> None:
        """
        Main setup before firing up the REPL.

        Parameters
        ----------
        group_ctx : click.Context
            The click context object of the root/parent/CLI group.
        """

        self.group_ctx: "Context" = get_group_ctx(group_ctx)
        self.group: "MultiCommand" = self.group_ctx.command  # type: ignore[assignment]

        self.repl_check()
        self.setup_repl_ctx()

    def loop(self, group_ctx: "Context") -> None:
        """
        Runs the main REPL loop.

        Parameters
        ----------
        group_ctx : click.Context
            The click context object of the root/parent/CLI group.
        """

        self.setup_repl(group_ctx)

        with self.repl_ctx:
            while True:
                try:
                    # Resetting the toolbar to clear its text content,
                    # ensuring that it doesn't display command info from
                    # the previously executed command.

                    BOTTOMBAR.reset_state()
                    command = self.get_command()

                except KeyboardInterrupt:
                    continue

                except EOFError:
                    break

                if not command:
                    if ISATTY:
                        # If ISATTY is True, it means we can still get
                        # input manually from the user in
                        # interactive mode, so we continue the loop.
                        continue

                    else:
                        # If ISATTY is False, it means the input is
                        # being read from stdin. If the command
                        # string is empty, it indicates that the stdin
                        # stream has reached the end-of-file,
                        # so we break the loop.
                        break

                try:
                    self.execute_command(command)

                except (ClickExit, SystemExit):
                    # Hitting Ctrl+C or any click.Context.exit() method
                    # calls should not abort the REPL. We continue the loop to
                    # allow the user to continue interacting with the REPL.
                    continue

                except click.ClickException as e:
                    # For exceptions of type click.ClickException, the exception
                    # class provides a show() method to display the exception
                    # message.
                    e.show()

                except ExitReplException:
                    # If an ExitReplException is raised, it is intended to break out
                    # of the REPL loop. So, We break out of the loop to exit the REPL.
                    break

                except InternalCommandException as e:
                    # InternalCommandException exceptions are caught to print
                    # their error messages in red text, and continue the REPL
                    # loop.

                    click.secho(
                        f"{type(e).__name__}: {e}", color=True, err=True, fg="red"
                    )

                except Exception:
                    # Any other exceptions are caught here, as they can potentially
                    # disrupt the REPL. The traceback error message is displayed,
                    # and the loop continues to the next iteration.

                    traceback.print_exc()


def repl(
    group_ctx: "Context",
    prompt_kwargs: "Dict[str, Any]" = {},
    repl_cls: "Optional[Type[Repl]]" = None,
    **attrs: "Any",
) -> None:
    """
    Start an Interactive Shell. All subcommands are available in it.

    If stdin is not a TTY, No prompt will be printed, but only subcommands
    can be read from stdin.

    Parameters
    ----------
    group_ctx : click.Context
        The current click context object.

    prompt_kwargs : Dictionary of str: Any pairs.
        Parameters passed to `prompt_toolkit.PromptSession`.
        These parameters configure the prompt appearance and behavior,
        such as prompt message, history, completion, etc.

    repl_cls : click_repl._repl.Repl type class.
        Repl class to use for the click_repl app. if `None`, the
        `click_repl._repl.Repl` class is used by default. This allows
        customization of the REPL behavior by providing a custom Repl subclass.

    **attrs : dict, optional
        Extra keyword arguments to be passed to the Repl class. These additional
        arguments can be used to further customize the behavior of the Repl class.
    """

    # Repl class setup.
    if repl_cls is None:
        repl_cls = Repl

    repl_cls(prompt_kwargs=prompt_kwargs, **attrs).loop(group_ctx)


def register_repl(group: "Group", name: str = "repl") -> None:
    """
    Registers `repl()` as sub-command named `name` within the `group`.

    Parameters
    ----------
    group : click.Group
        The Group (current CLI) object to which the repl command will be registered.

    name : str
        The name of the repl command in the given Group.

    Raises
    ------
    TypeError
        If the given group is not an instance of click Group.
    """

    if not isinstance(group, click.Group):
        raise TypeError(
            "Expected 'group' to be a type of click.Group, "
            f"but got {type(group).__name__}"
        )

    group.command(name=name)(click.pass_context(repl))
