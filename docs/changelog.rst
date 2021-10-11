Changelog
=========

**0.9.0** (xx October, 2021)
  * Refactor non-model code from :py:mod:`deface.model` into :py:mod:`deface.ingest`
    (*code quality*)
  * Add ``HOME`` to subprocess environment in ``run.py`` so that git finds
    configuration (*bug fix*)
  * Replace ``deface`` command with more general ``run`` in ``run.py`` (*tooling*)

**0.8.0** (7 October, 2021)
  * Support older version of posts file, which does not contain an array of posts
    but an object whose ``status_updates`` field is that array (*new feature*)
  * Make media objects mergeable if they differ only in one not having comments
    (*new feature*)
  * Tolerate repeated ``event``, ``external_context``, and ``name`` fields if they
    have the same value (*new feature*)
  * Don't unescape ``\u00xx`` if preceded by an uneven number of backslashes; it is
    not an instance of Facebook's broken encoding but rather of text discussing the
    broken encoding on Facebook (*bug fix*)
  * Simplify code in ``run.py`` (*code quality*)

**0.7.0** (21 September, 2021)
  * Add validations to ``run.py`` (*code quality*)
  * Refactor ``run.py``'s utility functions into namespaces (*code quality*)
  * Generally improve documentation (*documentation*)

**0.6.0** (18 September, 2021)
  * Add ability to deserialize post model from JSON (*new feature*)
  * Actually output posts in chronological order (*bug fix*)
  * Add ``run.py`` to bootstrap development and run build tasks (*tooling*)
  * Increase test coverage for post ingestion (*code quality*)

**0.5.0** (8 September, 2021)
  Initial release
