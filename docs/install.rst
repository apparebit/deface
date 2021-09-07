Installation
============

*deface* has no dependencies outside Python's standard library. It does,
however, require **Python 3.9 or later**.

To install *deface* into your current Python environment, simply execute:

.. code-block:: shell

   $ pip install ???

That makes the ``deface`` command available in your shell. Try running it:

.. code-block:: shell

   $ deface -V
   deface 1.0.0


Use as Library
--------------

If you want to use *deface* as a library from within your own code, you
install the package just the same. Just remember to add the dependency to your
project's ``requirements.txt`` or ``pyproject.toml``.


Develop deface
--------------

If you want to modify *deface* itself, you need to fork the repository. The
development setup relies on a few extra tools, notably ``pytest`` and ``mypy``
for testing and ``sphinx-build`` with a couple of third-party extensions for
document generation. Consistent with `PEP 621
<https://www.python.org/dev/peps/pep-0621/>`_, they are specified in
``pyproject.toml``. Currently, that limits you to `flit
<https://github.com/takluyver/flit>`_ for easily installing them.
