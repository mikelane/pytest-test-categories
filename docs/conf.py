# ruff: noqa: INP001, A001
"""Sphinx configuration for pytest-test-categories documentation."""

from __future__ import annotations

import sys
from pathlib import Path

# Add source directory to path for autodoc
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

# -- Project information -----------------------------------------------------

project = 'pytest-test-categories'
copyright = '2025, Mike Lane'
author = 'Mike Lane'
release = '0.3.0'
version = '0.3.0'

# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
    'sphinx_copybutton',
    'myst_parser',
    'autoapi.extension',
]

# MyST-parser configuration for Markdown support
myst_enable_extensions = [
    'colon_fence',
    'deflist',
    'fieldlist',
    'substitution',
    'tasklist',
]
myst_heading_anchors = 3

# AutoAPI configuration for automatic API documentation
autoapi_type = 'python'
autoapi_dirs = ['../src/pytest_test_categories']
autoapi_root = 'api'
autoapi_options = [
    'members',
    'undoc-members',
    'show-inheritance',
    'show-module-summary',
]
autoapi_ignore = ['**/tests/**', '**/conftest.py']
autoapi_keep_files = True
autoapi_add_toctree_entry = True
autoapi_python_class_content = 'both'
autoapi_member_order = 'groupwise'

# Napoleon configuration for Google-style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_type_aliases = None

# Intersphinx configuration for cross-referencing external docs
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'pytest': ('https://docs.pytest.org/en/stable/', None),
    'pydantic': ('https://docs.pydantic.dev/latest/', None),
}

# Templates and static files
templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', 'planning']

# Source file suffixes
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

# Master document
master_doc = 'index'

# -- Options for HTML output -------------------------------------------------

html_theme = 'furo'
html_static_path = ['_static']
html_title = 'pytest-test-categories'
html_short_title = 'pytest-test-categories'

# Furo theme options
html_theme_options = {
    'sidebar_hide_name': False,
    'navigation_with_keys': True,
    'top_of_page_buttons': ['view', 'edit'],
    'source_repository': 'https://github.com/mikelane/pytest-test-categories/',
    'source_branch': 'main',
    'source_directory': 'docs/',
}

# -- Options for autodoc -----------------------------------------------------

autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__',
}
autodoc_typehints = 'description'
autodoc_class_signature = 'separated'

# -- Options for copybutton --------------------------------------------------

copybutton_prompt_text = r'>>> |\.\.\. |\$ |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: '
copybutton_prompt_is_regexp = True
copybutton_remove_prompts = True

# -- Suppress warnings -------------------------------------------------------

suppress_warnings = [
    'myst.header',
    'autosectionlabel.*',
    'ref.myst',
]

# Suppress autoapi duplicate warnings for re-exported objects
nitpicky = False
