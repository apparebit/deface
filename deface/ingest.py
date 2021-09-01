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

import dataclasses
from typing import Any

from deface.error import DefaceError, MergeError, ValidationError
from deface.model import (
  Comment, Event, ExternalContext, Location, Media, MediaType, Post, PostHistory
)
from deface.validator import Validator

_COMMENT_KEYS: set[str] = { 'author', 'comment', 'timestamp' }

def ingest_comment(data: Validator[Any]) -> Comment:
  """
  Ingest the current JSON data value as a comment.
  """
  comment_data = data.to_object(valid_keys=_COMMENT_KEYS)
  fields = comment_data.value
  comment_data['author'].to_string()
  comment_data['comment'].to_string()
  comment_data['timestamp'].to_integer()
  return Comment(**fields) # type: ignore

# ------------------------------------------------------------------------------

_EVENT_KEYS = { 'name', 'start_timestamp', 'end_timestamp' }

def ingest_event(data: Validator[Any]) -> Event:
  """
  Ingest the current JSON data value as an event.
  """
  event_data = data.to_object(valid_keys=_EVENT_KEYS)
  fields = event_data.value
  event_data['name'].to_string()
  event_data['start_timestamp'].to_integer()
  event_data['end_timestamp'].to_integer()
  return Event(**fields) # type: ignore

# ------------------------------------------------------------------------------

_EXTERNAL_CONTEXT_KEYS = { 'name', 'source', 'url' }

def ingest_external_context(data: Validator[Any]) -> ExternalContext:
  """
  Ingest the current JSON data value as an external context.
  """
  context_data = data.to_object(valid_keys=_EXTERNAL_CONTEXT_KEYS)
  fields = context_data.value
  if 'name' in context_data.value:
    context_data['name'].to_string()
  if 'source' in context_data.value:
    context_data['source'].to_string()
  context_data['url'].to_string()
  return ExternalContext(**fields) # type: ignore

# ------------------------------------------------------------------------------

_LOCATION_KEYS: set[str] = { 'address', 'coordinate', 'name', 'url' }
_COORDINATE_KEYS: set[str] = { 'latitude', 'longitude' }

def ingest_location(data: Validator[Any]) -> Location:
  """
  Ingest the current JSON data value as a location.
  """
  location_data = data.to_object(valid_keys=_LOCATION_KEYS)
  fields = {}
  if 'address' in location_data.value:
    fields['address'] = location_data['address'].to_string().value

  if 'coordinate' in location_data.value:
    coordinates = location_data['coordinate'].to_object(
      valid_keys=_COORDINATE_KEYS
    )
    fields['latitude'] = float(coordinates['latitude'].to_number().value)
    fields['longitude'] = float(coordinates['longitude'].to_number().value)

  fields['name'] = location_data['name'].to_string().value
  if 'url' in location_data.value:
    fields['url'] = location_data['url'].to_string().value

  return Location(**fields) # type: ignore

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
  Ingest the current JSON data value as media.
  """
  media_data = data.to_object(valid_keys=_MEDIA_KEYS)
  fields = {}

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

  media_metadata = media_data['media_metadata'].to_object(
    valid_keys=_METADATA_KEYS, singleton=True
  )
  metadata_key = media_metadata.only_key
  fields['media_type'] = (
    MediaType.PHOTO
    if metadata_key == 'photo_metadata'
    else MediaType.VIDEO
  )
  fields['metadata'] = media_metadata[metadata_key].to_object().value

  if 'thumbnail' in media_data.value:
    thumbnail_data = media_data['thumbnail'].to_object(
      valid_keys={'uri'}, singleton=True
    )
    fields['thumbnail'] = thumbnail_data['uri'].to_string().value

  fields['title'] = media_data['title'].to_string().value
  fields['uri'] = media_data['uri'].to_string().value

  return Media(**fields) # type: ignore

# ------------------------------------------------------------------------------

_ATTACHMENT_KEYS: set[str] = {
  'event', 'external_context', 'media', 'name', 'place', 'text'
}
_DATA_KEYS: set[str] = { 'backdated_timestamp', 'post', 'update_timestamp' }
_POST_KEYS: set[str] = { 'attachments', 'data', 'tags', 'timestamp', 'title' }

def _handle_attachments(
  data: Validator[Any], fields: dict[str, Any]
) -> tuple[list[Media], list[Location], list[str]]:
  all_media: list[Media] = []
  all_places: list[Location] = []
  all_text: list[str] = []

  for outer_item in data.to_list().items():
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
      elif key in fields:
        inner_data.raise_invalid(f'has repeated value for field "{key}"')
      elif key == 'event':
        fields['event'] = ingest_event(inner_data[key])
      elif key == 'external_context':
        fields['external_context'] = ingest_external_context(inner_data[key])
      else: # key == 'name'
        fields['name'] = inner_data[key].to_string().value

  return all_media, all_places, all_text

def ingest_post(data: Validator[Any]) -> Post:
  """
  Ingest the current JSON data value as a post.
  """
  post_data = data.to_object(valid_keys=_POST_KEYS)
  fields: dict[str, Any] = {}

  if 'attachments' in post_data.value:
    all_media, all_places, all_text = _handle_attachments(
      post_data['attachments'], fields
    )
  else:
    all_media: list[Media] = list()
    all_places: list[Location] = list()
    all_text: list[str] = list()

  if 'data' in post_data.value:
    for item in post_data['data'].to_list().items():
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
  fields['place'] = tuple(all_places)
  fields['text'] = tuple(all_text)

  return Post(**fields) # type: ignore

def ingest_into_history(
  data: Validator[Any], history: PostHistory
) -> list[DefaceError]:
  """
  Ingest the current JSON data value as list of posts into the given history.
  This function returns a list of ingestion errors.
  """
  errors: list[DefaceError] = []
  for item_data in data.to_list().items():
    try:
      post = ingest_post(item_data)
      history.add(post)
    except MergeError as err:
      errors.append(err)
    except ValidationError as err:
      err.args = err.args + (data.value,)
      errors.append(err)
  return errors
