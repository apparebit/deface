Design Principles
=================

The design and implementation of **deface** adhere to three principles:

1. Preserve independent semantic concepts as records. Also preserve all key,
   value pairs within those records. Critically, the immediate key of a
   semantically relevant value does not change.
2. Simplify the data: Eliminate unnecessary structure as well as obviously
   redundant values. The latter may involve reconciling fields with different
   names in different records.
3. Strictly validate all inputs and fail immediately when data diverges from
   expectation. The presence of unknown or unexpected fields must trigger a
   validation failure.

As already implied by their ordering, preservation of data takes precedence over
simplification. However, the preservation principle applies only to Objects
representing semantic concepts as well as the leaves of the JSON graph, i.e.,
keys with scalar values. That is very much intentional, since the posts data
provided by Facebook is a rather wasteful, encoding of that information.
Notably, posts have up to two top-level fields, ``annotations`` and ``data``,
whose values are lists of singleton objects representing the fields of a record.
Similarly, locations have a nested ``coordinates`` object with the ``latitude``
and ``longitude``. In contrast, under **deface**'s data model, the
:py:class:`deface.model.Post` and :py:class:`deface.model.Location` records are
flat, which reduces storage overheads and simplifies traversal.

While the elimination of deep nesting is straight-forward, the elimination of
redundant values is more difficult: Leave no information behind! Nonetheless,
**deface** can still eliminate significant repetition in the data provided by
Facebook. Notably, when several posts have the exact same fields with the exact
same values but differ in their media records, they are combined into a single
post with only one copy of all fields. Furthermore, if *all* of a post's media
records have the same description and the post has no body, the repeated
descriptions are removed and effectively hoisted up to the post. Similarly, if a
media record's description is the same as the post's body, the description is
removed. In all cases, no information is lost since posts, as written and
displayed on Facebook, don't repeat the description either. The redundancy
simply is an artifact of Facebook's rather strange encoding for personal data
archives.

This emphasis on data safety is also reflected in the third principle. Unlike
serialization formats such as `protocol buffers
<https://developers.google.com/protocol-buffers>`_ with their clever rules for
compatible schema evolution, **deface** explicitly mandates a more conservative
approach to change management. Facebook changing the schema of personal data
archives always requires attendant changes to this package's implementation.
However, a validation failure in one post doesn't prevent the processing of the
remaining posts, which are independent. Instead, the implementation accumulates
validation errors and returns them with the successfully ingested data. By
default, the command-line tool refuses to export the partial data to prevent
data loss.
