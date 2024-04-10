Internal Commands Utility
=========================

click-repl allows usage of certain prefixes to use the system shell commands.
It also has other pre-defined, helpful Internal commands registered in it.
These commands are not :class:`~click.Command` types.

Internal Commands
~~~~~~~~~~~~~~~~~

The internal commands can be invoked with a prefix associated to refer to their name (Default: ``:``).
Run ``:help`` in a repl to know about it's usage.


:class:`~click_repl._internal_cmds.InternalCommandSystem`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All the internal commands are defined and accessed from :class:`~click_repl._internal_cmds.InternalCommandSystem` object.
You can get this object from :attr:`~click_repl.core.ReplContext.internal_command_system` attribute of the current repl context.

.. admonition:: Example

    .. code-block:: python

        from click_repl._globals import get_current_repl_ctx

        ics_obj = get_current_repl_ctx().internal_command_system # <class 'InternalCommandSystem'>


Add/Remove internal commands
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This object can also be used to define and add your own internal command. It's done by using the :func:`~click_repl._internal_cmds.InternalCommandSystem.register_command` decorator.
It takes in a function, names/aliases and description for it. The function's name and docstring is the command's only name and description by default.

.. admonition:: Example

    You can register your internal command from anywhere.
    But for following example, we register the ``kill`` function as an internal command from the main group.

    .. code-block:: python

        import click
        import click_repl

        @click.group(invoke_without_subcommand=True)
        @click.pass_context
        @click_repl.register_repl
        def main(ctx: click.Context, repl_ctx: click_repl.ReplContext):
            # Defining custom internal command inside the main group.
            ...

            if not ctx.invoked_subcommand:
                ics_obj = repl_ctx.internal_command_system

                # Allows aliases.
                @ics_obj.register_command(
                    names=['kill', 'pkill'],
                    description='Stops a certain process'
                )
                def kill():
                    ...

                # Function's docstring can also be the command's description.
                @ics_obj.register_command
                def kill():
                    '''Stops a certain process.'''
                    ...

Remove internal commands
~~~~~~~~~~~~~~~~~~~~~~~~

Pass in any one of the aliases of the command into :meth:`!click_repl._internal_cmds.InternalCommandSystem.remove_command` to remove the command, along with all of it's aliases.


Default internal commands
~~~~~~~~~~~~~~~~~~~~~~~~~

There are 3 internal commands registered by default. They are:

1. `clear <click.clear>`_ - Clears terminal screen. Uses click's :class:`~click.clear` function.

**Aliases:** ``clear``, ``cls``

2. `help <click_repl._internal_cmds.help_internal>`_ - Displays general help information about the internal commands.

**Aliases:** ``?``, ``h``, ``help``

.. admonition:: Output

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

3. `exit <click_repl._internal_cmds.repl_exit>`_ - Exits the REPL.

**Aliases:** ``exit``, ``q``, ``quit``


System Commands
---------------

click-repl also allows shell escape to run underlying system's shell commands by using it's specified prefix in repl (Default: ``!``).

.. admonition:: Example

  .. code-block:: shell

      > !echo hi
      hi

Assigning custom prefixes
~~~~~~~~~~~~~~~~~~~~~~~~~

You can use custom prefixes for the internal command utility, by passing in those prefixes explicitly into :func:`~click_repl.repl` function.

.. admonition:: Example

	.. code-block:: python

		import click
		from click_repl import repl

		@click.group()
		@click.option('-i', '--interactive', flag=True)
		@click.pass_context
		def main(ctx: click.Context, interactive: bool):
			if interactive:
				repl(
					internal_command_prefix='-',  # Disables access to internal commands.
					system_command_prefix='$'  # Disables shell escape from the REPL.
				)

	.. code-block:: shell

		> -help
		REPL help:

		External/System Commands:
			Prefix External/System commands with "!".

		Internal Commands:
			Prefix Internal commands with ":".
			:clear, :cls      Clears screen.
			:?, :h, :help     Displays general help information.
			:exit, :q, :quit  Exits the REPL.

		> $echo hi
		hi
		>

Enabling/Disabling Internal Commands and shell escape
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Assigning ``None`` as prefix disables the internal command utility. But you need to assign it explicitly for both internal command and system command prefixes, to remove them both.

.. admonition:: Example

	.. code-block:: python

		import click
		from click_repl import repl

		@click.group()
		@click.option('-i', '--interactive', flag=True)
		@click.pass_context
		def main(ctx: click.Context, interactive: bool):
			if interactive:
				repl(
					internal_command_prefix=None,  # Disables access to internal commands.
					system_command_prefix=None  # Disables shell escape from the REPL.
				)

	.. code-block:: shell

		> !echo
		main: No such command '!echo'

		> :help
		main: No such command ':help'

	But make sure you have a way to exit out of the repl in order to not get stuck in it.
	If you've forgotten to so, then, well... good luck on getting out of the REPL. (Just close the terminal).
