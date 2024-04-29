Getting Started
===============

.. _installation:

Installation
------------

Installation is done via pip:

.. code-block:: shell

    pip install -U click-repl

To install it from source:

.. code-block:: shell

	pip install -U git+https://github.com/click-contrib/click-repl.git

.. _usage:

Usage
-----

click-repl can be integrated with your click application in various ways. Each of them has their own benefits.

#. Use the :func:`~click_repl._repl.register_repl` function to add the :func:`~click_repl._repl.repl` command to your click app.

   This is the traditional way to add a REPL to a click app. It just adds a click command to your group, that invokes the REPL.

   .. code-block:: python

       import click
       from click_repl import register_repl

       @click.group()
       def cli():
           pass

       @cli.command()
       def hello():
           click.echo("Hello world!")

       register_repl(cli, name='myrepl')
       cli()

   But now, you can use :func:`~click_repl._repl.register_repl` as a decorator.

   .. code-block:: python

       import click
       from click_repl import register_repl

       @register_repl(name='myrepl')
       @click.group()
       def cli():
           pass

       @cli.command()

       def hello():
           click.echo("Hello world!")

       cli()


   .. code-block:: shell

       $ my_app myrepl

       > hello
       Hello world!
       > :exit
       $ echo hello | my_app repl
       Hello World!
       $


#. Use the :class:`~click_repl._repl.ReplCli` class in the ``cls`` parameter of the :func:`~click.group` decorator.

   .. code-block:: python

       import click
       from click_repl import ReplCli

       @click.group(
           cls=ReplCli,
           prompt='> ',
           startup=lambda: print("Entering REPL..."),
           cleanup=lambda: print("Exiting REPL...")
       )
       def cli():
           pass

       @cli.command()
       def hello():
           click.echo("Hello world!")

       register_repl(cli)
       cli()


   .. code-block:: shell

       $ my_app
       Entering REPL...
       > hello
       Hello world!
       > :q
       Exiting REPL...
       $


#. Invoke the :class:`~click_repl._repl.repl` function manually wherever as you want:

   .. code-block:: python

       import click
       from click_repl import repl

       @click.group(invoke_without_command=True)
       @click.option('-i', '--interactive', is_flag=True)
       @click.pass_context
       def cli(ctx, interactive):
           if interactive:
               repl(ctx)

       @cli.command()
       def hello():
           click.echo("Hello world!")

       cli()


   .. code-block:: shell

       $ my_app -i
       > hello
       Hello world!
       > :q


.. _advanced_usage:

Advanced Usage
--------------

For more flexibility over how your REPL works, you can use the :class:`~click_repl._repl.repl` function, the
:class:`~click_repl._repl.ReplCli` class (as shown above), instead of :func:`~click_repl._repl.register_repl`. For example, in your app:

.. code-block:: python

  import click
  from click_repl import repl
  from prompt_toolkit.history import FileHistory

  @click.group()
  def cli():
      pass

  @cli.command()
  @click.pass_context
  def myrepl(ctx):
      repl(ctx, prompt_kwargs={
          'history': FileHistory('/etc/myrepl/myrepl-history'),
      })

  cli()

Now, your custom ``myrepl`` command will be available on your CLI, which will start a REPL which has its history stored in
``/etc/myrepl/myrepl-history`` and persist between sessions.

Any arguments that can be passed to the `python-prompt-toolkit <https://github.com/prompt-toolkit/python-prompt-toolkit>`_'s
:class:`~prompt_toolkit.shortcuts.PromptSession` class can be passed in the ``prompt_kwargs`` argument and will be used when
instantiating your prompt.
