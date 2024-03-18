Internal Commands Utility
=========================

click-repl allows usage of certain prefixes to use the system shell commands.
It also has other pre-defined, helpful Internal commands registered in it.
These commands are not :class:`~click.Command` types.

Internal Commands
-----------------

The internal commands can be invoked with a prefix associated to refer to their name (Default: ``:``).
Run ``:help`` in a repl to know about it's usage.


:class:`~click_repl.internal_commands.InternalCommandSystem`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All the internal commands are defined and accessed from :class:`~click_repl.internal_commands.InternalCommandSystem` object.
You can get this object from :attr:`~click_repl.core.ReplContext.internal_command_system` attribute of the current repl
session's :class:`~click_repl.ReplContext` object.

.. code-block:: python

    from click_repl._globals import get_current_repl_ctx

    ics_obj = get_current_repl_ctx().internal_command_system # <class 'InternalCommandSystem'>


Add/Remove internal commands
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This object can also be used to define and add your own internal command. It's done by using the
:meth:`~click_repl.internal_commands.InternalCommandSystem.register_command` decorator.
It takes in a function, names/aliases and description for it. The function's name and docstring is the command's only name
and description by default.

To remove an internal command, pass in any one of the aliases of the command into
:meth:`~click_repl.internal_commands.InternalCommandSystem.remove_command` to remove the command, along with all of it's
other aliases.

.. note::

    * You can register and delete internal commands from anywhere, as long as you can access the current repl session's :class:`~click_repl.ReplContext` object.

    * The callback function for your custom internal command must be in the type of ``Callable[[], None]``. That is, It shouldn't take in any arguments, and should return nothing.

    * :meth:`~click_repl.internal_commands.InternalCommandSystem.remove_command` removes all the aliases of the given alias of a command, by default. In order to remove only the mentioned alias, pass ``remove_all_aliases=False`` to the method.

For this example, we register the ``hi`` function as an internal command, and delete it later on.

.. code-block:: python

    import click
    import click_repl

    @click.group()
    @click.pass_context
    def main(ctx):
        click_repl.repl(ctx)

    @main.command()
    @click_repl.pass_context
    def add_internal_command(repl_ctx: click_repl.ReplContext):
        ics_obj = repl_ctx.internal_command_system

    @ics_obj.register_command(names=["hi", "greet", "hola"])
    def hi():
        print("Hi!")

    @main.command()
    @click_repl.pass_context
    def del_internal_command(repl_ctx: click_repl.ReplContext):
        ics_obj = repl_ctx.internal_command_system
        ics_obj.remove_command("hi", remove_all_aliases=False) # Removes only alias 'hi'
        # ics_obj.remove_command("hi") # Removes all the aliases that belong to command 'hi'


.. code-block:: shell

    > add-internal-command
    > :hi
    Hi!
    > del-internal-command
    > :hi
    Hi!
    'hi', command not found

Default internal commands
~~~~~~~~~~~~~~~~~~~~~~~~~

There are 3 internal commands registered by default. They are:

#. `clear <click.clear>`_ - Clears terminal screen. Uses click's :func:`~click.clear` function as command callback.

   **Aliases:** ``clear``, ``cls``

#. `help <click_repl.internal_commands.help_internal>`_ - Displays general help information about the internal commands.

   **Aliases:** ``?``, ``h``, ``help``

   .. code-block:: shell

       > :help
       REPL help:

       External/System Commands:
         Prefix External/System commands with "!".

       Internal Commands:
         Prefix Internal commands with ":".
         :clear, :cls      Clears screen.
         :?, :h, :help     Displays general help information.
         :exit, :q, :quit  Exits the REPL.

#. `exit <click_repl.internal_commands.repl_exit>`_ - Exits the REPL.

   **Aliases:** ``exit``, ``q``, ``quit``

   .. note::

        You need to raise :exc:`~click_repl.exceptions.ExitReplException` anywhere from your code to exit out of the repl.

System Commands
---------------

click-repl also allows shell escape to run underlying system's shell commands by using it's specified prefix in
repl (Default: ``!``).

.. code-block:: shell

    > !echo hi
    hi


Assigning custom prefixes
-------------------------

You can use custom prefixes for the internal command utility, by passing in those prefixes explicitly into
:func:`~click_repl._repl.repl` function.

.. code-block:: python

    import click
    from click_repl import repl

    @click.group()
    @click.option('-i', '--interactive', flag=True)
    @click.pass_context
    def main(ctx, interactive):
        if interactive:
            repl(
                internal_command_prefix='-',  # Disables access to internal commands.
                system_command_prefix='$'  # Disables shell escape from the REPL.
            )


.. code-block:: shell

    > -help
    REPL help:

    External/System Commands:
        Prefix External/System commands with "-".

    Internal Commands:
        Prefix Internal commands with "$".
        :clear, :cls      Clears screen.
        :?, :h, :help     Displays general help information.
        :exit, :q, :quit  Exits the REPL.

    > $echo hi
    hi

Enabling/Disabling Internal and System Commands
-----------------------------------------------

Assigning ``None`` as prefix disables the appropriate internal command utility. But you need to assign it explicitly for both
internal command and system command prefixes, to remove them both. Assigning ``None`` to system command disables
shell escape utilty.

.. note::

    Make sure you have a way to exit out of the repl in order to not get stuck in it, after doing either -

    * Disabling internal commands, or

    * Deleting the `exit <click_repl.internal_commands.repl_exit>`_ internal command.

    If you've forgotten to so, then, well... good luck on getting out of the REPL. (*Just close the terminal*).

.. code-block:: python

    import click
    from click_repl import repl

    @click.group()
    @click.pass_context
    def main(ctx):
        repl(
            internal_command_prefix=None,  # Disables access to internal commands.
            system_command_prefix=None  # Disables shell escape from the REPL.
        )

.. code-block:: shell

    > !echo
    main: No such command '!echo'
    > :help
    main: No such command ':help'
