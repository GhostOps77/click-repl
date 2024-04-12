Text as Tokens
==============

click-repl tokenizes the text that should be displayed in suggestions, and in bottom bar, to colorize them based on their
semantic significance and indication of their purpose.

This module uses :class:`~click_repl.tokenizer.TokenizedFormattedText` to display text as tokens.

TokenizedFormattedText
----------------------

:class:`~click_repl.tokenizer.TokenizedFormattedText` class inherits it's functionality from
:class:`~prompt_toolkit.formatted_text.FormattedText`. It also has some of it's own methods that makes it easy to work with
it. This class defines a text along with a token class assigned alongside with it as a **token**. So that you can uniquely
identify this token from other group of text. This tokenization of text is used widely in this module to give syntactic colour
to some of the text. By this, the user can also customize their prompt's colour scheme.

Refer to `Formatted text <https://python-prompt-toolkit.readthedocs.io/en/master/pages/printing_text.html#formatted-text>`_ docs from
:mod:`~prompt_toolkit` to know more about giving unique colour scheme to your text.

:class:`~click_repl.tokenizer.TokenizedFormattedText` objects are used to tokenize the text that goes in
:attr:`~prompt_toolkit.formatted_text.FormattedText.display` and :attr:`~prompt_toolkit.formatted_text.FormattedText.display_meta`
parameters of the :class:`~click_repl.completer.ReplCompletion` class, and also for text that's sent to
:class:`~click_repl.tokenizer.Marquee`.

.. _marquee_class:

Marquee
-------

:class:`~click_repl.tokenizer.Marquee` is responsible for generating text in bottom bar in order to appear in the style of
`<marquee> <https://developer.mozilla.org/en-US/docs/Web/HTML/Element/marquee>`_ html element.

It's constructor has 2 parameters -

* :attr:`~click_repl.tokenizer.Marquee.prefix` - The text that stays at the left most end of the bottom bar, and stays static.

* :attr:`~click_repl.tokenizer.Marquee.text` - This text gets displayed in marquee style as mentioned, if the terminal width is
  not enough to display the whole text. Or else, the whole text will be displayed as static.

.. note::

    Both of these parameters recieve only :class:`~click_repl.tokenizer.TokenizedFormattedText` type objects. And it's expected
    to be, because :class:`~click_repl.tokenizer.TokenizedFormattedText` has special methods to slice the text that's given inside
    the list of tokens.

    Refer to `TokenizedFormattedText API docs <click_repl.tokenizer.TokenizedFormattedText>` to know more about those methods.

Token Class Hierarchy
---------------------

A constant set of token classes are used to label text that's generated from some aspects of this module, and they are
classified in a hierarchy.

* Token class names that labels text that are used for displaying suggestions, comes under the ``autocompletion-menu`` root class,
  by default. Every token class that's used inside :class:`~click_repl.completer.ClickCompleter` comes under this root class.
  The root class can be changed in :attr:`~click_repl.completer.ClickCompleter.parent_token_class_name` attribute of
  :class:`~click_repl.completer.ClickCompleter`.

* Similary, Token class names that labels text that are generated in bottom bar, comes under the ``bottom-bar`` root class, by default.
  The root class can be changed in :attr:`~click_repl.bottombar.BottomBar.parent_token_class_name` attribute of
  :class:`~click_repl.bottombar.BottomBar`.

click-repl has some default styles for text with some tokens. You can override these values in
:meth:`~click_repl._repl.Repl._get_default_prompt_kwargs` method's ``style_config_dict`` parameter.
Each token class is used along with their parent classes. For example, The token ``autocompletion-menu.parameter.option.name``
represents the style format in -

.. code-block::

    autocompletion-menu
    └── parameter
        └── option
            └── name


Token Class Hierarchy Tree
~~~~~~~~~~~~~~~~~~~~~~~~~~

Refer to `(style, text) tuples <https://python-prompt-toolkit.readthedocs.io/en/master/pages/printing_text.html#style-text-tuples>`_ to
know more about the styles that you can use for a text.

For text in suggestions, each of these token classes represent -

| autocompletion-menu - Parent/root class name for token classes that are used in autocompletion
| │
| ├── parameter - :class:`~click.Parameter` based objects
| │   │
| │   └── type - :class:`~click.ParamType` based objects
| │       │
| │       ├── bool - :obj:`~click.BOOL`
| │       │   ├── totrue - option name that has action as ``store_true`` (Default style: ``fg:#44e80e``)
| │       │   └── tofalse - (Default style: ``fg:red``)
| │       │
| │       ├── path - filesystem path (used in :class:`~click.Path` and :class:`~click.File` param types)
| │       │   ├── directory - filesystem path of a directory
| │       │   └── file - filesystem path of a file
| │       │
| │       ├── range - number range based param types
| │       │   ├── integer - :class:`~click.IntRange`
| │       │   └── float - :class:`~click.FloatRange`
| │       │
| │       ├── argument - :class:`~click.Argument`
| │       │   └── name - argument name
| │       │
| │       └── option - :class:`~click.Option`
| │           └── name - option name
| │               └── separator - character that's used to separate joined option names
| │
| ├── command - :class:`~click.Command` based objects
| │   └── name - command name
| │
| ├── group - :class:`~click.Group` based objects
| │   └── name - group name
| │
| ├── internalcommand - `Internal Commands <Internal Commands>`_
| │   └── name - name of the internal command
| │
| ├── symbol - non-alphabetic characters
| │   └── bracket - Brackets and Parentheses
| │
| └── space - space character

For text in bottom bar, each of these token classes represent -

| bottom-bar - Parent/root class name for token classes that are used in bottom bar
| │
| ├── group - :class:`~click.Group` based objects
| │   ├── name - group name (Default style: ``bold``)
| │   ├── type - group object's class name (Default style: ``bold``)
| │   └── metavar - Metavar template text of the group
| │
| ├── command - :class:`~click.Command` based objects
| │   ├── name - command name (Default style: ``bold``)
| │   ├── type - (Default style: ``bold``)
| │   └── metavar - Metavar template text of commands
| │
| ├── paramter - :class:`~click.Parameter` based objects
| │   │
| │   ├── name - name of the parameter
| │   ├── nargs - nargs of the paramter
| │   │   └── counter - `counting option <https://click.palletsprojects.com/en/8.1.x/options/#counting>`_ (Default style: ``fg:green``)
| │   │
| │   ├── usage - usage state of the parameter
| │   │   ├── inuse - parameter is now currently receiving values. (Default style: ``bold underline``)
| │   │   ├── used - parameter has got it's values. (Default style: ``strike``)
| │   │   └── unused - parameter haven't received it's values
| │   │
| │   ├── type - :class:`~click.ParamType` based objects
| │   │   │
| │   │   ├── usage - usage state of the param type
| │   │   │   ├── inuse - parameter is now currently receiving values. (Default style: ``bold underline``)
| │   │   │   ├── used - parameter has got it's values. (Default style: ``strike``)
| │   │   │   └── unused - parameter haven't received it's values
| │   │   │
| │   │   ├── string - :obj:`~click.STRING`
| │   │   ├── integer - :obj:`~click.INT`
| │   │   ├── float - :obj:`~click.FLOAT`
| │   │   ├── range - number range based param types
| │   │   │   ├── integer - :class:`~click.IntRange`
| │   │   │   ├── float - :class:`~click.FloatRange`
| │   │   │   └── descriptor - description text about the number range based param type
| │   │   │
| │   │   ├── bool - :obj:`~click.BOOL`
| │   │   ├── choice - :class:`~click.Choice`
| │   │   ├── composite - :class:`~click.types.CompositeParamType`
| │   │   ├── datetime - :class:`~click.DateTime`
| │   │   ├── file - :class:`~click.File`
| │   │   ├── path - :class:`~click.Path`
| │   │   ├── unprocessed - :class:`~click.UNPROCESSED`
| │   │   └── uuid - :class:`~click.UUID`
| │   │
| │   ├── argument - :class:`~click.Argument`
| │   │   └── name - argument name
| │   │
| │   └── option - :class:`~click.Option`
| │       └── name - option name
| │
| ├── symbol - non-alphabetic characters
| │   └── bracket - Brackets and Parentheses
| │
| ├── space - space character
| └── ellipsis - Ellipsis (``...``) text that's used to represent ``None`` values
