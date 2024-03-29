# Configuration file for the Sphinx documentation builder.

# Project information

from __future__ import annotations

import click_repl

project = "click-repl"
copyright = "2024, Markus Unterwaditzer"
author = "Markus Unterwaditzer"
repo_link = "https://github.com/GhostOps77/click-repl/tree/GhostOps77-patch-1"

version = click_repl.__version__

# General configuration

extensions = [
    "sphinx.ext.duration",
    # "sphinx.ext.doctest",
    "sphinx.ext.linkcode",
    "sphinx.ext.autodoc",
    # 'sphinx.ext.extlinks',
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "autoapi.extension",
    # "sphinx_autodoc_typehints",
]

extlinks = {
    "issue": ("https://github.com/click-contrib/click-repl/issues/%s", "GH-%s"),
}

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
    "python-prompt-toolkit": (
        "https://python-prompt-toolkit.readthedocs.io/en/master/",
        None,
    ),
    "click": ("https://click.palletsprojects.com/en/8.1.x/", None),
}

html_show_sphinx = False
html_context = {"default_mode": "dark"}
html_theme = "furo"

pygments_style = "friendly"

intersphinx_disabled_domains = ["std"]
exclude_patterns = ["_build"]

# html_static_path = ["_static"]
# templates_path = ["_templates"]

autoapi_dirs = ["../../src"]

# autodoc_member_order = 'alphabetical'
autodoc_typehints = "description"
autodoc_typehints_format = "short"

# autoclass_content = 'both'

# Options for EPUB output
epub_show_urls = "footnote"

# Napoleon settings
napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = True
napoleon_include_special_with_doc = False
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = True
napoleon_type_aliases = None
napoleon_attr_annotations = True

# # sphinx-autodoc-typehints settings
# always_document_param_types = True
# typehints_use_signature = True
# typehints_use_signature_return = False


def linkcode_resolve(domain: str, info: dict) -> str:
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
        types.ModuleType
        | types.MethodType
        | types.FunctionType
        | types.TracebackType
        | types.FrameType
        | types.CodeType,
    ):
        try:
            lines, first = inspect.getsourcelines(val)
            last = first + len(lines) - 1
            filename += f"#L{first}-L{last}"
        except (OSError, TypeError):
            pass

    return f"{repo_link}/blob/main/src/{filename}"
