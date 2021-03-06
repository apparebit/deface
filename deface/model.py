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

"""
The data model for posts. This module defines *deface*'s own post schema, which
captures all Facebook post data in a much simpler fashion. The main type is the
:py:class:`Post` dataclass. It depends on the :py:class:`Comment`,
:py:class:`Event`, :py:class:`ExternalContext`, :py:class:`Location`,
:py:class:`Media`, and :py:class:`MediaMetaData` dataclasses as well as the
:py:class:`MediaType` enumeration.

The schema uses Python tuples instead of lists because the former are immutable
and thus do not get in the way of all model classes being both equatable and
hashable.

The model's JSON serialization follows directly from its definition, with every
dataclass instance becoming an object in the JSON text that has the same fields
— with one important exception: If an attribute has ``None`` or the empty tuple
``()`` as its value, :py:func:`deface.serde.prepare` removes it from the JSON
representation. Since the schema needs to capture all information contained in
Facebook post data, it includes a relatively large number of optional
attributes. Including them in the serialized representation would offer little
benefit while also cluttering the JSON text.

The model can easily be reinstated from its JSON text post-by-post by passing
the deserialized dictionary to :py:meth:`Post.from_dict`. The method patches the
representation of nested model types and also fills in ``None`` and ``()``
values. For uniformity of mechanism, all model classes implement ``from_dict``,
even if they do not need to patch fields before invoking the constructor.
"""

from __future__ import annotations

import dataclasses
import enum

from typing import Any, Optional, TypeVar
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

# --------------------------------------------------------------------------------------
# Helper Functions for Merging Records

def _are_equal_or_one_is_none(o1: object, o2: object) -> bool:
  """Determine whether the two object are equal or one is ``None``."""
  return (
    o1 == o2 or (o1 is None and o2 is not None) or (o1 is not None and o2 is None)
  )


def _are_equal_or_one_is_empty(l1: tuple[T, ...], l2: tuple[T, ...]) -> bool:
  """Determine whether the two tuples are equal or one is the empty tuple."""
  return (
    l1 == l2 or (len(l1) == 0 and len(l2) > 0) or (len(l1) > 0 and len(l2) == 0)
  )


T = TypeVar('T')

def _if_not_none_or(o1: T, o2: T) -> T:
  return o1 if o1 is not None else o2

# --------------------------------------------------------------------------------------
# The Model Classes

class MediaType(enum.Enum):
  """
  An enumeration of media types.
  """
  PHOTO = 'PHOTO'
  VIDEO = 'VIDEO'


@dataclasses.dataclass(frozen=True)
class Comment:
  """A comment on a post, photo, or video."""
  author: str
  """The comment's author."""

  comment: str
  """The comment's text."""

  timestamp: int
  """The comment's timestamp."""

  @classmethod
  def from_dict(cls, data: dict[str, Any]) -> Comment:
    """
    Create a new comment from deserialized JSON text. This method assumes that
    the JSON text was created by serializing the result of
    :py:func:`deface.serde.prepare`, just as :py:func:`deface.serde.dumps` does.
    """
    return cls(**data)


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

  @classmethod
  def from_dict(cls, data: dict[str, Any]) -> Event:
    """
    Create a new event from deserialized JSON text. This method assumes that the
    JSON text was created by serializing the result of
    :py:func:`deface.serde.prepare`, just as :py:func:`deface.serde.dumps` does.
    """
    return cls(**data)


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

  @classmethod
  def from_dict(cls, data: dict[str, Any]) -> ExternalContext:
    """
    Create a new external context from deserialized JSON text. This method
    assumes that the JSON text was created by serializing the result of
    :py:func:`deface.serde.prepare`, just as :py:func:`deface.serde.dumps` does.
    """
    return cls(**data)


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
  """The location's name."""

  address: Optional[str] = None
  """The location's address."""

  latitude: Optional[float] = None
  """
  The location's latitude. In the original Facebook post data, this attribute is
  nested inside the ``coordinate`` attribute.
  """

  longitude: Optional[float] = None
  """
  The location's longitude. In the original Facebook data, this attribute is
  nested inside the ``coordinate`` attribute.
  """

  url: Optional[str] = None
  """The URL for the location on `<https://www.facebook.com>`_."""

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

  @classmethod
  def from_dict(cls, data: dict[str, Any]) -> Location:
    """
    Create a new location from deserialized JSON text. This method assumes that
    the JSON text was created by serializing the result of
    :py:func:`deface.serde.prepare`, just as :py:func:`deface.serde.dumps` does.
    """
    return cls(**data)


@dataclasses.dataclass(frozen=True)
class MediaMetaData:
  """
  The metadata for a photo or video. In the original Facebook post data, this
  object also includes the ``upload_ip`` and ``upload_timestamp``, but since
  both attributes describe the use of the photo or video on Facebook and not the
  photo or video itself, they are hoisted into the :py:class:`Media` record. The
  remaining attributes, even if present in the original Facebook post data, tend
  to be meaningless, i.e., are either the empty string or zero. Also, while the
  remaining attributes would be meaningful for both photos and videos, they are
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

  def is_mergeable_with(self, other: Optional[MediaMetaData]) -> bool:
    if other is None:
      return True

    return (
      self.camera_make == other.camera_make
      and self.camera_model == other.camera_model
      and self.exposure == other.exposure
      and self.focal_length == other.focal_length
      and self.f_stop == other.f_stop
      and self.iso_speed == other.iso_speed
      and self.latitude == other.latitude
      and self.longitude == other.longitude
      and self.modified_timestamp == other.modified_timestamp
      and self.orientation == other.orientation
      and self.original_height == other.original_height
      and self.original_width == other.original_width
      and _are_equal_or_one_is_none(self.taken_timestamp, other.taken_timestamp)
    )

  def merge(self, other: MediaMetaData) -> MediaMetaData:
    if self == other:
      return self
    elif not self.is_mergeable_with(other):
      raise MergeError('Unable to merge media metadata', self, other)

    taken = _if_not_none_or(self.taken_timestamp, other.taken_timestamp)
    return dataclasses.replace(self, taken_timestamp=taken)

  @classmethod
  def from_dict(cls, data: dict[str, Any]) -> MediaMetaData:
    """
    Create new media metadata from deserialized JSON text. This method assumes
    that the JSON text was created by serializing the result of
    :py:func:`deface.serde.prepare`, just as :py:func:`deface.serde.dumps` does.
    """
    return cls(**data)


@dataclasses.dataclass(frozen=True)
class Media:
  """A posted photo or video."""

  media_type: MediaType
  """
  The media type, which is derived from the metadata key in the original
  data.
  """

  uri: str
  """
  The path to the photo or video file within the personal data archive. In terms
  of `RFC 3986 <https://www.rfc-editor.org/rfc/rfc3986.txt>`_, the attribute
  provides a *relative-path reference*, i.e., it lacks a scheme such as
  ``file:`` and does not start with a slash ``/``. However, it should not be
  resolved relative to the file containing the field but rather from the root of
  the personal data archive.
  """

  description: Optional[str] = None
  """
  A description of the photo or video. In the original Facebook post data, the
  value for this attribute may be duplicated amongst all of a post's media
  objects as well as the post's body. Whereever safe, such redundancy is
  resolved in favor of the post's body. As a result, any remaining description
  on a media record is unique to that photo or video.
  """

  title: Optional[str] = None
  """
  The title for the photo or video. This field is filled in automatically and
  hence generic. Common variations are ``Mobile Uploads`` or ``Timeline Photos``
  for photos and the empty string for videos.
  """

  thumbnail: Optional[str] = None
  """
  The thumbnail for a photo or video. If present in the original Facebook data,
  the value is an object with ``uri`` as its only field. Just like
  :py:attr:`Media.uri`, the thumbnail URI is a *relative-path reference* that
  should be resolved from the root of the personal data archive.
  """

  metadata: Optional[MediaMetaData] = None
  """The metadata for the photo or video."""

  creation_timestamp: Optional[int] = None
  """
  Seemingly the timestamp for when the media object was created *on Facebook*.
  In the original Facebook, this timestamp differs from the post's timestamp by
  less than 30 seconds.
  """

  upload_timestamp: Optional[int] = None
  """
  The timestamp at which the photo or video was uploaded. In the original
  Facebook post data, this field is part of the  ``photo_metadata`` or
  ``video_metadata`` object nested inside the media object's ``media_metadata``.
  However, since it really is part of Facebook's data on the use of the photo or
  video, it is hoisted into the media record during ingestion.
  """

  upload_ip: Optional[str] = None
  """
  The IP address from which the photo or video was uploaded from. In the
  original Facebook post data, this attribute is part of the  ``photo_metadata``
  or ``video_metadata`` object nested inside the media object's
  ``media_metadata``. It also is the only attribute reliably included with that
  object. However, since ``upload_ip`` really is part of Facebook's data on the
  use of the photo or video, it is hoisted into the media record during
  ingestion.
  """

  comments: tuple[Comment, ...] = dataclasses.field(default_factory=tuple)
  """Comments specifically on the photo or video."""

  def is_mergeable_with(self, other: Media) -> bool:
    """
    Determine whether this media object can be merged with the other media
    object. That is the case if both media objects have the same field values
    with exception of :py:attr:`comments`, :py:attr:`metadata`,
    :py:attr:`title`, and :py:attr:`upload_ip`, which may be omitted from one of
    the two media objects. The exceptions account for the fact that Facebook
    changed the fields it includes in post data over time. As a result, the same
    post with the same media may have different fields depending on when it was
    exported.
    """
    return (
      self.media_type == other.media_type
      and self.uri == other.uri
      and self.description == other.description
      and self.thumbnail == other.thumbnail
      and self.creation_timestamp == other.creation_timestamp
      and self.upload_timestamp == other.upload_timestamp
      and _are_equal_or_one_is_none(self.title, other.title)
      and _are_equal_or_one_is_none(self.metadata, other.metadata)
      and _are_equal_or_one_is_none(self.upload_ip, other.upload_ip)
      and _are_equal_or_one_is_empty(self.comments, other.comments)
      and (
        self.metadata is None # Merges with any value
        or self.metadata.is_mergeable_with(other.metadata)
      )
    )

  def merge(self, other: Media) -> Media:
    """
    Merge this media object with the other media object. If the two media
    objects are not equal but nonetheless mergeable according to
    :py:meth:`is_mergeable_with`, this method returns a new media object with
    the truthy :py:attr:`comments`, :py:attr:`metadata`, :py:attr:`title`, and
    :py:attr:`upload_ip` values from either media object.

    :raises MergeError: indicates that the two media objects are not mergeable.
    """
    if self == other:
      return self
    elif not self.is_mergeable_with(other):
      raise MergeError('Unable to merge media descriptors', self, other)

    comments = tuple(self.comments or other.comments)

    metadata: Optional[MediaMetaData]
    if self.metadata is None:
      metadata = other.metadata
    elif other.metadata is None:
      metadata = self.metadata
    else:
      metadata = self.metadata.merge(other.metadata)

    title = _if_not_none_or(self.title, other.title)
    upload_ip = _if_not_none_or(self.upload_ip, other.upload_ip)

    return dataclasses.replace(
      self,
      comments=comments,
      metadata=metadata,
      title=title,
      upload_ip=upload_ip,
    )

  @classmethod
  def from_dict(cls, data: dict[str, Any]) -> Media:
    """
    Create a new media descriptor from deserialized JSON text. This method
    assumes that the JSON text was created by serializing the result of
    :py:func:`deface.serde.prepare`, just as :py:func:`deface.serde.dumps` does.
    """
    data['comments'] = tuple(
      [Comment.from_dict(c) for c in data.get('comments', [])]
    )
    data['media_type'] = MediaType[data['media_type']]
    if data.get('metadata'):
      data['metadata'] = MediaMetaData.from_dict(data['metadata'])
    return cls(**data)


@dataclasses.dataclass(frozen=True)
class Post:
  """A post on Facebook."""

  timestamp: int
  """
  The time a post was made in seconds since the beginning of the Unix epoch on
  January 1, 1970 at midnight.
  """

  backdated_timestamp: Optional[int] = None
  """A backdated timestamp. Its semantics are unclear."""

  update_timestamp: Optional[int] = None
  """
  Nominally, the time of an update. In practice, if a post includes this field,
  its value appears to be the same as that of ``timestamp``. In other words, the
  field has devolved to a flag indicating whether a post was updated.
  """

  post: Optional[str] = None
  """The post's textual body."""

  name: Optional[str] = None
  """The name for a recommendations."""

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

  text: tuple[str, ...] = dataclasses.field(default_factory=tuple)
  """The text introducing a shared memory."""

  external_context: Optional[ExternalContext] = None
  """An external context, typically with URL only."""

  event: Optional[Event] = None
  """The event this post is about."""

  places: tuple[Location, ...] = dataclasses.field(default_factory=tuple)
  """
  The places for this post. Almost all posts have at most one
  :py:class:`Location`. Occasionally, a post has two locations that share the
  same address, latitude, longitude, and name but differ on
  :py:attr:`Location.url`, with one location having ``None`` and the other
  having some value. In that case, :py:func:`deface.ingest.ingest_post`
  eliminates the redundant location object while keeping ``url``'s value. Posts
  with two or more distinct locations seem rare but do occur.
  """

  tags: tuple[str, ...] = dataclasses.field(default_factory=tuple)
  """The tags for a post, including friends and pages."""

  media: tuple[Media, ...] = dataclasses.field(default_factory=tuple)
  """
  The photos and videos attached to a post.
  """

  def is_simultaneous(self, other: Post) -> bool:
    """
    Determine whether this post and the other post have the same timestamp.
    """
    return self.timestamp == other.timestamp

  def is_mergeable_with(self, other: Post) -> bool:
    """
    Determine whether this post can be merged with the given post. The two posts
    are mergeable if they have the same field values with exception of the
    :py:attr:`title` and :py:attr:`update_timestamp`, which may be omitted from
    one of the two posts, as well as the :py:attr:`media`, which may diverge
    entirely. The exceptions account for the fact that Facebook may export the
    same post repeatedly but with different media objects instead of a single
    post with all those media objects. Furthermore, the fields included with a
    post may vary as well. As a result, the same post may be represented
    differently depending on when it was exported.
    """
    return (
      self.tags == other.tags
      and self.timestamp == other.timestamp
      and self.event == other.event
      and self.external_context == other.external_context
      and self.name == other.name
      and self.places == other.places
      and self.post == other.post
      and _are_equal_or_one_is_none(self.backdated_timestamp, other.backdated_timestamp)
      and _are_equal_or_one_is_none(self.title, other.title)
      and _are_equal_or_one_is_none(self.update_timestamp, other.update_timestamp)
    )

  def merge(self, other: Post) -> Post:
    """
    Merge this post with the other post. If the two posts are not equal but
    nonetheless mergeable according to :py:meth:`is_mergeable_with`, this method
    returns a new post with the truthy :py:attr:`media`, :py:attr:`title`, or
    :py:attr:`update_timestamp` values from either media object.

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
      if not previous.is_mergeable_with(media):
        raise MergeError(
          'Unable to merge posts with different media descriptors'
          ' for the same photo/video',
          self,
          other,
        )
      by_uri[media.uri] = previous.merge(media)

    for media in self.media:
      collect(media)
    for media in other.media:
      collect(media)

    backdated = _if_not_none_or(self.backdated_timestamp, other.backdated_timestamp)
    title = _if_not_none_or(self.title, other.title)
    update = _if_not_none_or(self.update_timestamp, other.update_timestamp)

    return dataclasses.replace(
      self,
      media=tuple(by_uri.values()),
      backdated_timestamp=backdated,
      title=title,
      update_timestamp=update,
    )

  @classmethod
  def from_dict(cls, data: dict[str, Any]) -> Post:
    """
    Create a new post from deserialized JSON text. This method assumes that the
    JSON text was created by serializing the result of
    :py:func:`deface.serde.prepare`, just as :py:func:`deface.serde.dumps` does.
    """
    data['media'] = tuple([Media.from_dict(m) for m in data.get('media', [])])
    data['places'] = tuple(
      [Location.from_dict(l) for l in data.get('places', [])]
    )
    data['tags'] = tuple(data.get('tags', []))
    data['text'] = tuple(data.get('text', []))
    if data.get('event'):
      data['event'] = Event.from_dict(data['event'])
    if data.get('external_context'):
      data['external_context'] = ExternalContext.from_dict(
        data['external_context']
      )
    return cls(**data)
