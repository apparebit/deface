# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys


# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(1, os.path.abspath('sphinx_extensions'))

import deface

# sphinx.ext.linkcode generates links to source code and defers to an inscope
# linkcode_resolve() for producing actual URLs. Let's create that function.
from github_link import make_linkcode_resolve  # type: ignore
linkcode_resolve = make_linkcode_resolve('apparebit', 'deface')  # type: ignore


# -- Project information -----------------------------------------------------

project = 'deface'
copyright = '2021, Robert Grimm'
author = 'Robert Grimm'

# The major and minor version only.
version = '.'.join(deface.__version__.split('.')[:2])

# The full version, including alpha/beta/rc tags
release = deface.__version__


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
  # Builtin
  'sphinx.ext.autodoc',
  'sphinx.ext.coverage',
  'sphinx.ext.duration',
  'sphinx.ext.githubpages',
  'sphinx.ext.linkcode',
  # External
  'sphinx_argparse_cli',
  'sphinxext.opengraph'
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# Source order is nicer than alphabetizing fields and methods.
autodoc_member_order = 'bysource'

# Known types are linked, so the fully qualified name adds mostly noise.
python_use_unqualified_type_names = True

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'furo'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
