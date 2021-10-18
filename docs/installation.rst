Installation
============

*deface* has no dependencies outside Python's standard library. It does,
however, require **Python 3.9 or later**.


As Command Line Tool
--------------------

To install *deface* into your current Python environment, simply execute:

.. code-block:: shell

   $ pip install deface-social

That makes the ``deface`` command available in your shell. Try running it:

.. code-block:: shell

   $ deface -V
   deface 1.0.0


As Library
----------

As long you comply by the terms of the license, you can also use *deface* as a
library within your own code. That includes using the model classes to represent
cleaned up and simplified posts. The above instructions for installing *deface*
apply just the same. Just remember to add the dependency to your project's
``requirements.txt`` or ``pyproject.toml``.


For Development
---------------

While *deface* has no runtime dependencies outside Python's standard library, it
does have several buildtime dependencies, e.g., for checking types, generating
documentation, and making a release. Consistent with `PEP 621
<https://www.python.org/dev/peps/pep-0621/>`_, these dependencies are specified
in the ``project.optional-dependencies`` table of ``pyproject.toml``. You can
use any package manager supporting that convention, such as `flit
<https://github.com/takluyver/flit>`_, to install the dependencies.


run.py
^^^^^^

You can also use the ``run.py`` script in the repository root. It automatically
sets up a virtual environment for the project and installs all necessary
buildtime dependencies. From then on out, it ensures that Python scripts execute
within that virtual environment. Even better, you do not need to activate the
virtual environment. ``run.py`` takes care of that for you.

To find out more about supported commands and their options, please check out
``run.py``'s help message:

.. sphinx_argparse_cli::
   :module: run
   :func: create_parser
   :prog: run.py
   :title:
   :group_title_prefix:

.. tip::

   Execute ``./run.py -h`` in your terminal to see the list of supported
   commands and their (short) descriptions.

``run.py`` has commands for all development tasks ranging from initial setup to
making a release. Nonetheless, it has no runtime requirement beyond Python since
it installs all packages needed, including the package manager, itself. At the
same time, it comprises only a little more than 500 well-documented and
well-structured lines of code. Hence you can easily modify existing commands or
add new ones yourself.

To do so, look for the ``@command`` decorator. It registers a function as
implementation of a command with the same name. The function can either take no
arguments — a so-called *simple* command — or arbitrarily many positional
arguments — a so-called *special* command. ``run.py`` can execute any number of
simple commands per invocation. But it can only ever execute one special
command, since ``run.py`` passes through all arguments following the command
name to the implementation.
