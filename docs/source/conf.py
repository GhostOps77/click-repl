from __future__ import annotations

import typing as t

import click_repl

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx


project = "click-repl"
author = "Markus Unterwaditzer"
repo_link = "https://github.com/GhostOps77/click-repl"
repo_branch = "GhostOps77-patch-1"
version = click_repl.__version__

# General configuration

extensions = [
    "sphinx.ext.duration",
    # "sphinx.ext.doctest",
    "notfound.extension",
    "sphinx.ext.linkcode",
    "sphinx.ext.autodoc",
    "sphinx_copybutton",
    "sphinx.ext.extlinks",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "autoapi.extension",
    # "sphinxnotes.strike",
    # "myst_parser",
    # "sphinx_autodoc_typehints",
]

extlinks = {
    "issue": ("https://github.com/click-contrib/click-repl/issues/%s", "#%s"),
}


intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
    "python-prompt-toolkit": (
        "https://python-prompt-toolkit.readthedocs.io/en/master/",
        None,
    ),
    "click": ("https://click.palletsprojects.com/en/8.1.x/", None),
    "typing_extensions": ("https://typing-extensions.readthedocs.io/en/latest/", None),
}

html_experimental_html5_writer = True
html_show_sphinx = False
html_context = {"default_mode": "dark"}
html_title = "click-repl Documentation"
html_theme = "furo"
# html_static_path = ["_static"]
# templates_path = ["_templates"]
source_suffix = ".rst"

html_theme_options = {
    "footer_icons": [
        {
            "name": "GitHub",
            "url": "https://github.com/GhostOps77/click-repl/tree/GhostOps77-patch-1",
            "html": """
                <svg stroke="currentColor" fill="currentColor" stroke-width="0" viewBox="0 0 16 16">
                    <path fill-rule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"></path>
                </svg>
            """,
            "class": "",
        },
    ],
}

pygments_style = "friendly"

intersphinx_disabled_domains = ["std"]
exclude_patterns = ["build", "_build", "Thumbs.db", ".DS_Store"]


# autodoc_member_order = 'alphabetical'
autoapi_dirs = ["../../src/click_repl/"]
autoapi_python_use_implicit_namespaces = True

# autodoc_type_aliases = {}
autodoc_typehints_format = "short"
autodoc_default_options = {
    "special-members": False,
}

# Options for EPUB output
epub_show_urls = "footnote"

# Napoleon settings
napoleon_google_docstring = False
# napoleon_numpy_docstring = True
# napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = False
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = False
napoleon_preprocess_types = True
napoleon_type_aliases = None
napoleon_attr_annotations = True

# # sphinx-autodoc-typehints settings
# always_document_param_types = True
# typehints_use_signature = True
# typehints_use_signature_return = False

# myst config
# myst_enable_extensions = [
#     "dollarmath",
#     "amsmath",
#     "deflist",
#     "fieldlist",
#     "html_admonition",
#     "html_image",
#     "colon_fence",
#     "smartquotes",
#     "replacements",
#     "linkify",
#     "strikethrough",
#     "substitution",
#     "tasklist",
#     "attrs_inline",
#     "attrs_block",
# ]
# myst_heading_anchors = 2


# def setup(app: Sphinx):
#     """Add functions to the Sphinx setup."""
#     from myst_parser._docs import (
#         DirectiveDoc,
#         DocutilsCliHelpDirective,
#         MystAdmonitionDirective,
#         MystConfigDirective,
#         MystExampleDirective,
#         MystLexer,
#         MystToHTMLDirective,
#         MystWarningsDirective,
#         NumberSections,
#         StripUnsupportedLatex,
#     )

#     app.add_directive("myst-config", MystConfigDirective)
#     app.add_directive("docutils-cli-help", DocutilsCliHelpDirective)
#     app.add_directive("doc-directive", DirectiveDoc)
#     app.add_directive("myst-warnings", MystWarningsDirective)
#     app.add_directive("myst-example", MystExampleDirective)
#     app.add_directive("myst-admonitions", MystAdmonitionDirective)
#     app.add_directive("myst-to-html", MystToHTMLDirective)
#     app.add_post_transform(StripUnsupportedLatex)
#     app.add_post_transform(NumberSections)
#     # app.connect("html-page-context", add_version_to_css)
#     app.add_lexer("myst", MystLexer)


# def autoapi_skip_member(app, what, name, obj, skip, options):
#     """Exclude all private attributes, methods, and dunder methods from Sphinx."""
#     import re

#     exclude = re.match(r"\._.[^.]*__$", name)  # and what != 'module'
#     return skip or exclude


def autodoc_skip_member(app: Sphinx, what, name: str, obj: t.Any, skip: bool, options):
    # print(f'{name = }')
    import re

    if skip:
        return True

    exclude = re.findall(r"\._.*__$", str(obj)) and what != "module"
    return exclude


def setup(app: Sphinx):
    # app.connect('autoapi-skip-member', autoapi_skip_member)
    app.connect("autodoc-skip-member", autodoc_skip_member)


def linkcode_resolve(domain: str, info: dict[str, str]) -> str:
    """linkcode_resolve."""
    if domain != "py":
        return None

    if not info["module"]:
        return None

    import importlib
    import inspect
    import types

    mod = importlib.import_module(info["module"])

    val = mod
    for k in info["fullname"].split("."):
        val = getattr(val, k, None)
        if val is None:
            break

    filename = info["module"].replace(".", "/") + ".py"

    if isinstance(
        val,
        (
            types.ModuleType,
            types.MethodType,
            types.FunctionType,
            types.TracebackType,
            types.FrameType,
            types.CodeType,
        ),
    ):
        try:
            lines, first = inspect.getsourcelines(val)
            last = first + len(lines) - 1
            filename += f"#L{first}-L{last}"
        except (OSError, TypeError):
            pass

    return f"{repo_link}/blob/{repo_branch}/src/{filename}"
