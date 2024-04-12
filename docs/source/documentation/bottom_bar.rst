Bottom Bar
==========

.. role:: underline
    :class: underline

.. role:: strike
    :class: strike

click-repl displays a bottom bar, made by using :class:`~prompt_toolkit.PromptSession`'s
:attr:`~prompt_toolkit.PromptSession.bottom_toolbar` feature.

It's used to display the current command, current parameter that requires value. It also shows which parameters of type
of the current command has recieved values and not. It's very helpful to track which parameter needs values, and which does not.
It prints the blue print of the current click command/group in a custom format, to show it's current state of usage in
the prompt.

The bottom bar displays the command's parameters if any of them haven't received their values.

For parameters, these are the formatting style implemented into bottom bar.

* Parameters that haven't received any values will be dipslayed as plain text with no special formatting.

* Parameters that are currently receiving values are represented as bold, underlined text.

* Parameters that have received all of it's necessary values from the prompt are represented as strikethrough text.

It also keeps track of number of arguments that a parameter with `nargs>1` has received.

.. code-block:: python

    import click
    from click_repl import repl


    @click.group()
    @click.pass_context
    def main():
        repl(ctx)

    @main.command()
    @click.option('--student-name')
    @click.argument('marks', nargs=5, type=float)
    def get_marks(student_name, marks):
        ...

<insert image>

BottomBar
---------

This class is responsible for generating text that should be displayed at the bottom bar. It's object returns a
:class:`~click_repl.tokenizer.Marquee` object, which will yield the appropriate chunk of text for every iteration to imitate
the behaviour of `<marquee> <https://developer.mozilla.org/en-US/docs/Web/HTML/Element/marquee>` html tag, to display the text that overflows the terminal window (It's only meant to
scroll the text left and right in the terminal screen).

For more about :class:`~click_repl.tokenizer.Marquee`'s behaviour, Refer from here: :ref:`marquee_class`

Custom BottomBar
----------------

The :class:`~click_repl.bottom_bar.BottomBar` has separate methods to render the metadata about each component of
the click command and their parameters. Therefore, it's easy to override some of it's default behaviour and use your own
bottom bar. Refer to `BottomBar API docs <click_repl.bottom_bar.BottomBar>`_ to look onto those methods.

You can use your own bottom bar class by passing it through ``bottom_toolbar`` key in :class:`~click_repl._repl.repl`'s
``prompt_kwargs`` dictionary. You can send it as an object.

.. code-block:: python

    import click
    from click_repl import repl
    from click_repl.bottombar import BottomBar

    class MyBottomBar(BottomBar):
        # Implement your custom token generation methods.
        ...

    @click.group()
    @click.pass_context
    def main(ctx):
        repl(ctx, prompt_kwargs={
            "bottom_toolbar": MyBottomBar()
        })

.. note::

   The value in ``bottom_toolbar`` should be in a type of
   :obj:`~prompt_toolkit.formatted_text.AnyFormattedText` | :class:`~click_repl.bottom_bar.BottomBar`. The click-repl's
   :class:`~click_repl.bottom_bar.BottomBar` object supplies updated text via it's ``__call__`` method.
   :class:`~prompt_toolkit.PromptSession` will use the bottom bar object's ``__call__`` method to get the text that has to be displayed.
