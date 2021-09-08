# Copyright 2021 Robert Grimm
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import dataclasses
import enum

from typing import Optional, Union
from deface.error import MergeError


__all__ = [
  'MediaType',
  'Comment',
  'Event',
  'ExternalContext',
  'Location',
  'MediaMetaData',
  'Media',
  'Post',
  'PostHistory',
  'find_simultaneous_posts'
]


class MediaType(enum.Enum):
  """
  An enumeration of media types.
  """
  PHOTO = 'PHOTO'
  VIDEO = 'VIDEO'


@dataclasses.dataclass(frozen=True)
class Comment:
  """
  A comment on a post, photo, or video.
  """
  author: str
  comment: str
  timestamp: int


@dataclasses.dataclass(frozen=True)
class Event:
  """
  An event
  """
  name: str
  """The event's name."""

  start_timestamp: int
  """The beginning of the event."""

  end_timestamp: int
  """The end of the event or zero for events without a defined duration."""


@dataclasses.dataclass(frozen=True)
class ExternalContext:
  """
  The external context for a post. In the original Facebook post data, a post's
  external context is part of the attachments:

  .. code-block:: json

     {
       "attachments": [
         {
           "data": [
             {
               "external_context": {
                 "name": "Instagram Post by Ro\\u00cc\\u0081isi\\u00cc\\u0081n Murphy",
                 "source": "instagram.com",
                 "url": "https://www.instagram.com/p/B_13ojcD6Fh/"
               }
             }
           ]
         }
       ]
     }

  Unusually, the example includes a ``name`` and ``source`` in addition to the
  ``url``. It also illustrates the mojibake resulting from Facebook erroneously
  double encoding all text. The ``name`` should read ``Instagram Post by
  Róisín Murphy``.
  """

  url: str
  """A URL linking to external content."""

  name: Optional[str] = None
  """
  The name of the website or, if article, its title. Not a common attribute.
  """

  source: Optional[str] = None
  """
  The name of the website or, if article, the publication's name. Not a common
  attribute.
  """


@dataclasses.dataclass(frozen=True)
class Location:
  """
  A location in the real world. In the original Facebook post data, a post's
  place is part of the attachments:

  .. code-block:: json

     {
       "attachments": [
         {
           "data": [
             {
               "place": {
                 "name": "Whitney Museum of American Art",
                 "coordinate": {
                   "latitude": 40.739541735,
                   "longitude": -74.009095020556
                 },
                 "address": "",
                 "url": "https://www.facebook.com/whitneymuseum/"
               }
             }
           ]
         }
       ]
     }

  The ``coordinate`` is stripped during ingestion to hoist ``latitude`` and
  ``longitude`` into the location record. In rare cases, the ``coordinate`` may
  be missing from the original Facebook data, hence both the ``latitude`` and
  ``longitude`` attributes are optional.
  """
  name: str
  address: Optional[str] = None

  latitude: Optional[float] = None
  """
  The latitude. In the original Facebook post data, this attribute is nested
  inside the ``coordinate`` attribute.
  """

  longitude: Optional[float] = None
  """
  The longitude. In the original Facebook data, this attribute is nested inside
  the ``coordinate`` attribute.
  """

  url: Optional[str] = None

  def is_mergeable_with(self, other: Location) -> bool:
    """
    Determine whether this location can be merged with the other location. For
    two locations to be mergeable, they must have identical ``name``,
    ``address``, ``latitude``, and ``longitude`` attributes. Furthermore, they
    must either have identical ``url`` attributes or one location has a string
    value while the other location has ``None``.
    """
    return (
      self.name == other.name
      and self.address == other.address
      and self.latitude == other.latitude
      and self.longitude == other.longitude
      and (
        self.url == other.url
        or self.url is None
        or other.url is None
      )
    )

  def merge(self, other: Location) -> Location:
    """
    Merge this location with the given location. In case of identical URLs, this
    method returns ``self``. In case of divergent URLs, this method returns the
    instance with the URL value.

    :raises MergeError: indicates that the locations differ in more than their
      URLs and thus cannot be merged.
    """
    if not self.is_mergeable_with(other):
      raise MergeError('Unable to merge unrelated locations', self, other)
    elif self.url == other.url or other.url is None:
      return self
    else:
      return other

@dataclasses.dataclass(frozen=True)
class MediaMetaData:
  """
  The metadata for a photo or video. In the original Facebook post data, this
  object also includes the ``upload_ip`` and ``upload_timestamp``, but since
  both attributes describe the use of the photo or video on Facebook and not the
  photo or video itself, they are hoisted into the :py:class:`Media` record. The
  remaining attributes, even if present in the original Facebook post data, tend
  to be meaningless, i.e., are either the empty string or zero. Also, while the
  remaining attributes would be meaningful for both photos and videos, the are
  found only on photos.
  """
  camera_make: Optional[str] = None
  camera_model: Optional[str] = None
  exposure: Optional[str] = None
  focal_length: Optional[str] = None
  f_stop: Optional[str] = None
  iso_speed: Optional[int] = None
  latitude: Optional[float] = None
  longitude: Optional[float] = None
  modified_timestamp: Optional[int] = None
  orientation: Optional[int] = None
  original_height: Optional[int] = None
  original_width: Optional[int] = None
  taken_timestamp: Optional[int] = None


@dataclasses.dataclass(frozen=True)
class Media:
  """A posted photo or video."""

  comments: tuple[Comment, ...]
  """Comments specifically on the photo or video."""

  media_type: MediaType
  """
  The media type, which is derived from the metadata key in the original
  data.
  """

  uri: str
  """
  The absolute path to the photo or video within the personal data archive. In
  terms of `RFC 3986 <https://www.rfc-editor.org/rfc/rfc3986.txt>`, the
  attribute provides a *relative reference*, i.e., it lacks a scheme such as
  ``file:``.
  """

  upload_ip: str
  """
  The IP address from which the photo or video was uploaded from. In the
  original Facebook post data, this attribute is part of the  ``photo_metadata``
  or ``video_metadata`` object nested inside the media object's
  ``media_metadata``. It also is the only attribute reliably included with that
  object. However, since ``upload_ip`` really is part of Facebook's data on the
  use of the photo or video, it is hoisted into the media record during
  ingestion.
  """

  creation_timestamp: Optional[int] = None

  description: Optional[str] = None
  """
  A description of the photo or video. In the original Facebook post data, the
  value for this attribute may be duplicated amongst all of a post's media
  objects as well as the post's body. Whereever safe, such redundancy is
  resolved in favor of the post's body. As a result, any remaining description
  on a media record is unique to that photo or video.
  """

  metadata: Optional[MediaMetaData] = None
  """The metadata for the photo or video."""

  thumbnail: Optional[str] = None
  title: Optional[str] = None

  upload_timestamp: Optional[int] = None
  """
  The timestamp at which the photo or video was uploaded. In the original
  Facebook post data, this field is part of the  ``photo_metadata`` or
  ``video_metadata`` object nested inside the media object's ``media_metadata``.
  However, since it really is part of Facebook's data on the use of the photo or
  video, it is hoisted into the media record during ingestion.
  """


@dataclasses.dataclass(frozen=True)
class Post:
  """A post on Facebook."""

  media: tuple[Media, ...]
  """
  The photos and videos attached to a post.
  """

  places: tuple[Location, ...]
  """
  The places for this post. Almost all posts have at most one
  :py:class:`deface.model.Location`. Occasionally, a post has two locations that
  share the same address, latitude, longitude, and name but differ on
  :py:attr:`deface.model.Location.url`, with one location having ``None`` and
  the other having some value. In that case,
  :py:func:`deface.ingest.ingest_post` eliminates the redundant location object
  while keeping ``url``'s value. Posts with two or more distinct locations seem
  rare but do occur.
  """

  tags: tuple[str, ...]
  """The tags for a post, including friends and pages."""

  text: list[str]
  """The text introducing a shared memory."""

  timestamp: int
  """
  The time a post was made in seconds since the beginning of the Unix epoch on
  January 1, 1970 at midnight.
  """

  backdated_timestamp: Optional[int] = None
  """A backdated timestamp. Its semantics are unclear."""

  event: Optional[Event] = None

  external_context: Optional[ExternalContext] = None
  """An external context, typically with URL only."""

  name: Optional[str] = None
  """The name for a recommendations."""

  post: Optional[str] = None
  """The post's textual body."""

  title: Optional[str] = None
  """
  The title of a post. This field is filled in automatically and hence generic.
  Starting with more common ones, variations include:

  * ``Alice``
  * ``Alice updated her status.``
  * ``Alice shared a memory.``
  * ``Alice wrote on Bob's timeline.``
  * ``Alice is feeling blessed.``
  * ``Alice was with Bob.``
  """

  update_timestamp: Optional[int] = None
  """
  Nominally, the time of an update. In practice, if a post includes this field,
  its value appears to be the same as that of ``timestamp``. In other words, the
  field has devolved to a flag indicating whether a post was updated.
  """

  def is_simultaneous(self, other: Post) -> bool:
    """
    Determine whether this post and the other post have the same timestamp.
    """
    return self.timestamp == other.timestamp

  def is_mergeable_with(self, other: Post) -> bool:
    """
    Determine whether this post can be merged with the given post. The two posts
    are mergeable if they differ in their media at most.
    """
    return (
      self.tags == other.tags
      and self.timestamp == other.timestamp
      and self.backdated_timestamp == other.backdated_timestamp
      and self.event == other.event
      and self.external_context == other.external_context
      and self.name == other.name
      and self.places == other.places
      and self.post == other.post
      and self.title == other.title
      and self.update_timestamp == other.update_timestamp
    )

  def merge(self, other: Post) -> Post:
    """
    Merge this post with the other post. If the two posts differ only in their
    media, this method returns a new post that combines the media from both
    posts.

    :param other: the post to merge with.

    :raises MergeError: indicates that the two posts differ in more than their
      media or have different media descriptors for the same photo or video.
    """
    if self == other:
      return self
    elif not self.is_mergeable_with(other):
      raise MergeError('Unable to merge unrelated posts', self, other)

    by_uri: dict[str, Media] = {}
    def collect(media: Media) -> None:
      if media.uri not in by_uri:
        by_uri[media.uri] = media
        return

      previous = by_uri[media.uri]
      if previous != media:
        raise MergeError(
          'Unable to merge posts with different media descriptors'
          ' for the same photo/video',
          self,
          other,
        )

    for media in self.media:
      collect(media)
    for media in other.media:
      collect(media)
    return dataclasses.replace(self, media=tuple(by_uri.values()))


class PostHistory:
  """
  A history of posts. This class tracks added posts by timestamp so that it can
  merge posts that only differ in media while also eliminating duplicate posts.
  The latter is important when ingesting posts from more than one personal data
  archive, since the archives may just overlap in time.
  """
  def __init__(self) -> None:
    self._posts: dict[int, Union[Post, list[Post]]] = dict()

  def add(self, post: Post) -> None:
    """
    Add the post to the history of posts. If the history already includes one or
    more posts with the same timestamp, this method tries merging the given post
    with each of those posts and replaces the post upon a successful merge.
    Otherwise, this method adds the post to the history.
    """
    timestamp = post.timestamp
    if timestamp not in self._posts:
      # No prior post with same timestamp.
      self._posts[timestamp] = post
      return

    already_recorded = self._posts[timestamp]
    if isinstance(already_recorded, Post):
      # One prior post with same timestamp.
      if already_recorded.is_mergeable_with(post):
        self._posts[timestamp] = already_recorded.merge(post)
      else:
        self._posts[timestamp] = [already_recorded, post]
      return

    # Several prior posts with same timestamp.
    for index, other in enumerate(already_recorded):
      if other.is_mergeable_with(post):
        already_recorded[index] = other.merge(post)
        return
    already_recorded.append(post)

  def timeline(self) -> list[Post]:
    """
    Get a timeline for the history of posts. The timeline includes all posts
    from the history in chronological order.
    """
    posts: list[Post] = []
    for value in self._posts.values():
      if isinstance(value, Post):
        posts.append(value)
      else:
        posts.extend(value)
    sorted(posts, key=lambda p: p.timestamp)
    return posts


def find_simultaneous_posts(timeline: list[Post]) -> list[range]:
  """
  Find all simultaneous posts on the given timeline and return the ranges of
  their indexes.
  """
  simultaneous_posts: list[range] = []

  index = 0
  length = len(timeline)
  while index < length:
    # Start with current index.
    start = index
    post = timeline[index]
    # Scan for subsequent simultaneous posts.
    while index + 1 < length and post.is_simultaneous(timeline[index + 1]):
      index += 1
    # Jot down the range if there were simultaneous posts.
    if start != index:
      simultaneous_posts.append(range(start, index + 1))
    # Make sure next iteration looks at subsequent post.
    index += 1

  return simultaneous_posts
