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

from deface.error import DefaceError, MergeError, ValidationError
from deface.json_data import JsonData
from deface.model import (
  Comment, Event, ExternalContext, Location, Media, MediaType, Post, PostHistory
)

_COMMENT_KEYS: set[str] = { 'author', 'comment', 'timestamp' }

def ingest_comment(data: JsonData) -> Comment:
  """
  Ingest the current JSON data value as a comment.
  """
  fields = data.to_object(_COMMENT_KEYS)
  data['author'].to_string()
  data['comment'].to_string()
  data['timestamp'].to_integer()
  return Comment(**fields)

# ------------------------------------------------------------------------------

_EVENT_KEYS = { 'name', 'start_timestamp', 'end_timestamp' }

def ingest_event(data: JsonData) -> Event:
  """
  Ingest the current JSON data value as an event.
  """
  fields = data.to_object(_EVENT_KEYS)
  data['name'].to_string()
  data['start_timestamp'].to_integer()
  data['end_timestamp'].to_integer()
  return Event(**fields)

# ------------------------------------------------------------------------------

_EXTERNAL_CONTEXT_KEYS = { 'name', 'source', 'url' }

def ingest_external_context(data: JsonData) -> ExternalContext:
  """
  Ingest the current JSON data value as an external context.
  """
  fields = data.to_object(_EXTERNAL_CONTEXT_KEYS)
  if 'name' in data.value:
    data['name'].to_string()
  if 'source' in data.value:
    data['source'].to_string()
  data['url'].to_string()
  return ExternalContext(**fields)

# ------------------------------------------------------------------------------

_LOCATION_KEYS: set[str] = { 'address', 'coordinate', 'name', 'url' }
_COORDINATE_KEYS: set[str] = { 'latitude', 'longitude' }

def ingest_location(data: JsonData) -> Location:
  """
  Ingest the current JSON data value as a location.
  """
  data.to_object(_LOCATION_KEYS)
  fields = {}
  if 'address' in data.value:
    fields['address'] = data['address'].to_string()

  if 'coordinate' in data.value:
    with data['coordinate']:
      data.to_object(_COORDINATE_KEYS)
      fields['latitude'] = data['latitude'].to_float()
      fields['longitude'] = data['longitude'].to_float()

  fields['name'] = data['name'].to_string()
  if 'url' in data.value:
    fields['url'] = data['url'].to_string()

  return Location(**fields)

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

def ingest_media(data: JsonData) -> Media:
  """
  Ingest the current JSON data value as media.
  """
  data.to_object(_MEDIA_KEYS)
  fields = {}

  comments = []
  if 'comments' in data.value:
    with data['comments']:
      for index in data.to_list_range():
        with data[index]:
          comments.append(ingest_comment(data))
  fields['comments'] = tuple(comments)

  #if 'creation_timestamp' in data.value:
  fields['creation_timestamp'] = data['creation_timestamp'].to_integer()

  if 'description' in data.value:
    fields['description'] = data['description'].to_string()

  #if 'media_metadata' in data.value:
  with data['media_metadata']:
    key = data.to_singleton_object(_METADATA_KEYS)
    fields['media_type'] = (
      MediaType.PHOTO
      if key == 'photo_metadata'
      else MediaType.VIDEO
    )
    fields['metadata'] = data[key].to_object()
  #else:
  #  fields['metadata'] = dict()

  if 'thumbnail' in data.value:
    with data['thumbnail']:
      data.to_singleton_object(['uri'])
      fields['thumbnail'] = data['uri'].to_string()

  #if 'title' in data.value:
  fields['title'] = data['title'].to_string()

  fields['uri'] = data['uri'].to_string()

  # if not 'media_type' in fields:
  #   fields['media_type'] = (
  #     MediaType.VIDEO
  #     if fields['uri'].endswith('.mp4')
  #     else MediaType.PHOTO
  #   )

  return Media(**fields)

# ------------------------------------------------------------------------------

_ATTACHMENT_KEYS: set[str] = {
  'event', 'external_context', 'media', 'name', 'place'
}
_DATA_KEYS: set[str] = { 'backdated_timestamp', 'post', 'update_timestamp' }
_POST_KEYS: set[str] = { 'attachments', 'data', 'tags', 'timestamp', 'title' }

def _handle_attachments(
  data: JsonData, fields: dict
) -> tuple[list[Media], list[Location]]:
  all_media = []
  all_places = []

  for index in data.to_list_range():
    with data[index]:
      data.to_singleton_object(['data'])
      with data['data']:
        for index2 in data.to_list_range():
          with data[index2]:
            key = data.to_singleton_object(_ATTACHMENT_KEYS)
            if key == 'media':
              with data['media']:
                all_media.append(ingest_media(data))
            elif key == 'place':
              with data['place']:
                a_place = ingest_location(data)
                did_merge = False
                for index, another_place in enumerate(all_places):
                  try:
                    all_places[index] = a_place.merge(another_place)
                    did_merge = True
                  except:
                    pass
                if not did_merge:
                  all_places.append(a_place)
            elif key in fields:
              data.signal(f'has repeated values for field "{key}"')
            elif key == 'event':
              with data['event']:
                fields['event'] = ingest_event(data)
            elif key == 'external_context':
              with data['external_context']:
                fields['external_context'] = ingest_external_context(data)
            else: # key == 'name'
              fields['name'] = data['name'].to_string()

  return all_media, all_places

def ingest_post(data: JsonData) -> Post:
  """
  Ingest the current JSON data value as a post.
  """
  data.to_object(_POST_KEYS)
  fields = {}

  if 'attachments' in data.value:
    with data['attachments']:
      all_media, all_places = _handle_attachments(data, fields)
  else:
    all_media = list()
    all_places = list()

  if 'data' in data.value:
    with data['data']:
      for index in data.to_list_range():
        with data[index]:
          key = data.to_singleton_object(_DATA_KEYS)
          if key in fields:
            data.signal(f'has single, redundant field "{key}"')
          elif key == 'post':
            fields['post'] = data['post'].to_string()
          else:
            fields[key] = data[key].to_integer()

  tags = []
  if 'tags' in data.value:
    with data['tags']:
      for index in data.to_list_range():
        tags.append(data[index].to_string())
  fields['tags'] = tuple(tags)

  fields['timestamp'] = data['timestamp'].to_integer()
  if 'title' in data.value:
    fields['title'] = data['title'].to_string()

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

  return Post(**fields)

def ingest_into_history(
  data: JsonData, history: PostHistory
) -> list[DefaceError]:
  """
  Ingest the current JSON data value as list of posts into the given history.
  This function returns a list of ingestion errors.
  """
  errors = []
  for index in data.to_list_range():
    with data[index]:
      try:
        post = ingest_post(data)
        history.add(post)
      except MergeError as err:
        errors.append(err)
      except ValidationError as err:
        err.args = err.args + (data.value,)
        errors.append(err)
  return errors
