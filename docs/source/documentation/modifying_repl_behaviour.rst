Modify REPL behaviour
=====================

Remove ``repl`` command after invoking the REPL
-----------------------------------------------

The :func:`~click_repl._repl.register_repl` decorator assigns the :func:`~click_repl._repl.repl` function
as a command to your group. However, it's possible to initialize a REPL session within an another REPL session,
because the ``repl`` command is still available within the REPL session itself.

.. code-block:: python
   :linenos:

   import click
   from click_repl import register_repl

   @register_repl
   @click.group()
   def main():
       pass

   @main.command()
   def my_command():
       pass


   main()

.. image:: ../../../assets/nesting_repl_issue.gif
   :align: center
   :alt: nesting_repl_issue

As shown, invoking the :func:`~click_repl._repl.repl` command within its own REPL leads to a nested REPL.
Exiting the entire REPL requires exiting each layer of the REPL individually.

To prevent this behavior and remove the :func:`~click_repl._repl.repl` command before invoking the REPL, set the ``remove_command_before_repl`` parameter to :obj:`True`
in :func:`~click_repl._repl.register_repl`. By default, this parameter is set to False, meaning it doesn't remove the ``repl`` command.

.. code-block:: python
   :linenos:

   import click
   from click_repl import register_repl

   @register_repl(remove_command_before_repl=True)
   @click.group()
   def main():
       pass

   @main.command()
   def my_command():
       pass


   main()

ReplGroup
---------

The :class:`~click_repl._repl.ReplGroup` class inherits from :class:`~click.Group`, and can also invoke REPL.

.. code-block:: python
   :linenos:

   # file: app.py

   import click
   from click_repl import ReplGroup

   @click.group(cls=ReplGroup)
   def main():
       pass

   @main.command()
   @click.argument('name')
   def greet(name):
       print(f'Hi {name}!')


   main()

It invokes REPL only when no extra arguments were passed to the group.

.. code-block:: shell

   $ python app.py greet Sam
   Hi Sam!
   $ python app.py
   > greet Sam
   Hi Sam!
   >

However, :class:`~click_repl._repl.ReplGroup` offers more features than using either
:func:`~click_repl._repl.register_repl` or :func:`~click_repl._repl.repl`.

Startup and Cleanup Callbacks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:class:`~click_repl._repl.ReplGroup` allows you to run code before invoking the REPL, and after exiting it.
You can provide the code to be executed before invoking the REPL as a callback to the
:attr:`~click_repl._repl.ReplGroup.startup` parameter of :class:`~click_repl._repl.ReplGroup`,
and similarly for cleanup using the :attr:`~click_repl._repl.ReplGroup.cleanup` parameter.

.. note::

   The :attr:`~click_repl._repl.ReplGroup.startup` and :attr:`~click_repl._repl.ReplGroup.cleanup` callbacks should be of type ``Callable[[], None]``.

.. code-block:: python
   :linenos:

   # file: app.py

   import click
   from click_repl import ReplGroup

   @click.group(
       cls=ReplGroup,
       startup=lambda: print('Entering REPL...'),
       cleanup=lambda: print('Exiting REPL...')
   )
   def main():
       pass

   @main.command()
   @click.argument('name')
   def greet(name):
       print(f'Hi {name}!')


   main()

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

Custom Prompt
-------------

By default, click-repl uses ``>`` as its prompt. You can customize the prompt by:

#. Assigning your prompt to the ``message`` key in :func:`~click_repl._repl.repl`'s ``prompt_kwargs`` dictionary.

   .. code-block:: python
      :linenos:

      # file: app.py

      import click
      from click_repl import repl

      @click.group(invoke_without_command=True)
      @click.pass_context
      def main(ctx):
          repl(ctx, prompt_kwargs={
              'message': '>>> '
          })


      main()

   .. code-block:: shell

      $ python app.py
      >>>

#. Pass it via the :attr:`~click_repl._repl.ReplGroup.prompt` parameter in :attr:`~click_repl._repl.ReplGroup`.

   .. code-block:: python
      :linenos:

      import click
      from click_repl import ReplGroup

      @click.group(cls=ReplGroup, prompt='>>> ')
      def main():
          pass


      main()

#. Accessing and modifying the prompt during runtime using the :attr:`~click_repl.core.ReplContext.prompt` property.

   .. code-block:: python
      :linenos:

      import os

      import click
      import click_repl
      from pathlib import Path

      @click.group(cls=click_repl.ReplGroup, prompt='user@/$ ')
      def main():
          pass

      @main.command('cd')
      @click.argument('path', type=click.Path(file_okay=False))
      @click_repl.pass_context
      def change_directory(repl_ctx, path):
          resolved_path = Path(repl_ctx.prompt.split('@')[1].removesuffix('$ ') + path).resolve()
          os.chdir(resolved_path)
          repl_ctx.prompt = f"user@{resolved_path}$ "


      main()

prompt_kwargs
-------------

click-repl uses an instance of :class:`~prompt_toolkit.shortcuts.PromptSession` as its prompt interface. You can provide custom arguments to
this :class:`~prompt_toolkit.shortcuts.PromptSession` instance via the ``prompt_kwargs`` parameter of :func:`~click_repl._repl.repl` function
or :class:`~click_repl._repl.ReplGroup` class.

.. code-block:: python
   :linenos:

   import click
   from click_repl import ReplGroup
   from prompt_toolkit.history import FileHistory

   @click.group(
       cls=ReplGroup,
       prompt_kwargs={
           "history": FileHistory("/etc/myrepl/myrepl-history"),
       }
   )
   def main():
       pass


   main()

With this configuration, the click-repl application stores a history of previously executed commands in the specified file.

This dictionary of keyword arguments will be updated with the default keyword arguments of :class:`~prompt_toolkit.shortcuts.PromptSession`
when initializing the REPL. The default arguments and their values for
:class:`~prompt_toolkit.shortcuts.PromptSession` are:

#. ``history`` - :class:`~prompt_toolkit.history.InMemoryHistory` (Object for storing previous command history per REPL session.)
#. ``message`` - ``"> "``
#. ``complete_in_thread`` - :obj:`True`
#. ``complete_while_typing`` - :obj:`True`
#. ``validate_while_typing`` - :obj:`True`
#. ``mouse_support`` - :obj:`True`
#. ``refresh_interval`` - 0.15

These default values are supplied from :meth:`~click_repl._repl.Repl.get_default_prompt_kwargs` method.
For further details about these parameters, refer to :class:`~prompt_toolkit.shortcuts.PromptSession` docs.

Repl
----

The :class:`~click_repl._repl.Repl` class is the central component of this module, responsible for configuring and
executing the REPL action through its :meth:`~click_repl._repl.Repl.loop` method.

Custom Repl
~~~~~~~~~~~

If you require extensive customization of the REPL configuration and execution, you can create your own ``Repl`` class
based on the blueprint/template of the :class:`~click_repl._repl.Repl`. It's recommended to inherit and use it
from the :class:`~click_repl._repl.Repl` class.

Once you've created your custom ``Repl`` class, you can use it by passing it into ``cls``
parameter of :func:`~click_repl._repl.repl` function.

.. code-block:: python
   :linenos:

   import click
   from click_repl import Repl, repl

   class MyRepl(Repl):
       # Implement your own REPL customization.
       ...

   @click.group(invoke_without_command=True)
   @click.pass_context
   def main(ctx):
       repl(ctx, cls=MyRepl)


   main()

ReplContext
-----------

Unlike :class:`~click.Context`, the :class:`~click_repl.core.ReplContext` class is instantiated for every new REPL session.
This object tracks the current REPL's state, while parsing arguments from the prompt while typing.

From this context object, you can obtain many objects responsible for the REPL's functionality,
allowing extreme flexibility in customizing your REPL session during runtime.

You can access it using the click_repl's :func:`~click_repl.core.pass_context` decorator, which is similar to click's
:func:`~click.pass_context`. Ensure not to accidentally switch them.

.. note::

   A :class:`~click_repl.core.ReplContext` is instantiated only when the REPL is invoked. Therefore, you won't be able to use it inside the group.

.. code-block:: python
   :linenos:

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

PromptSession object
~~~~~~~~~~~~~~~~~~~~

click-repl utilzes the :class:`~prompt_toolkit.shortcuts.PromptSession` object, resopnsible for the REPL's functionality.
This object can be accessed via the :attr:`~click_repl.core.ReplContext.session` attribute of the :attr:`~click_repl.core.ReplContext`
object. You can leverage this to extend the functionality of the REPL. Refer to
`python-prompt-toolkit <https://python-prompt-toolkit.readthedocs.io/en/master/>`_'s
`PromptSession <https://python-prompt-toolkit.readthedocs.io/en/master/pages/asking_for_input.html#the-promptsession-object>`_ docs.
