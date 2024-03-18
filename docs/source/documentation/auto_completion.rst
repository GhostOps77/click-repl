Auto Completion
===============

click-repl uses :class:`~prompt_toolkit.completion.Completer` as it's base class to implement it's auto-completion
class (:class:`~click_repl.completer.ClickCompleter`), to provide suggestions to it's prompt.
It uses :class:`~click_repl.completer.ClickCompleter` by default.

It can yield out completions from every click component's ``shell_complete`` (or ``autocompletion`` in version 7) method.
It also does generate auto completion specific to each of click components.

:class:`~click_repl.completer.ReplCompletion`
---------------------------------------------

It's implemented by using :class:`~prompt_toolkit.completion.Completion` as the base class.
Objects of this type holds the information about the possible suggestion for the incomplete text in repl prompt.
These objects are submitted from prompt to appear as suggestions in terminal.

:class:`~click_repl.completer.ReplCompletion` vs :class:`~prompt_toolkit.completion.Completion`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The only difference between :class:`~click_repl.completer.ReplCompletion`and :class:`~prompt_toolkit.completion.Completion`
is, :class:`~click_repl.completer.ReplCompletion` calculates the starting position, relative to the text cursor, from
where the :attr:`~prompt_toolkit.completion.Completion.text` must inserted, whereas
:class:`~prompt_toolkit.completion.Completion` just appends the values in prompt, from the position of cursor.

Usage
~~~~~

click-repl retrieves it's suggestions from ``shell_complete`` functions first (``autocompletion`` in click v7).
It prioritizes and yields the suggestions from these functions, other than generating them by their types.

You can use :class:`~click_repl.completer.ReplCompletion` in your custom ``shell_complete`` function.

.. code-block:: python

    from difflib import get_close_matches

    import os
    import click
    from click_repl import repl

    games_list = os.listdir("my/games/directory")

    @click.group()
    @click.pass_context
    def main():
        repl(ctx)

    def complete_games_list(ctx, param, incomplete):
        return [
            ReplCompletion(i, incomplete)
            for i in get_close_matches(incomplete, games_list, cutoff=0.5)
        ]

    @click.command()
    @click.argument("name", shell_complete=complete_games_list)
    def get_game(name):
        click.echo(f"Game name: {name}")


But, It will still work if you just return suggestions as plain string.

.. code-block:: python

    def complete_games_list(ctx, param, incomplete):
        return get_close_matches(incomplete, games_list, cutoff=0.5)

    @click.command()
    @click.argument("name", shell_complete=complete_games_list)
    def get_game(name):
        click.echo(f"Game name: {name}")


Or as a tuple of ``(text, display_meta)``

.. code-block:: python

    def complete_games_list(ctx, param, incomplete):
        # Displays game titles as in 'title' format as help text, but inserts text as in raw form.
        return [
            (i, i.title())
            for i in get_close_matches(incomplete, games_list, cutoff=0.5)
        ]

    @click.command()
    @click.argument("name", shell_complete=complete_games_list)
    def get_game(name):
        click.echo(f"Game name: {name}")


Or as :class:`~click.shell_completion.CompletionItem`

.. code-block:: python

    from click.shell_completion import CompletionItem

    def complete_games_list(ctx, param, incomplete):
        # Displays game titles as in 'title' format as help text, but inserts text as in raw form.
        return [
            CompletionItem(i, help=i.title())
            for i in get_close_matches(incomplete, games_list, cutoff=0.5)
        ]

    @click.command()
    @click.argument("name", shell_complete=complete_games_list)
    def get_game(name):
        click.echo(f"Game name: {name}")

All these examples work in the similar manner.

It does also use ``shell_complete`` method from :class:`~click.types.ParamType` classes. Refer to
`Custom Type Completion <https://click.palletsprojects.com/en/8.1.x/shell-completion/#custom-type-completion>`_ from click docs.

Custom Completer
----------------

You can make your own completer class. And in order to use it, pass it into the :func:`~click_repl._repl.repl` function's
``completer_cls`` parameter. Passing in the class alone will supply it's constructor with necessary values to it's parameters.

.. note::

    Make sure to use :class:`click_repl.completer.ClickCompleter` as base class in order to make your custom completer
    work with repl.

    :class:`~click_repl.completer.ClickCompleter` has an abstract method for almost every unique aspect and components
    in click module. Therefore, It's easy to customize it's autocompletion behaviour for every single component.

.. code-block:: python

    import click

    from click_repl import repl
    from click_repl.completer import ClickCompleter


    class MyCompleter(ClickCompleter):
        def get_completions(self, document):
            # Implement your logic on generating suggestions for incomplete text in prompt.
            ...

    @click.group()
    @click.pass_context
    def main():
        repl(ctx, completer_cls=MyCompleter)  # Now, it'll use custom completer.


Refer to ``ClickCompleter``'s `API Docs <~click_repl.completer.ClickCompleter>`_ to know about component specific methods.


.. note::

    You cannot disable completer in the same way just like for the validator. The completer is the crucial component of the click-repl module.

Completer kwargs
----------------

If you want to pass in extra keyword arguments to the completer, you can pass it through ``completer_kwargs`` parameter
of :func:`~click_repl._repl.repl` function.

.. code-block:: python

	@click.group()
	@click.pass_context
	def main():
		repl(ctx, completer_cls=MyCompleter, completer_kwargs={
            # Your extra keyword arguments goes here.
            'shortest_opts_only': True,
            'show_hidden_commands': False
            ...
        })

This keyword arguments dictionary will be updated with the default keyword arguments of completer, that will be supplied to
the completer while initializing the repl. The default arguments for :class:`~click-repl.completer.ClickCompleter` are -

    #. ``ctx`` - :class:`~click.Context` of the invoked group.
    #. ``internal_command_system`` - :class:`~click_repl.internal_commands.InternalCommandSystem` object, and
    #. ``bottom_bar`` - :class:`~click_repl.bottom_bar.BottomBar` object of the current repl session.

These default values are supplied from :meth:`~click_repl._repl.Repl._get_default_completer_kwargs` method.

Suggesting shortest opt names only for Options
----------------------------------------------

:class:`~click_repl.completer.ClickCompleter` suggests all the option names separately by default.
In order to suggest only the shortest flag for each option, set ``shortest_opts_only`` as ``True`` to the
completer's keyword arguments.

The flag :attr:`~click_repl.completer.ClickCompleter.shortest_opts_only` determines whether only the shortest name of an
option parameter should be used for auto-completion or not. It's ``False`` by default.

By this, The options that have more than 1 option name will insert only the shortest opts when the suggestion is accepted,
but their suggestions have all of their names separated by ``/``.

.. code-block:: python

    @click.group()
    @click.pass_context
    def main(ctx):
        repl(ctx, completer_kwargs={
            'shortest_opt_names_only': True
        })

    @main.command()
    @click.option('-u', '--username')
    @click.option('-p', '--port')
    def connect_to_db(username, port):
        ...

<insert image>

Suggesting hidden Commands and Parameters
-----------------------------------------

:class:`~click_repl.completer.ClickCompleter` won't suggest hidden commands and parameters by default.

In order to change that, use :attr:`click_repl.completer.ClickCompleter.show_hidden_commands` flag to get hidden
commands in your suggestions. And use :attr:`click_repl.completer.ClickCompleter.show_hidden_params` flag
to get hidden suggestions for hidden parameters. Assign ``True`` to them to display hidden commands and parameters.

These flags determine whether the hidden commands/parameters should be shown in suggestions or not.
It's ``False`` by default.

But even if :attr:`click_repl.completer.ClickCompleter.show_hidden_commands` is ``False``, if user enters
the whole name of the hidden command, it's parmeters are then suggested.

.. code-block:: python

    @click.group()
    @click.pass_context
    def main(ctx):
        repl(ctx, completer_kwargs={
            'show_hidden_commands': True,
            'show_hidden_params': True
        })

    @main.command()
    @click.option('-u', '--username')
    @click.option('-p', '--port')
    def connect_to_db(username, port):
        ...

    @main.command(hidden=True)
    @click.option('-u', '--username')
    @click.option('-p', '--port', hidden=True)
    def connect_to_admin_db(username, port):
        ...

<insert image>

Suggesting only unused Parameters
---------------------------------

click-repl suggests option names even of the parameters that have already received their values from the prompt, by default.
So that the user can overwrite and give a different value even after supplying a value to it.

In order to stop the completer to suggest option names of such parameters, set
:attr:`click_repl.completer.ClickCompleter.show_only_unused_options` as ``True``. It's ``False`` by default.

This flag determines whether the options that are already mentioned or used in the current prompt should be
displayed for suggestion or not.

.. code-block:: python

    @click.group()
    @click.pass_context
    def main(ctx):
        repl(ctx, completer_kwargs={
            'show_only_unused_options': True
        })

    @main.command()
    @click.option('-u', '--username')
    @click.option('-p', '--port')
    def connect_to_db(username, port):
        ...

<insert image>
