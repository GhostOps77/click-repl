Internal Commands Utility
=========================

click-repl allows usage of certain prefixes to execute system shell commands via REPL.
It also provides other pre-defined, helpful internal commands registered within it.
These commands are not of type :class:`~click.Command`.

.. _Internal Commands:

Internal Commands
-----------------

The internal commands can be invoked with a prefix associated with their name (Default: ``:``).
Run ``:help`` in the REPL to know about its usage.

.. code-block::

  > :help
  REPL help:

    External/System Commands:
      Prefix External/System commands with "!".

    Internal Commands:
      Prefix Internal commands with ":".
      :clear, :cls      Clears screen.
      :?, :h, :help     Displays general help information.
      :exit, :q, :quit  Exits the REPL.


InternalCommandSystem
~~~~~~~~~~~~~~~~~~~~~

All the internal commands are defined and accessed from :class:`~click_repl.internal_commands.InternalCommandSystem` object.
You can get this object from the :attr:`~click_repl.core.ReplContext.internal_command_system` attribute of the current REPL
session's :class:`~click_repl.core.ReplContext` object.

.. code-block:: python
   :linenos:

    from click_repl.globals_ import get_current_repl_ctx

    ics_obj = get_current_repl_ctx().internal_command_system # <class 'InternalCommandSystem'>


Add/Remove Internal Commands
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This object can also be used to define and add your own internal command. It's done by using the
:meth:`~click_repl.internal_commands.InternalCommandSystem.register_command` decorator.
It takes a function, names/aliases and description for it. The provided function's name and docstring
is the command's only name and description by default.

To remove an internal command, pass any one of the aliases of the command into
:meth:`~click_repl.internal_commands.InternalCommandSystem.remove_command` to remove the command, along with all of its
other aliases.

.. note::

    * You can register and delete internal commands from anywhere, as long as you can access the current REPL session's :class:`~click_repl.core.ReplContext` object.

    * The callback function for your custom internal command must be of type ``Callable[[], None]``. That is, it shouldn't take in any arguments, and return nothing.

    * :meth:`~click_repl.internal_commands.InternalCommandSystem.remove_command` removes all the aliases of the given alias of a command, by default. To remove only the mentioned alias, set ``remove_all_aliases`` to :obj:`False` to the method.

For this example, we register the ``hi`` function as an internal command, and delete it later on.

.. code-block:: python
   :linenos:

    import click
    import click_repl

    @click.group(invoke_without_command=True)
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


    main()


.. code-block:: shell

    > add-internal-command
    > :hi
    Hi!
    > del-internal-command
    > :hi
    Hi!
    'hi', command not found

Default Internal Commands
~~~~~~~~~~~~~~~~~~~~~~~~~

There are 3 internal commands registered by default. They are:

#. `clear <click.clear>`_ - Clears the terminal screen.

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

        You need to raise :exc:`~click_repl.exceptions.ExitReplException` anywhere from your code to exit out of the REPL.

System Commands
---------------

click-repl also allows shell escape to run underlying system's shell commands by using its specified prefix in
the REPL (Default: ``!``).

.. code-block:: shell

    > !echo hi
    hi


Assigning Custom Prefixes
-------------------------

You can use custom prefixes for the internal command utility by passing in those prefixes explicitly into
:func:`~click_repl._repl.repl` function.

.. code-block:: python
   :linenos:

    import click
    from click_repl import repl

    @click.group(invoke_without_command=True)
    @click.option('-i', '--interactive', flag=True)
    @click.pass_context
    def main(ctx, interactive):
        if interactive:
            repl(
                internal_command_prefix='-',
                system_command_prefix='$'
            )


    main()

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

Assigning :obj:`None` as prefix disables the appropriate internal command utility. But you need to assign it explicitly for both
internal command and system command prefixes to remove them both. Assigning :obj:`None` to the system command disables
shell escape utilty.

.. note::

   Make sure you have a way to exit out of the REPL to avoid getting stuck in it after doing either -

   * Disabling internal commands, or

   * Deleting the `exit <click_repl.internal_commands.repl_exit>`_ internal command.

   If you've forgotten to so, then, well... good luck on getting out of the REPL. (*Just close the terminal*).

.. code-block:: python
   :linenos:

   import click
   from click_repl import repl

   @click.group(invoke_without_command=True)
   @click.pass_context
   def main(ctx):
       repl(
           internal_command_prefix=None,  # Disables access to internal commands.
           system_command_prefix=None  # Disables shell escape from the REPL.
       )


   main()


.. code-block:: shell

   > !echo
   main: No such command '!echo'
   > :help
   main: No such command ':help'
