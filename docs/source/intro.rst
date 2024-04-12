click-repl is an extension for the `click <https://click.palletsprojects.com/en/>`_ module, designed to integrate a REPL
(Read-Eval-Print-Loop) within your click application. It achieves this by utilizing
`python-prompt-toolkit <https://python-prompt-toolkit.readthedocs.io/en/master/>`_ as its backend. This module enables seamless
interaction with your CLI commands, providing auto-completion features in your shell environment, and offering a platform to execute
shell commands without the need to tweak your ``.bashrc`` or ``.ps1`` configuration files.

All customizations can be conveniently handled using pure Python code.

Installation
============

You can install click-repl via pip:

.. code-block:: shell

    pip install click-repl


Usage
=====

To add the :func:`~click_repl._repl.repl` command to your click app's main group,
use :func:`~click_repl._repl.register_repl` decorator. Invoke it from command line to start the REPL.

.. code-block:: python
   :linenos:

   # filename.py

   import click
   from click_repl import register_repl

   @register_repl
   @click.group()
   def cli():
       pass

   @cli.command()
   def hello():
       click.echo("Hello world!")

   cli()


.. image:: ../../assets/demo.gif
   :align: center
   :alt: Demo
