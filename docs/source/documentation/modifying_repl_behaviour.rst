Modify REPL behaviour
=====================

Remove ``repl`` command after invoking the REPL
-----------------------------------------------

The :func:`~click_repl.s.register_repl` decorator assigns the :func:`~click_repl._repl.repl` function
as a command to your group. But, you can also initialize a repl session inside a repl session, as this same
``repl`` command is available in the repl session.

.. code-block:: python

    import click
    from click_repl import register_repl

    @click.group()
    @register_repl
    def main():
        pass

    @main.command()
    def command1():
        pass

<insert image>

In order to remove this repl command before invoking the repl, set the ``remove_command_before_repl`` parameter to ``False``
in :func:`~click_repl.decorators.register_repl`.

.. code-block:: python

    import click
    from click_repl import register_repl

    @click.group()
    @register_repl(remove_command_before_repl=True)
    def main():
        pass

    @main.command()
    def command1():
        pass

<insert image>

:class:`~click_repl._repl.ReplCli`
----------------------------------

This class inherits from :class:`~click.Group`, which can also be used to invoke repl.

.. code-block:: python

    # file: app.py

    import click
    from click_repl import ReplCli

    @click.group(cls=ReplCli)
    def main():
        pass

    @main.command()
    @click.argument('name')
    def greet(name):
        print(f'Hi {name}!')

It invokes repl, only when no extra arguments were passed to the group.

.. code-block:: shell

    $ python app.py greet Sam
    Hi Sam!
    $ python app.py
    > greet Sam
    Hi Sam!
    >

But :class:`~click_repl._repl.ReplCli` provides a little more features than just using either :func:`~click_repl.decorators.register_repl`
or :func:`~click_repl._repl.repl`.

:attr:`~click_repl._repl.ReplCli.startup` and :attr:`~click_repl._repl.ReplCli.cleanup` callbacks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:class:`~click_repl._repl.ReplCli` allows you to run code before invoking the repl, and after exiting out of the repl.

The code that should be ran before invoking the repl can be supplied as a callback to :attr:`~click_repl._repl.ReplCli.startup`
parameter of :class:`~click_repl._repl.ReplCli`.

Similarly, the code that should be executed after exiting out of the repl can also be supplied as a callback to ``cleanup`` parameter
of :class:`~click_repl._repl.ReplCli`.

.. note::

    The ``startup`` and ``cleanup`` callbacks should be in type of ``Callable[[], None]``.

.. code-block:: python

    # file: app.py

    import click
    from click_repl import ReplCli

    @click.group(
        cls=ReplCli,
        startup=lambda: print('Entering REPL...'),
        cleanup=lambda: print('Exiting REPL...')
    )
    def main():
        pass

    @main.command()
    @click.argument('name')
    def greet(name):
        print(f'Hi {name}!')

.. code-block:: shell

    $ python app.py greet Sam
    Hi Sam!
    $ python app.py
    Entering REPL...
    > greet Sam
    Hi Sam!
    > :exit
    Exiting REPL...
    $

Custom prompt
-------------

click-repl uses  ``> `` as it's prompt by default. But you can assign custom prompt instead of the default prompt by -

#. Assigning your prompt to ``message`` key in :func:`~click_repl._repl.repl`'s ``prompt_kwargs`` dictionary.

   .. code-block:: python

       # file: app.py

       import click
       from click_repl import repl

       @click.group()
       @click.pass_context
       def main(ctx):
           repl(ctx, prompt_kwargs={
               'message': '>>> '
           })

   .. code-block:: shell

       $ python app.py
       >>>

#. Pass it in via :attr:`~click_repl._repl.ReplCli.prompt` parameter in :attr:`~click_repl._repl.ReplCli`.

   .. code-block:: python

       import click
       from click_repl import ReplCli

       @click.group(cls=ReplCli, prompt='>>> ')
       def main():
           pass

#. You can also access the prompt that's used in the repl from :attr:`~click_repl.core.ReplContext.prompt` property. You
   can modify the prompt in this property to change the prompt during runtime.

   .. code-block:: python

       import os

       import click
       import click_repl
       from pathlib import Path

       @click.group(cls=click_repl.ReplCli, prompt='user@/$ ')
       def main():
           pass

       @main.command('cd')
       @click.argument('path', type=click.Path(file_okay=False))
       @click_repl.pass_context
       def change_directory(repl_ctx, path):
           resolved_path = Path(repl_ctx.prompt.split('@')[1].removesuffix('$ ') + path).resolve()
           os.chdir(resolved_path)
           repl_ctx.prompt = f"user@{resolved_path}$ "


``prompt_kwargs``
-----------------

click-repl uses an instance :class:`~prompt_toolkit.PromptSession` as it's prompt interface. You can supply custom arguments to
the :class:`~prompt_toolkit.PromptSession` instance via :func:`~click_repl._repl.repl` or :class:`~click_repl._repl.ReplCli`'s
``prompt_kwargs`` keyword argument.

.. code-block:: python

    import click
    from click_repl import ReplCli
    from prompt_toolkit.history import FileHistory

    @click.group(
        cls=ReplCli,
        prompt_kwargs={
            'history': FileHistory('/etc/myrepl/myrepl-history'),
        }
    )
    def main():
        pass

Now, this click-repl app stores history of previously executed commands in the above mentioned file.

This keyword arguments dictionary will be updated with the default keyword arguments of :class:`~prompt_toolkit.PromptSession`,
that will be supplied to it while initializing the repl. The default arguments and their values for
:class:`~prompt_toolkit.PromptSession` are -

    #. ``history`` - :class:`~prompt_toolkit.history.InMemoryHistory` object for storing previous command history per repl session.
    #. ``message`` - ``"> "``
    #. ``complete_in_thread`` - ``True``
    #. ``complete_while_typing`` - ``True``
    #. ``validate_while_typing`` - ``True``
    #. ``mouse_support`` - ``True``
    #. ``refresh_interval`` - 0.15

These default values are supplied from :meth:`~click_repl._repl.Repl._get_default_prompt_kwargs` method. Refer to
:class:`~prompt_toolkit.PromptSession` docs for details about these parameters.

:class:`~click_repl._repl.Repl`
-------------------------------

This class is the curcial part of this module which configures and performs the repl action via it's
:meth:`~click_repl._repl.Repl.loop` method.

Custom :class:`~click_repl._repl.Repl`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you really want to customize every aspects of the repl configuration and execution, you can create your own Repl class
that has the same blueprint/template of :class:`~click_repl._repl.Repl`. It's better if you inherit and use it
from :class:`~click_repl._repl.Repl`.

After creating one, you can use it by passing it into ``cls`` parameter of :func:`~click_repl._repl.repl` function.

.. code-block:: python

    import click
    from click_repl import Repl, repl

    class MyRepl(Repl):
        # Implement your own REPL customization.
        ...

    @click.group()
    @click.pass_context
    def main(ctx):
        repl(ctx, cls=MyRepl)


:class:`~click_repl.core.ReplContext`
-------------------------------------

Unlike :class:`~click.Context`, this class is instantiated for every new repl session.
This object keeps track of the current repl's state, while it's parsing arguments from the prompt while typing.

You can also obtain many objects that's responsible for the functionality of the repl, from this context object,
in order to have extreme flexibility over customizing your repl session during runtime.

You can access it using :func:`~click_repl.decorators.pass_context` decorator, which is similar to :func:`~click.pass_context`.
So, please don't accidentally switch them.

.. note::

    A :class:`~click_repl.core.ReplContext` is instantiated only when repl is invoked. Therefore, you won't be able to use it inside the group.

.. code-block:: python

    import click
    import click_repl

    @click_repl.register_repl
    @click.group()
    @click.pass_context
    def main(ctx):
        pass

    @main.command()
    @click.pass_context
    @click_repl.pass_context
    def command(ctx, repl_ctx):
        # You can do whatever you want with the current repl session's context object.
        ...
