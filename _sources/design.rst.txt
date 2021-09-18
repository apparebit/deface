Design Considerations
=====================

.. tip::

   This page explains how *deface* simplifies the data and eliminates redundant
   fields while ensuring that all content is preserved. It may be more
   approachable if you first run the tool and compare input to output.

The design and implementation of *deface* adhere to three principles:

1. Preserve independent semantic concepts as records. Also preserve all key,
   value pairs within those records. Critically, the immediate key of a
   semantically relevant value does not change.
2. Simplify the data: Eliminate unnecessary structure as well as obviously
   redundant values. The latter may involve reconciling fields with different
   names in different records.
3. Strictly validate all inputs and fail immediately when data diverges from
   expectation. The presence of unknown or unexpected fields must trigger a
   validation failure.

The preservation principle applies to the leaves of the JSON graph, that is,
keys with scalar values including text, and to interior nodes that are
meaningful in the domain of social media posts, e.g., not only posts themselves
but also media, events, or locations. At the same time, they do not include
artifacts of Facebook's fairly elaborate JSON encoding. For example, a post's
``attachments`` and ``data`` keys, if present, have lists of singleton objects
as values. Each nested singleton object is a key, value pair representing a
property of the post, with some keys appearing in multiple singleton objects to
specify multiple values.

.. code-block:: json

  {
    "timestamp": 946684799,
    "data": [
      {
        "post": "Let's party like it's 1999!"
      },
      {
        "update_timestamp": 946684800
      }
    ]
  }

The obvious and more concise alternative is to add all keys to the post object
itself and to use lists of values where the more elaborate encoding repeats a
key.

.. code-block:: json

  {
    "timestamp": 946684799,
    "post": "Let's party like it's 1999!",
    "update_timestamp": 946684800
  }

The simplification principle also applies to the ``attachments`` and ``data``
introduced above because they aren't meaningful in the domain of social media
posts. A more subtle application of the simplification principle are places in
the original Facebook post data: Such locations are included amongst a post's
attachments and their ``coordinate`` attributes are nested objects with the
``latitude`` and ``longitude``. Since coordinates and locations are related
rather than independent concepts, the simplification principle does apply. The
corresponding transform removes the nested object after hoisting its contents
into the outer object.

In addition to the encoding being already rather elaborate, Facebook's post data
contains a surprising amount of duplicated data. For example:

* Posts containing several photos and/or videos may be represented as that many
  post objects with identical ``timestamp`` and ``post`` body but different
  media objects describing those photos and/or videos.
* All of a post's media objects may have the same ``description``, which may
  also be the same as the ``post`` body.
* Very few posts have more than one place. If they do, they usually have two
  locations that differ only in ``url``, with one location object having
  ``None`` and the other having a string value.

In all these cases, the simplification principle applies, but the implementation
must take care to preserve all information. For example, when combining media
objects, that means distinguishing them by ``uri``, the path to the actual photo
or video, while also ensuring that the other attributes don't gratuitously
diverge. When hoisting descriptions from media objects to posts, that means
ensuring that all of a post's media have the same description. And when removing
redundant locations, that means not dropping the one with the URL.

The validation principle goes beyond the preservation principle by requiring
human intervention when the original Facebook data deviates from the expected
schema. More permissive designs such as `protocol buffers
<https://developers.google.com/protocol-buffers>`_ are certainly feasible but
critically depend on common rules for compatible schema evolution. That is not
feasible for this use case and hence the only reasonable option is to disallow
automatic schema evolution. Since posts are independent top-level entities, that
doesn't mean to terminate post processing upon first failure. We can still
process the remaining posts, one at a time. The validation principle would
suggest not saving such a partial result. But pragmatic concerns point towards
users having that option. After all, having some posts seems better than having
none posts.

.. tip::

   More detailed notes on the different entities potentially belonging to a post
   as well as on individual attributes are included in the API documentation for
   :py:mod:`deface.model`, which defines *deface*'s schema.
