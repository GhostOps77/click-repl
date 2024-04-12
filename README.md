### click-repl

[![Tests](https://github.com/GhostOps77/click-repl/actions/workflows/workflow.yml/badge.svg?branch=GhostOps77-patch-1)](https://github.com/GhostOps77/click-repl/actions/workflows/workflow.yml)
[![License](https://img.shields.io/pypi/l/click-repl?label=License)](https://github.com/GhostOps77/click-repl/blob/GhostOps77-patch-1/LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
![Python - Version](https://img.shields.io/badge/python-3%20%7C%203.7%20%7C%203.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)
[![PyPI - Version](https://img.shields.io/badge/pypi-v0.2.0-blue)](https://pypi.org/project/click-repl/)
![wheels](https://img.shields.io/piwheels/v/click-repl?label=wheel)
![PyPI - Status](https://img.shields.io/pypi/status/click)
![PyPI - Downloads](https://img.shields.io/pypi/dm/click-repl)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

click-repl is an extension for the `click <https://click.palletsprojects.com/en/>`_ module,
designed to integrate a REPL (Read-Eval-Print-Loop) within your click application. It achieves this by utilizing
`python-prompt-toolkit <https://github.com/prompt-toolkit/python-prompt-toolkit>`_ as its backend. This module enables
seamless interaction with your CLI commands, providing auto-completion features in your shell environment, and offering a platform to
execute shell commands without the need to tweak your ``.bashrc`` or ``.ps1`` configuration files.

All customizations can be conveniently handled using pure Python code.

#### Installation

Installation is done via pip:

```shell
pip install click-repl
```

#### Usage

To add the ``repl`` command to your click app, use ``register_repl()`` decorator
on your click app's main group. Invoke it from command line to start the REPL.

```py
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
```

![Demo](assets/demo.gif)
