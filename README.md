# deface: Liberate Your Posts From Facebook

The **deface** command line tool and library clean and consolidate the post data
from `posts/your_posts_n.json` files in personal archives exported from
Facebook. That should make it easier to extricate your content and also yourself
from the social network. Doing so matters because Facebook is an imminent threat
to human rights and democracy all over the world. I presented the
(dispassionate) [case against Facebook](https://youtu.be/iYJQSfQGDEE) as an
invited talk at
[Rebase](http://rebase-conf.org/2020/#technology-today-a-paucity-of-integrity-and-imagination)/[SPLASH](https://2020.splashcon.org)
in November 2020.


## Design Principles

The design and implementation of **deface** adhere to three principles:

 1. Preserve all content. Notably, access values through the same immediate
    keys.
 2. Simplify the data. Notably, eliminate generic fields such as `"attachments"`
    and `"data"` as well as obviously redundant content.
 3. Fail fast and loud. When it is unclear how to adhere to the first two
    principles, notably upon unexpected input data, fail immediately with an
    exception.

As implied by their order, preserving content takes priority over simplifying
the data. The principles are necessary because the JSON data provided by
Facebook doesn't have a documented schema and exhibits several idiosyncrasies.
It certainly looks like Facebook engineers followed the company's "*move fast
and break things*" motto while implementing the personal archive export feature.

## Data Transformation

**deface** processes posts as follows:

  * To ingest `posts/your_posts_n.json` files, the tool fixes their broken
    character encoding first. It appears that Facebook generates UTF-8-encoded
    JSON, escaping only double quotes and newlines inside string literals as
    `\"` and `\n`, respectively, and then — instead of stopping — also encodes
    every byte that isn't a valid ASCII character as a faux Unicode escape
    sequence of the form `\u00xx`.
  * After correcting the encoding and parsing the JSON, **deface** processes one
    post at a time and rigorously validates the structure and types of the post
    data. The result is either a `DefaceError` in case of unexpected or
    malformed input data or a `Post` object with the cleaned up data.

While converting the post input data into `Post` object, **deface** makes the
following simplifying transformations:

  * It hoists individual `attachments`, which comprise data on `event`,
    `external_context` (typically just a URL), `media`, `name` (for
    recommendations), `place` (see next bullet point), and `text` (for the text
    of memories) as well as individual `data` fields, which comprise the
    `backdated_timestamp`, the actual `post` text, and the `update_timestamp`
    into `Post`, which reduces the nesting of records.
  * Typically, a post has at most one `place` specifying a `Location`. However,
    Facebook does at times include two such records for the same post that
    differ only in their `url`, with one having `None` and the other having an
    actual URL. **deface** detects such duplicated location information, folding
    it into one `Location` object, but also preserves several, different
    locations (which seem rare).
  * When a post's `media` all have the same `description` and the `Post` object
    has has no `post` text, **deface** hoists the description into the post and
    removes it from the media. Similarly, if a `Media` object's `description` is
    the same as the `post` text, it deletes the redundant `description`.
  * When several posts with the same `timestamp` only differ in `media`,
    **deface** combines the posts into one with the union of all `Media`
    objects. This heuristic reduces almost all posts with the same timestamp to
    a single post. Unfortunately, however, I have encountered at least two posts
    with the same timestamp that are completely different. It is unclear how I
    managed to post them within the same second.

---

**deface** has been released as open source under the [Apache 2.0
license](LICENSE).
