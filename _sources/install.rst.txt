Installation
============

*deface* has no dependencies outside Python's standard library. It does,
however, require **Python 3.9 or later**.

To install *deface* into your current Python environment, simply execute:

.. code-block:: shell

   $ pip install deface-social

That makes the ``deface`` command available in your shell. Try running it:

.. code-block:: shell

   $ deface -V
   deface 1.0.0


Use as Library
--------------

As long you comply by the terms of the license, you can also use *deface* as a
library within your own code. Notably, that enables you to use the model classes
for representing cleaned up and simplified posts. To this end, you install the
package just the same. Just remember to add the dependency to your project's
``requirements.txt`` or ``pyproject.toml``.


Modify Source Code
------------------

While *deface* has no runtime dependencies outside Python's standard library, it
does have several buildtime dependencies, e.g., for checking types, generating
documentation, and making a release. Consistent with `PEP 621
<https://www.python.org/dev/peps/pep-0621/>`_, these dependencies are specified
in the ``project.optional-dependencies`` table of ``pyproject.toml``. You can
use any package manager supporting that convention, such as `flit
<https://github.com/takluyver/flit>`_, to install the dependencies.


run.py
^^^^^^

You can also use the ``run.py`` script in the repository root. Unless you are
already running the script in a virtual environment, it automatically bootstraps
a virtual environment for the project and installs all necessary
development-only dependencies. From then on out, it ensures that Python scripts
execute within the virtual environment, even if the commands are not obviously
written in Python. You do not need to activate the virtual environment as long
as you use ``run.py`` for running tasks.

To find out more about supported commands and their options, please check out
``run.py``'s help message:

.. sphinx_argparse_cli::
   :module: run
   :func: create_parser
   :prog: run.py
   :title:
   :group_title_prefix:

*See actual help message of* ``run.py`` *for description of commands.*

``run.py`` has commands for all development tasks from bootstrap to making a
release. Yet it also has *no* external dependencies (beyond Python and pip) and
comprises a little more than 500 well-documented and -structured lines of code.
Hence, if the need arises, you can easily modify existing commands or add
entirely new ones yourself.

To do so, look for the ``@command`` decorator. It registers a function as
implementation for a command of the same name. The function can either take no
arguments — a so-called *simple* command — or arbitrarily many positional
arguments — a so-called *special* command. ``run.py`` can execute any number of
simple commands per invocation. But it can only ever execute one special
command, since that command receives all arguments following the command name.
