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

from typing import Optional
from deface.error import MergeError


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
  start_timestamp: int
  end_timestamp: int


@dataclasses.dataclass(frozen=True)
class ExternalContext:
  """
  The external context for a post.
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
  A location in the real world.
  """
  name: str
  address: Optional[str] = None
  latitude: Optional[float] = None
  longitude: Optional[float] = None
  url: Optional[str] = None

  def is_mergeable_with(self, other: Location) -> bool:
    """
    Determine whether this location can be merged with the other location. For
    two locations to be mergeable, they must have identical ``name``,
    ``address``, ``latitude``, and ``longitude`` fields. Furthermore, they must
    either have identical ``url`` fields or one location has a string value
    while the other location has ``None``.
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

    :raises MergeError: indicates that the locations are different and thus
      cannot be merged.
    """
    if not self.is_mergeable_with(other):
      raise MergeError('Unable to merge unrelated locations', self, other)
    elif self.url == other.url or other.url is None:
      return self
    else:
      return other

@dataclasses.dataclass(frozen=True)
class MediaMetaData:
  upload_ip: str
  camera_make: Optional[str] = None
  camera_model: Optional[str] = None
  exposure: Optional[str] = None
  focal_length: Optional[str] = None
  f_stop: Optional[str] = None
  iso_speed: Optional[int] = None
  orientation: Optional[int] = None
  original_height: Optional[int] = None
  original_width: Optional[int] = None
  upload_timestamp: Optional[int] = None


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

  metadata: MediaMetaData

  uri: str
  """
  The absolute path to the photo or video within the personal data archive. In
  terms of `RFC 3986 <https://www.rfc-editor.org/rfc/rfc3986.txt>`, the field
  provides a *relative reference*, i.e., it lacks a scheme such as ``file:``.
  """

  creation_timestamp: Optional[int] = None

  description: Optional[str] = None
  """
  deface prioritizes the :py:attr:`deface.model.Post.post` over its media
  objects' :py:attr:`deface.model.Media.description`. When safe,
  :py:func:`deface.ingest.ingest_post` hoists the media description into the
  post body while also deleting redundant media descriptions.
  """

  thumbnail: Optional[str] = None
  title: Optional[str] = None


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
  The time a post was made in seconds since the beginning of the Unix epoch
  (January 1, 1970 at midnight).
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
  The title of a post, which seems to be filled in automatically and hence is of
  limited use.
  """

  update_timestamp: Optional[int] = None
  """
  Nominally, the time of an update. In practice, if a post includes this field,
  its value appears to be the same as that of ``timestamp``. In other words, the
  field has devolved to a flag indicating whether a post was updated.
  """

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
    Merge this post with the other post. If the two posts differ only in media,
    this method returns a new post that combines the media from both posts.

    :param other: The post to merge with.
    :raises MergeError: indicates that the two posts differ in more than their
      media
    """
    if self == other:
      return self
    elif not self.is_mergeable_with(other):
      raise MergeError('Unable to merge unrelated posts', self, other)

    media1 = set(self.media)
    media2 = set(other.media)
    if media2 <= media1:
      return self
    elif media1 <= media2:
      return other
    else:
      return dataclasses.replace(self, media=tuple(media1 | media2))

class PostHistory:
  def __init__(self) -> None:
    self._posts: dict[int, Post] = dict()

  def add(self, post: Post) -> None:
    timestamp = post.timestamp
    if timestamp in self._posts:
      other_post = self._posts[timestamp]
      self._posts[timestamp] = post.merge(other_post)
    else:
      self._posts[post.timestamp] = post

  def posts(self) -> list[Post]:
    posts = list(self._posts.values())
    sorted(posts, key=lambda p: p.timestamp)
    return posts
