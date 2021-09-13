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

If you want to use *deface* as a library from within your own code, you
install the package just the same. Just remember to add the dependency to your
project's ``requirements.txt`` or ``pyproject.toml``.


Modify deface
-------------

While *deface* has no runtime dependencies outside Python's standard library, it
does have several buildtime dependencies, e.g., for checking types, generating
documentation, and making a release. Consistent with `PEP 621
<https://www.python.org/dev/peps/pep-0621/>`_, these dependencies are specified
in the ``project.optional-dependencies`` table of ``pyproject.toml``. You can
use any package manager supporting that convention, such as `flit
<https://github.com/takluyver/flit>`_, to install the dependencies.

The repository's root includes the ``run.py`` script as a lightweight build
tool. Have a look at its help message:

.. code-block:: shell

   $ ./run.py -h
   usage: run.py [-h] [--color | --no-color] [-v] COMMAND [COMMAND ...]

   supported commands:
   ...

If you try this yourself, you will see that ``run.py`` has commands for all
common development tasks including making releases. At the same time, its
implementation comprises less than 300 lines of well-documented code and thus is
easily modifyable. That is only possible because ``run.py``, as hinted at by its
name, delegates the heavy lifting to other tools. The goal is to bootstrap these
tools through ``run.py`` as well, even when starting with a fresh Python
installation.
