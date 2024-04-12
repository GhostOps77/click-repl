Validator
=========

click-repl uses :class:`~prompt_toolkit.valdiator.Validator` as a base class to Implement it's validator
(:class:`~click_repl.validator.ClickValidator`), to validate the user input.
It uses :class:`~click_repl.validator.ClickValidator` by default.

This utility displays the errors that are raised while generating autocompletion, in the form of text in bottom bar
with red background. It can be also used to verify input text from the prompt while typing.
The prompt will not accept the input if the validator reports that it's in an invalid format.

This is mostly useful for dislaying :exc:`~click.exceptions.UsageError` exception's formatted message from it's
:meth:`~click.exceptions.UsageError.format_message` method.

.. code-block:: python

    import click
    from click_repl import repl

    @click.group()
    @click.pass_context
    def main():
        pass

    @main.command()
    @click.argument('num', type=int)
    @click.option('--error', shell_complete=mock_error_during_shell_complete)
        def get_number(num):
        print(num)

    main()

<insert image>

Custom Validator
----------------

You can make your own valdiator class. And in order to use it, pass it into the :func:`~click_repl._repl.repl`
function's ``validator_cls`` parameter. Passing in the class alone will supply it's constructor with
necessary values to it's parameters.

.. note::

	Make sure to use :class:`click_repl.validator.ClickValidator` as base class in order to make your custom validtor work with repl.

.. code-block:: python

	import click

	from click_repl import repl
	from click_repl.validator import ClickValidator


	class MyValidator(ClickValidator):
		def validate(self, document):
			# Implement your logic on validating input text in prompt.
			...


	@click.group()
	@click.pass_context
	def main():
		repl(ctx, validator_cls=MyValidator)  # Now, it'll use custom validator.

You can also disable it in the same way, by passing in ``None`` to the ``validator_cls`` parameter.

.. code-block:: python

	@click.group()
	@click.pass_context
	def main():
		repl(ctx, validator_cls=None)  # No validation is done during typing in prompt.

This disables the usage of validator. Therefore, no validation of input is done while typing in prompt.

Validator kwargs
----------------

If you want to pass in extra keyword arguments to the validator, you can pass it through ``validator_kwargs`` parameter
of :func:`~click_repl._repl.repl` function.

.. code-block:: python

	@click.group()
	@click.pass_context
	def main():
		repl(ctx, validator_cls=MyValidator, validator_kwargs={
            # Your extra keyword arguments goes here.
            'display_all_errors': False
            ...
        })

This keyword arguments dictionary will be updated with the default keyword arguments of validator, that will be supplied
to the validator while initializing the repl. The default arguments for :class:`~click-repl.validator.ClickValidator` are -

    #. ``ctx`` - :class:`~click.Context` of the invoked group.
    #. ``internal_command_system`` - :class:`~click_repl.internal_commands.InternalCommandSystem` object of the current repl session.

These default values are supplied from :meth:`~click_repl._repl.Repl._get_default_validator_kwargs` method.

Display all errors
------------------

By default, :class:`~click_repl.validator.ClickValidator` displays all the exceptions, that are raised while typing in prompt,
in validator bar, including generic python exceptions.

In order to change this default behaviour, set ``display_all_errors`` parameter to ``False`` in the validator kwargs.
The flag :attr:`~click_repl.validator.ClickValidator.display_all_errors` determines whether to raise generic
Python Exceptions, and not to display them in the validator bar, resulting in the full error traceback being
redirected to a log file in the REPL mode.

By default it's ``True``, which means, All errors raised while typing in prompt are
displayed in the validator bar. If not, Error tracebacks are displayed during the REPL, interrupting the prompt.
The error traceback and messages are also logged into ``.click-repl-err.log`` file.

.. note::

    The :class:`~click_repl.validator.ClickValidator` displays all the exceptions from click module
    (:exc:`~click.exceptions.ClickException` based exceptions) in validator bar, by default. This flag has no effect on it.
    It only applies to exceptions that are not a sub-class of :exc:`~click.exceptions.ClickException`.

.. code-block:: python

    @click.group()
    @click.pass_context
    def main():
        repl(ctx, validator_kwargs={
            'display_all_errors': False
        })

    def mock_error_during_shell_complete(ctx, param, incomplete):
        raise ValueError("mocking error during shell complete")

    @main.command()
    @click.argument('num', type=int)
    @click.option('--error', shell_complete=mock_error_during_shell_complete)
    def get_number(num):
        print(num)

<insert image>
