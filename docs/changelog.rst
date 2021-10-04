Changelog
=========

**0.8.0** (XXX October, 2021)
  * Support older version of the posts file, which do not contain an array of
    posts but an object whose ``status_updates`` field is that array (*new feature*)
  * Make media objects mergeable if they differ only in one not having comments
    (*new feature*)
  * Tolerate repeated ``event``, ``external_context``, and ``name`` fields if they
    have the same value (*new feature*)
  * Don't unescape the text of unicode escapes starting with two slashes (*bug fix*)
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
