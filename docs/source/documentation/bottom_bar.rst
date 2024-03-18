Bottom Bar
==========

click-repl displays a bottom bar, made by using :class:`~prompt_toolkit.PromptSession`'s
:attr:`~prompt_toolkit.PromptSession.bottom_toolbar` feature.

It's used to display the current command, current parameter that requires value. It also shows which parameters of type
of the current command has recieved values and not. It's very helpful to track which parameter needs values, and which does not.
It prints the blue print of the current click command/group in a custom format, to show it's current state of usage in
the prompt.

The bottom bar displays the command's parameters if any of them haven't received their values.

For parameters, these are the formatting style implemented into bottom bar.

    * Parameters that haven't received any values will be dipslayed as plain text with no special formatting.

    * Parameters that are currently receiving values are represented as bold, underlined **text**.

    * Parameters that have received all of it's necessary values from the prompt are represented as strikethrough :strike:`text`.

It also keeps track of number of arguments that a parameter with nargs>1 has received.

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

:class:`~click_repl.bottombar.BottomBar`
----------------------------------------

This class is responsible for generating text that should be displayed at the bottom bar. It's object returns a
:class:`~click_repl.formatting.Marquee` object, which will yield the appropriate chunk of text for every iteration to imitate
the behaviour of ``<marquee></marquee>`` html tag, to display the text that overflows the terminal window.

For more about it's behaviour, Refer from here: `Marquee <marquee>`_
