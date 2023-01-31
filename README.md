Click-REPL
===

[![Tests](https://github.com/GhostOps77/click-repl/actions/workflows/workflow.yml/badge.svg?branch=GhostOps77-patch-1)](https://github.com/GhostOps77/click-repl/actions/workflows/workflow.yml)
[![License](https://img.shields.io/pypi/l/click-repl?label=License)](https://github.com/GhostOps77/click-repl/blob/GhostOps77-patch-1/LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
![Python - Version](https://img.shields.io/badge/python-3%20%7C%203.6%20%7C%203.7%20%7C%203.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)
[![PyPI - Version](https://img.shields.io/badge/pypi-v0.2.0-blue)](https://pypi.org/project/click-repl/)
![wheels](https://img.shields.io/piwheels/v/click-repl?label=wheel)
![PyPI - Status](https://img.shields.io/pypi/status/click)
![PyPI - Downloads](https://img.shields.io/pypi/dm/click-repl)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/GhostOps77/click-repl/main.svg?branch=GhostOps77-patch-1)](https://results.pre-commit.ci/latest/github/GhostOps77/click-repl/GhostOps77-patch-1)

Installation
===

Installation is done via pip:
```shell
pip install click-repl
```
Usage
===

There are many facilitating ways to create your click-repl app<br>
All you have to do in your [click](https://click.palletsprojects.com/en/) app is either -

<details>
  <summary>1. Use <code>register_repl</code> to add <code>repl</code> command to your click app</summary>

  ```py
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
  ```
  In the shell:
  ```shell
  $ my_app
  Entering REPL...
  >>> hello
  Hello world!
  Exiting REPL...
  >>> :exit
  $ echo hello | my_app repl
  Hello World!
  $
  ```
</details>
<details>
  <summary>2. Use the <code>Repl</code> class in the <code>cls</code> parameter of the <code>click.group()</code> decorator</summary>

  ```py
  import click
  from click_repl import Repl

  @click.group(
      cls=ReplCli,
      prompt='>>> ',
      startup=lambda: print("Entering REPL...")
      cleanup=lambda: print("Exiting REPL...")
  )
  def cli():
      pass

  @cli.command()
  def hello():
      click.echo("Hello world!")

  register_repl(cli)
  cli()
  ```
  In the shell:
  ```shell
  $ my_app
  >>> hello
  Hello world!
  >>> :q
  ```
</details>
<details>
  <summary>3. Invoke the <code>repl</code> function manually wherever as you want</summary>

  ```py
  import click
  from click_repl import repl

  @click.group()
  @click.option('-r', '--repl', is_flag=True)
  @click.pass_context
  def cli(ctx, repl):
      if repl:
          repl(ctx)

  @cli.command()
  def hello():
      click.echo("Hello world!")

  register_repl(cli)
  cli()
  ```
  In the shell:
  ```shell
  $ my_app --repl
  > hello
  Hello world!
  > :q
  $
  ```
</details>

**Features not shown:**

- Tab-completion.
- The parent context is reused, which means `ctx.obj` persists between
  subcommands. If you're keeping caches on that object (like I do), using the
  app's repl instead of the shell is a huge performance win.
- Shell commands can be execeuted via this REPL using a prefix (Default Prefix: `!`)
- Some pre-defined, helpful Internal commands are also registered, and invoked via a specified prefix (Default Prefix: `:`). You can use the internal `:help` command to explain usage.

Advanced Usage
===

For more flexibility over how your REPL works you can use the `repl` function, the `ReplCli` class (as shown above), instead of `register_repl`. For example, in your app:

```py
import click
from click_repl import repl
from prompt_toolkit.history import FileHistory

@click.group()
def cli():
    pass

@cli.command()
@click.pass_context
def myrepl():
    prompt_kwargs = {
        'history': FileHistory('/etc/myrepl/myrepl-history'),
    }
    repl(ctx, prompt_kwargs=prompt_kwargs)

cli()
```
And then your custom `myrepl` command will be available on your CLI, which
will start a REPL which has its history stored in
`/etc/myrepl/myrepl-history` and persist between sessions.

Any arguments that can be passed to the [`python-prompt-toolkit`](https://github.com/prompt-toolkit/python-prompt-toolkit) [PromptSession](https://python-prompt-toolkit.readthedocs.io/en/stable/pages/reference.html#prompt_toolkit.shortcuts.PromptSession) function can be passed in the `prompt_kwargs` argument and will be used when instantiating your `Prompt`.
