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
  An external context for a post.
  """
  url: str
  name: Optional[str] = None
  source: Optional[str] = None

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

  def merge(self, other: Location) -> Location:
    if (
      self.name == other.name
      or self.address == other.address
      or self.latitude == other.latitude
      or self.longitude == other.longitude
    ):
      if self.url == other.url or other.url is None:
        return self
      elif self.url is None:
        return other
    raise MergeError('Unable to merge unrelated locations', self, other)

@dataclasses.dataclass(frozen=True)
class Media:
  """
  A posted photo or video. The ``uri`` is *not* a URL but only a file path into
  the ``photos_and_videos`` directory of the Facebook data archive.
  """
  comments: tuple[Comment, ...]
  media_type: MediaType
  metadata: dict[str, Union[str, int]] = dataclasses.field(compare=False)
  uri: str
  creation_timestamp: Optional[int] = None
  description: Optional[str] = None
  thumbnail: Optional[str] = None
  title: Optional[str] = None

@dataclasses.dataclass(frozen=True)
class Post:
  """
  A post on Facebook. The most important fields are post's ``timestamp``,
  ``post`` with the body text, ``media`` describing attached photos and videos,
  as well as ``external_context`` linking to other websites. deface prioritizes
  the post body over media objects' ``description`` fields. If it is safe to do,
  ``ingest_post()`` fills in an empty body from media object descriptions while
  also deleting redundant media object descriptions.
  """
  media: tuple[Media, ...]

  place: tuple[Location, ...]
  """
  A place. Almost all posts have at most one location. Occasionally, a post has
  exactly two locations, with both having the same address, latitude, longitude,
  and name; one having ``None`` for URL; and the other having a URL. In that
  case, ``ingest_post()`` eliminates the redundant location object (without
  URL). Posts with two or more distinct locations are rare but do occur.
  """

  tags: tuple[str, ...]
  timestamp: int
  backdated_timestamp: Optional[int] = None
  event: Optional[Event] = None

  external_context: Optional[ExternalContext] = None
  """An external context usually consists of the URL only."""

  name: Optional[str] = None
  """A name only appears in recommendations"""

  post: Optional[str] = None
  title: Optional[str] = None
  update_timestamp: Optional[int] = None

  def merge(self, other: Post) -> Post:
    if self == other:
      return self
    elif (
      self.tags != other.tags
      or self.timestamp != other.timestamp
      or self.backdated_timestamp != other.backdated_timestamp
      or self.event != other.event
      or self.external_context != other.external_context
      or self.name != other.name
      or self.place != other.place
      or self.post != other.post
      or self.title != other.title
      or self.update_timestamp != other.update_timestamp
    ):
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
  def __init__(self):
    self._posts: dict[int, Post] = dict()

  def add(self, post: Post) -> None:
    timestamp = post.timestamp
    if timestamp in self._posts:
      other_post = self._posts[timestamp]
      self._posts[timestamp] = post.merge(other_post)
    else:
      self._posts[post.timestamp] = post

  def list(self) -> list[Post]:
    return self._posts.values()
