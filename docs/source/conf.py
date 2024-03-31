# Configuration file for the Sphinx documentation builder.

# Project information

from __future__ import annotations

import click_repl

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

html_show_sphinx = False
html_context = {"default_mode": "dark"}
html_theme = "furo"

pygments_style = "friendly"

intersphinx_disabled_domains = ["std"]
exclude_patterns = ["build", "_build", "Thumbs.db", ".DS_Store"]

# html_static_path = ["_static"]
# templates_path = ["_templates"]

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
