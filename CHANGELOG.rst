~==============
Change History
==============

v0.3.0
------

| **Release-date**: 15 Jun, 2023
| **Release-by**: `Asif Saif Uddin <https://github.com/auvipy>`_

- Drop Python 2 support, removed `six <https://github.com/benjaminp/six>`. :issue:`78`
- Uses :class:`~prompt_toolkit.shortcuts.PromptSession` class from prompt_toolkit instead of :func:`~prompt_toolkit.prompt` function (:issue:`63`).
- Added filter for hidden commands and options (:issue:`86`).
- Added click's autocompletion support (:issue:`88`).
- Added tab-completion for :class:`~click.Path` and :obj:`~click.BOOL` type arguments (:issue:`95`).
- Added 'expand environmental variables in path' feature (:issue:`96`).
- Delegate command dispatching to the actual group command.
- Updated completer class and tests based on new fix :issue:`92` (:issue:`102`).
- Python 3.11 support.


v0.2.0
------

| **Release-date**: 31 May, 2021
| **Release-by**: `untitaker <https://github.com/untitaker>`_

- Backwards compatibility between click v7 & v8
- support for click v8 changes
- Update tests to expect hyphens
