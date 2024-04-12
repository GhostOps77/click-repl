click-repl
==========

|Tests| |License| |Code style| |Python-Version| |PyPI-Version| |wheels| |PyPI-Status| |PyPI-Downloads| |pre-commit|

``click-repl`` is an extension for the `click <https://click.palletsprojects.com/en/>`_ module,
designed to integrate a REPL (Read-Eval-Print-Loop) within your click application, by using `python-prompt-toolkit <https://github.com/prompt-toolkit/python-prompt-toolkit>`_ as it's backend.
This module allows for seamless interaction with your CLI commands with auto-completion
features in your shell environment, while offering a platform to execute shell commands,
without the necessity to tweak your ``.bashrc`` or ``.ps1`` configuration files.

All customizations can be conveniently handled using pure Python code.

Installation
============

Installation is done via pip:

.. code-block:: shell

    pip install click-repl

Usage
=====

There are many facilitating ways to create your click-repl app
All you have to do in your `click <https://click.palletsprojects.com/en/>`_ app is to use ``register_repl()`` function to add ``repl`` command to your click app:

.. code-block:: python

  import click
  from click_repl import register_repl

  @click.group()
  def cli():
      pass

  @cli.command()
  def hello():
      click.echo("Hello world!")

  register_repl(cli)
  cli()

In the shell:

.. code-block:: shell

    $ my_app repl
    > hello
    Hello world!
    > :exit
    $ echo hello | my_app repl
    Hello World!
    $


.. |Tests| image:: https://github.com/GhostOps77/click-repl/actions/workflows/workflow.yml/badge.svg?branch=GhostOps77-patch-1
   :target: https://github.com/GhostOps77/click-repl/actions/workflows/workflow.yml
   :alt: Tests
   :height: 20

.. |License| image:: https://img.shields.io/pypi/l/click-repl?label=License
   :target: https://github.com/GhostOps77/click-repl/blob/GhostOps77-patch-1/LICENSE
   :alt: License
   :height: 20

.. |Code style| image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black
   :alt: Code style: black
   :height: 20

.. |Python-Version| image:: https://img.shields.io/badge/python-3%20%7C%203.7%20%7C%203.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue
   :alt: Python-Version
   :height: 20

.. |PyPI-Version| image:: https://img.shields.io/badge/pypi-v0.2.0-blue
   :target: https://pypi.org/project/click-repl/
   :alt: PyPI-Version
   :height: 20

.. |wheels| image:: https://img.shields.io/piwheels/v/click-repl?label=wheel
   :alt: wheels
   :height: 20

.. |PyPI-Status| image:: https://img.shields.io/pypi/status/click
   :alt: PyPI-Status
   :height: 20

.. |PyPI-Downloads| image:: https://img.shields.io/pypi/dm/click-repl
   :alt: PyPI-Downloads
   :height: 20

.. |pre-commit| image:: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white
   :target: https://github.com/pre-commit/pre-commit
   :alt: pre-commit
   :height: 20
