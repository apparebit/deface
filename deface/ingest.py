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
Ingestion of the original Facebook post data. This module provides code for
validating that posts have the expected structure and types and to then convert
them to *deface*'s own :py:mod:`deface.model`.
"""

import dataclasses
from typing import Any, Optional, Union

from deface.error import DefaceError, MergeError, ValidationError
from deface.model import (
  Comment,
  Event,
  ExternalContext,
  Location,
  Media,
  MediaType,
  MediaMetaData,
  Post,
)
from deface.validator import Sized, Validator

__all__ = [
  'ingest_into_history',
  'ingest_post',
  'ingest_media',
  'ingest_location',
  'ingest_external_context',
  'ingest_event',
  'ingest_comment',
  'PostHistory',
  'find_simultaneous_posts',
]

_COMMENT_KEYS: set[str] = { 'author', 'comment', 'timestamp' }

def ingest_comment(data: Validator[Any]) -> Comment:
  """
  Ingest the JSON data value wrapped by the validator as a comment.
  """
  comment_data = data.to_object(valid_keys=_COMMENT_KEYS)
  comment_data['author'].to_string()
  comment_data['comment'].to_string()
  comment_data['timestamp'].to_integer()
  return Comment(**comment_data.value)

# ------------------------------------------------------------------------------

_EVENT_KEYS = { 'name', 'start_timestamp', 'end_timestamp' }

def ingest_event(data: Validator[Any]) -> Event:
  """
  Ingest the JSON data value wrapped by the validator as an event.
  """
  event_data = data.to_object(valid_keys=_EVENT_KEYS)
  event_data['name'].to_string()
  event_data['start_timestamp'].to_integer()
  event_data['end_timestamp'].to_integer()
  return Event(**event_data.value)

# ------------------------------------------------------------------------------

_EXTERNAL_CONTEXT_KEYS = { 'name', 'source', 'url' }

def ingest_external_context(data: Validator[Any]) -> ExternalContext:
  """
  Ingest the JSON data value wrapped by the validator as an external context.
  """
  context_data = data.to_object(valid_keys=_EXTERNAL_CONTEXT_KEYS)
  if 'name' in context_data.value:
    context_data['name'].to_string()
  if 'source' in context_data.value:
    context_data['source'].to_string()
  context_data['url'].to_string()
  return ExternalContext(**context_data.value)

# ------------------------------------------------------------------------------

_LOCATION_KEYS: set[str] = { 'address', 'coordinate', 'name', 'url' }
_COORDINATE_KEYS: set[str] = { 'latitude', 'longitude' }

def ingest_location(data: Validator[Any]) -> Location:
  """
  Ingest the JSON data value wrapped by the validator as a location.
  """
  location_data = data.to_object(valid_keys=_LOCATION_KEYS)
  fields: dict[str, Any] = {}
  if 'address' in location_data.value:
    fields['address'] = location_data['address'].to_string().value

  if 'coordinate' in location_data.value:
    coordinate = location_data['coordinate'].to_object(
      valid_keys=_COORDINATE_KEYS
    )
    fields['latitude'] = float(coordinate['latitude'].to_float().value)
    fields['longitude'] = float(coordinate['longitude'].to_float().value)

  fields['name'] = location_data['name'].to_string().value
  if 'url' in location_data.value:
    fields['url'] = location_data['url'].to_string().value

  return Location(**fields)

# ------------------------------------------------------------------------------

_MEDIA_METADATA_KEYS: set[str] = {
  'camera_make',
  'camera_model',
  'exposure',
  'focal_length',
  'f_stop',
  'iso',
  'iso_speed',
  'latitude',
  'longitude',
  'modified_timestamp',
  'orientation',
  'original_width',
  'original_height',
  'taken_timestamp',
  'upload_ip',
  'upload_timestamp',
}

def ingest_metadata(
  data: Validator[Any], media_fields: dict[str, Any]
) -> Optional[MediaMetaData]:
  """
  Ingest the JSON data value wrapped by the validator as media metadata. Since
  the ``upload_ip`` and ``upload_timestamp`` attributes really belong to the
  media descriptor itself, this function adds them to the given
  ``media_fields``.
  """
  metadata = data.to_object(valid_keys=_MEDIA_METADATA_KEYS)

  if 'upload_ip' in metadata.value:
    media_fields['upload_ip'] = metadata['upload_ip'].to_string().value
  if 'upload_timestamp' in metadata.value:
    media_fields['upload_timestamp'] = (
      metadata['upload_timestamp'].to_integer().value
    )

  fields: dict[str, Any] = {}
  if 'camera_make' in metadata.value:
    fields['camera_make'] = metadata['camera_make'].to_string().value
  if 'camera_model' in metadata.value:
    fields['camera_model'] = metadata['camera_model'].to_string().value
  if 'exposure' in metadata.value:
    fields['exposure'] = metadata['exposure'].to_string().value
  if 'focal_length' in metadata.value:
    fields['focal_length'] = metadata['focal_length'].to_string().value
  if 'f_stop' in metadata.value:
    fields['f_stop'] = metadata['f_stop'].to_string().value
  if 'iso' in metadata.value:
    fields['iso_speed'] = metadata['iso'].to_integer().value
  elif 'iso_speed' in metadata.value:
    fields['iso_speed'] = metadata['iso_speed'].to_integer().value
  if 'latitude' in metadata.value:
    fields['latitude'] = metadata['latitude'].to_float().value
  if 'longitude' in metadata.value:
    fields['longitude'] = metadata['longitude'].to_float().value
  if 'modified_timestamp' in metadata.value:
    fields['modified_timestamp'] = metadata['modified_timestamp'].to_integer().value
  if 'orientation' in metadata.value:
    fields['orientation'] = metadata['orientation'].to_integer().value
  if 'original_height' in metadata.value:
    fields['original_height'] = metadata['original_height'].to_integer().value
  if 'original_width' in metadata.value:
    fields['original_width'] = metadata['original_width'].to_integer().value
  if 'taken_timestamp' in metadata.value:
    fields['taken_timestamp'] = metadata['taken_timestamp'].to_integer().value

  return MediaMetaData(**fields) if len(fields) > 0 else None

# ------------------------------------------------------------------------------

_MEDIA_KEYS: set[str] = {
  'comments',
  'creation_timestamp',
  'description',
  'media_metadata',
  'thumbnail',
  'title',
  'uri',
}

_METADATA_KEYS: set[str] = { 'photo_metadata', 'video_metadata' }

def ingest_media(data: Validator[Any]) -> Media:
  """
  Ingest the JSON data value wrapped by the validator as a media descriptor.
  """
  media_data = data.to_object(valid_keys=_MEDIA_KEYS)
  fields: dict[str, Any] = {}

  comments: list[Comment] = []
  if 'comments' in media_data.value:
    for comment_data in media_data['comments'].to_list().items():
      comments.append(ingest_comment(comment_data))
  fields['comments'] = tuple(comments)

  fields['creation_timestamp'] = (
    media_data['creation_timestamp'].to_integer().value
  )

  if 'description' in media_data.value:
    fields['description'] = media_data['description'].to_string().value

  uri = fields['uri'] = media_data['uri'].to_string().value

  if 'media_metadata' in media_data.value:
    metadata = media_data['media_metadata'].to_object(
      valid_keys=_METADATA_KEYS, singleton=True
    )
    metadata_key = metadata.only_key
    fields['media_type'] = (
      MediaType.VIDEO if metadata_key == 'video_metadata' else MediaType.PHOTO
    )
    metadata = metadata[metadata_key].to_object()
    if len(metadata.value) == 1 and 'exif_data' in metadata.value:
      metadata = metadata['exif_data'].to_list(Sized.EXACTLY_ONE)[0].to_object()
    media_metadata = ingest_metadata(metadata, fields)
    if media_metadata is not None:
      fields['metadata'] = media_metadata
  else:
    fields['media_type'] = (
      MediaType.VIDEO if uri.endswith('.mp4') else MediaType.PHOTO
    )

  if 'thumbnail' in media_data.value:
    thumbnail_data = media_data['thumbnail'].to_object(
      valid_keys={'uri'}, singleton=True
    )
    fields['thumbnail'] = thumbnail_data['uri'].to_string().value

  if 'title' in media_data.value:
    fields['title'] = media_data['title'].to_string().value

  return Media(**fields)

# ------------------------------------------------------------------------------

_ATTACHMENT_KEYS: set[str] = {
  'event', 'external_context', 'media', 'name', 'place', 'text'
}
_DATA_KEYS: set[str] = { 'backdated_timestamp', 'post', 'update_timestamp' }
_POST_KEYS: set[str] = { 'attachments', 'data', 'tags', 'timestamp', 'title' }

def _handle_attachments(
  data: Validator[Any], fields: dict[str, Any]
) -> tuple[list[Media], list[Location], list[str]]:
  """
  Handle a post's attachments, collecting individual fields in the eponymous
  dictionary and possibly repeated ``media``, ``place``, and ``tag`` values
  in separate lists (to be returned in a tuple).
  """
  all_media: list[Media] = []
  all_places: list[Location] = []
  all_text: list[str] = []

  for outer_item in data.to_list(Sized.ZERO_OR_MORE).items():
    outer_data = outer_item.to_object(valid_keys={'data'}, singleton=True)
    for inner_item in outer_data['data'].to_list().items():
      inner_data = inner_item.to_object(
        valid_keys=_ATTACHMENT_KEYS, singleton=True
      )
      key = inner_data.only_key
      if key == 'media':
        all_media.append(ingest_media(inner_data[key]))
      elif key == 'place':
        a_place = ingest_location(inner_data[key])
        did_merge = False
        for index, another_place in enumerate(all_places):
          try:
            all_places[index] = a_place.merge(another_place)
            did_merge = True
            break
          except MergeError:
            pass
        if not did_merge:
          all_places.append(a_place)
      elif key == 'text':
        all_text.append(inner_data['text'].to_string().value)
      else:
        # Remaining fields may be repeated iff values are the same.
        attachment: Union[ExternalContext, Event, str]
        if key == 'event':
          attachment = ingest_event(inner_data[key])
        elif key == 'external_context':
          attachment = ingest_external_context(inner_data[key])
        elif key == 'name':
          attachment = inner_data[key].to_string().value
        else:
          assert False, f'Internal error due to unexpected key "{key}"'

        if not key in fields:
          fields[key] = attachment
        elif attachment != fields[key]:
          inner_data.raise_invalid(f'has repeated, divergent value for field "{key}"')

  return all_media, all_places, all_text

def ingest_post(data: Validator[Any]) -> Post:
  """
  Ingest the JSON data value wrapped by the validator as a post.
  """
  post_data = data.to_object(valid_keys=_POST_KEYS)
  fields: dict[str, Any] = {}

  all_media: list[Media]
  all_places: list[Location]
  all_text: list[str]
  if 'attachments' in post_data.value:
    all_media, all_places, all_text = _handle_attachments(
      post_data['attachments'], fields
    )
  else:
    all_media = list()
    all_places = list()
    all_text = list()

  if 'data' in post_data.value:
    for item in post_data['data'].to_list(Sized.ZERO_OR_MORE).items():
      item_data = item.to_object(valid_keys=_DATA_KEYS, singleton=True)
      key = item_data.only_key
      if key in fields:
        item_data.raise_invalid(f'has redundant field "{key}"')
      elif key == 'post':
        fields['post'] = item_data['post'].to_string().value
      else:
        fields[key] = item_data[key].to_integer().value

  tags: list[str] = []
  if 'tags' in post_data.value:
    for tag_data in post_data['tags'].to_list().items():
      tags.append(tag_data.to_string().value)
  fields['tags'] = tuple(tags)

  fields['timestamp'] = post_data['timestamp'].to_integer().value
  if 'title' in post_data.value:
    fields['title'] = post_data['title'].to_string().value

  # Adjust media descriptions:
  #  1. Remove description from media object, if post body is the same.
  #  2. Hoist description to post body, if all media objects have same one
  #     and there is no post body.
  # In both cases, the post body is given priority over media descriptions.
  if 'post' in fields:
    post = fields['post']
    for index, media in enumerate(all_media):
      if post == media.description:
        media = dataclasses.replace(media, description=None)
        all_media[index] = media
  elif len(all_media) > 0 and all_media[0].description is not None:
    post = all_media[0].description
    if all(post == media.description for media in all_media):
      fields['post'] = post
      for index, media in enumerate(all_media):
        all_media[index] = dataclasses.replace(media, description=None)
  fields['media'] = tuple(all_media)
  fields['places'] = tuple(all_places)
  fields['text'] = tuple(all_text)

  return Post(**fields)

# ------------------------------------------------------------------------------

class PostHistory:
  """
  A history of posts. Use :py:meth:`ingest` to do just that for the wrapped post
  data. The implementation, in turn, uses :py:meth:`add` to add posts one-by-one
  as they are ingested. This class organizes posts by
  :py:attr:`deface.model.Post.timestamp`. That lets it easily merge posts that
  only differ in media as well as eliminate duplicate posts. The latter is
  particularly important when ingesting posts from more than one personal data
  archive, since archives may just overlap in time. Once all posts have been
  added to the history, :py:meth:`timeline` returns a list of all unique posts
  sorted by ``timestamp``.
  """
  def __init__(self) -> None:
    self._posts: dict[int, Union[Post, list[Post]]] = dict()

  def ingest(self, data: Validator[Any]) -> list[DefaceError]:
    """
    Ingest the JSON data value wrapped by the validator as a list of posts into
    this history and return a list of errors detected during ingestion.
    """
    errors: list[DefaceError] = []
    for item_data in data.to_list().items():
      try:
        post = ingest_post(item_data)
        self.add(post)
      except MergeError as err:
        errors.append(err)
      except ValidationError as err:
        err.args = err.args + (item_data.value,)
        errors.append(err)
    return errors

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
    posts.sort(key=lambda p: p.timestamp)
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
