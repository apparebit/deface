Design Considerations
=====================

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

The preservation principle applies to the leaves of the JSON graph, that is,
keys with scalar values including text, and to interior nodes that are
meaningful in the domain of social media posts, e.g., not only posts themselves
but also media, events, or locations. At the same time, they do not include
artifacts of Facebook's fairly elaborate JSON encoding. For example, a post's
``attachments`` and ``data`` keys, if present, have lists of singleton objects
as values. Each nested singleton object is a key, value pair representing a
property of the post, with some properties having multiple values. The obvious
and more concise alternative is to add the keys to the post object and to use
lists of values where the more elaborate encoding uses key, value pairs with the
same key.

The simplification principle applies to the ``attachments`` and ``data``
introduced above because they aren't meaningful in the domain of social media
posts. It also favors the more direct encoding because it only features keys
that are meaningful in the domain of social media posts. More subtly, the
simplification principle applies to locations in Facebook's JSON data. Their
``coordinates`` are nested objects with the ``latitude`` and ``longitude``. But
the nested coordinates do not represent a concept *independent* from the
location. The corresponding simplifying transform deletes the coordinates object
after hoisting its contents into the outer location.

In addition to the encoding being already rather elaborate, Facebook's post data
contains a surprising amount of duplicated data. For example:

* Posts containing several photos and/or video may be represented as that many
  post objects with identical ``timestamp`` and ``post`` body but different
  media objects describing those photos and/or videos.
* All of a post's media objects may have the same ``description``, which may
  also be the same as the ``post`` body.
* Very few posts have more than one location object. In most of those cases,
  there are two location objects that differ only in ``url``, with one object]
  having ``None`` and the other having a value.

In all these cases, the simplification principle applies but the implementation
must take care to preserve all information. That means treating media objects in
otherwise identical post objects as sets of media objects. That means hoisting a
description from media objects to post object only if *all* media objects have
the same description and the post has no body. However, if a media object has
the same description as the post's body, the description can be deleted without
checking the post's other media objects. Finally, that means keeping the
location object with URL.

The validation principle goes beyond the preservation principle by requiring
human intervention when data deviates from the expected schema. More permissive
designs such as `protocol buffers
<https://developers.google.com/protocol-buffers>`_ are feasible but critically
depend on shared rules for compatible schema evolution. For this use case, no
such framework exists and hence the only reasonable option is to disallow any
automatic schema evolution. However, since posts are independent top-level
entities, a tool that adheres to the principles needn't terminate processing
upon the first validation failure. It only needs to terminate processing that
post. The validation principle would suggest not exporting the partial dataset
resulting from such a run. But pragmatic concerns — having access to some
cleaned up posts is better than having access to none — point towards doing so
if the user insists. That is only fair since the principles seek to protect user
interest in the first place.
