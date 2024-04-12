Text as Tokens
==============

click-repl employs tokenization to represent text for suggestions and the bottom bar,
enabling semantic coloring based on their significance and purpose.

This module uses the :class:`~click_repl.tokenizer.TokenizedFormattedText` class to achieve this.

TokenizedFormattedText
----------------------

The :class:`~click_repl.tokenizer.TokenizedFormattedText` class inherits its functionality from
:class:`~prompt_toolkit.formatted_text.FormattedText`. It extends it with additional methods to
facilitate easier manipulation. This class defines text along with an assigned token class assigned
as a **token** to uniquely identify from other text groups. This text tokenization is widely
used in this module to give semantic colouring to certain text portions.
Consequently, users can customize their prompt's color scheme accordingly.

Refer to `Formatted text <https://python-prompt-toolkit.readthedocs.io/en/master/pages/printing_text.html#formatted-text>`_ docs from
the `python-prompt-toolkit <https://python-prompt-toolkit.readthedocs.io/en/master/>`_ module to learn more about
creating unique colour schemes for your text.

:class:`~click_repl.tokenizer.TokenizedFormattedText` objects are used to tokenize the text that goes in
:attr:`~prompt_toolkit.completion.Completion.display` and :attr:`~prompt_toolkit.completion.Completion.display_meta`
parameters of the :class:`~click_repl.completer.ReplCompletion` class, and also for text sent to
the :class:`~click_repl.tokenizer.Marquee` class.

.. _marquee_class:

Marquee
-------

:class:`~click_repl.tokenizer.Marquee` is responsible for generating text in the bottom bar to appear in the style of
`<marquee> <https://developer.mozilla.org/en-US/docs/Web/HTML/Element/marquee>`_ html element.

It's constructor has 2 parameters -

* :attr:`~click_repl.tokenizer.Marquee.prefix` - The text that remains at the left-most end of the bottom bar, and remains static.

* :attr:`~click_repl.tokenizer.Marquee.text` - This text gets displayed in marquee style if the terminal width is
  insufficient to display the entire text. Otherwise, the entire text is displayed statically.

.. note::

    Both of these parameters expect to recieve only objects of type :class:`~click_repl.tokenizer.TokenizedFormattedText`,
    because it uses :class:`~click_repl.tokenizer.TokenizedFormattedText`'s special methods to slice the text provided within
    the list of tokens.

    Refer to `TokenizedFormattedText API docs <click_repl.tokenizer.TokenizedFormattedText>` to learn more about those methods.

Token Class Hierarchy
---------------------

A constant set of token classes is used to label text generated from various aspects of this module, and they are
classified in a hierarchy.

* Token class names labelling text that are used for displaying suggestions fall under the ``autocompletion-menu`` root class
  by default. Every token class used within :class:`~click_repl.completer.ClickCompleter` falls under this root class.
  The root class can be changed in the :attr:`~click_repl.completer.ClickCompleter.parent_token_class_name` attribute of
  :class:`~click_repl.completer.ClickCompleter`.

* Similary, Token class names labeling text that are generated in bottom bar, falls under the ``bottom-bar`` root class by default.
  The root class can be changed in the :attr:`~click_repl.bottom_bar.BottomBar.parent_token_class_name` attribute of
  :class:`~click_repl.bottom_bar.BottomBar`.

click-repl has default styles for text with certain tokens. These values can be overridden in the
``style_config_dict`` parameter of the :meth:`~click_repl._repl.Repl.get_default_prompt_kwargs` method.

Each token class is used along with its parent classes.
For example, The token ``autocompletion-menu.parameter.option.name`` represents the below style format hierarchy:

.. code-block::

    autocompletion-menu
    └─ parameter
       └─ option
          └─ name


This implies that the token that has class ``autocompletion-menu.parameter.option.name`` inherits its style from
the classes ``autocompletion-menu``, ``parameter``, ``option``, and ``name``. However, each parent class's style
can be overridden by its child token class. In other words, the style configuration defined for
``autocompletion-menu`` can be overridden in ``parameter``, ``option``, or ``name`` classes.


.. note::

   * The default style configurations for tokens in auto-completions, bottom bar are defined in
     :obj:`~click_repl.styles.DEFAULT_COMPLETION_STYLE_CONFIG`, and
     :obj:`~click_repl.styles.DEFAULT_BOTTOMBAR_STYLE_CONFIG` respectfully.

   * And the default style configurations for :class:`~prompt_toolkit.shortcuts.PromptSession` are
     in :obj:`~click_repl.styles.DEFAULT_PROMPTSESSION_STYLE_CONFIG`.


Token Class Hierarchy Tree
~~~~~~~~~~~~~~~~~~~~~~~~~~

Refer to `(style, text) tuples <https://python-prompt-toolkit.readthedocs.io/en/master/pages/printing_text.html#style-text-tuples>`_ to
learn more about the styles that you can use for text.

For text in suggestions, each of these token classes represent:

.. parsed-literal::

   autocompletion-menu - Parent/root class name for token classes that are used in autocompletion
   │
   ├─ parameter - :class:`~click.Parameter` based objects
   │  │
   │  └─ type - :class:`~click.ParamType` based objects
   │     │
   │     ├─ bool - :obj:`~click.BOOL`
   │     │  ├─ totrue - Option name that has action as ``store_true`` (Default style: ``fg:#44e80e``)
   │     │  └─ tofalse - Option name that has action as ``store_false`` (Default style: ``fg:red``)
   │     │
   │     ├─ path - Filesystem path (used in :class:`~click.Path` and :class:`~click.File` param types)
   │     │  ├─ directory - Filesystem path of a directory
   │     │  └─ file - Filesystem path of a file
   │     │
   │     ├─ range - Number Range based param types
   │     │  ├─ integer - :class:`~click.IntRange` object
   │     │  └─ float - :class:`~click.FloatRange` object
   │     │
   │     ├─ argument - :class:`~click.Argument` object
   │     │  └─ name - Argument name
   │     │
   │     └─ option - :class:`~click.Option` object
   │        └─ name - Option name
   │           └─ separator - Character that's used to separate joined option names
   │
   ├─ command - :class:`~click.Command` based objects
   │  └─ name - Command name
   │
   ├─ group - :class:`~click.Group` based objects
   │  └─ name - Group name
   │
   ├─ internalcommand - `Internal Commands <Internal Commands>`_
   │  └─ name - Name of the internal command
   │
   ├─ symbol - Non-alphanumeric characters
   │  └─ bracket - Brackets and Parentheses
   │
   └─ space - Space character

For text in bottom bar, each of these token classes represent:

.. parsed-literal::

   bottom-bar - Parent/root class name for token classes that are used in bottom bar
   │
   ├─ group - :class:`~click.Group` based objects
   │  ├─ name - Group name (Default style: ``bold``)
   │  ├─ type - Group object's class name (Default style: ``bold``)
   │  └─ metavar - Metavar template text of the group
   │
   ├─ command - :class:`~click.Command` based objects
   │  ├─ name - Command name (Default style: ``bold``)
   │  ├─ type - (Default style: ``bold``)
   │  └─ metavar - Metavar template text of commands
   │
   ├─ paramter - :class:`~click.Parameter` based objects
   │  │
   │  ├─ name - Name of the parameter
   │  ├─ nargs - nargs of the paramter
   │  │  └─ counter - `counting option <https://click.palletsprojects.com/en/8.1.x/options/#counting>`_ (Default style: ``fg:green``)
   │  │
   │  ├─ usage - Usage state of the parameter
   │  │  ├─ inuse - Parameter is now currently receiving values (Default style: ``bold underline``)
   │  │  ├─ used - Parameter has got its values (Default style: ``strike``)
   │  │  └─ unused - Parameter haven't received its values
   │  │
   │  ├─ type - :class:`~click.ParamType` based objects
   │  │  │
   │  │  ├─ usage - Usage state of the param type
   │  │  │  ├─ inuse - Parameter is now currently receiving values. (Default style: ``bold underline``)
   │  │  │  ├─ used - Parameter has got its values. (Default style: ``strike``)
   │  │  │  └─ unused - Parameter haven't received its values
   │  │  │
   │  │  ├─ string - :obj:`~click.STRING` object
   │  │  ├─ integer - :obj:`~click.INT` object
   │  │  ├─ float - :obj:`~click.FLOAT` object
   │  │  ├─ range - Number Range based param types
   │  │  │  ├─ integer - :class:`~click.IntRange` object
   │  │  │  ├─ float - :class:`~click.FloatRange` object
   │  │  │  └─ descriptor - Description text about the number range based param type
   │  │  │
   │  │  ├─ bool - :obj:`~click.BOOL` object
   │  │  ├─ choice - :class:`~click.Choice` object
   │  │  ├─ composite - :class:`~click.types.CompositeParamType` objects
   │  │  ├─ datetime - :class:`~click.DateTime` object
   │  │  ├─ file - :class:`~click.File` object
   │  │  ├─ path - :class:`~click.Path` object
   │  │  ├─ unprocessed - :obj:`~click.UNPROCESSED` object
   │  │  └─ uuid - :obj:`~click.UUID` object
   │  │
   │  ├─ argument - :class:`~click.Argument` object
   │  │  └─ name - Argument name
   │  │
   │  └─ option - :class:`~click.Option` object
   │     └─ name - Option name
   │
   ├─ symbol - Non-alphanumeric characters
   │  └─ bracket - Brackets and Parentheses
   │
   ├─ error - Errors that are raised while generating auto-completions
   │  ├─ exception-class-name - Class name of the Exception raised
   │  └─ message - Message in the Exception class
   │
   ├─ space - Space character
   └─ ellipsis - Ellipsis (``...``) text that's used to represent :obj:`None` values
