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

import pytest

from typing import Any

from deface.error import DefaceError
from deface.model import (
  ExternalContext, Location, MediaMetaData, MediaType, PostHistory
)
from deface.ingest import ingest_into_history, ingest_post
from deface.validator import Validator

def test_ingest_post():
  data = Validator[Any]({
    "timestamp": 665,
    "attachments": [
      {
        "data": [
          {
            "external_context": {
              "url": "https://apparebit.com"
            }
          }
        ]
      },
      {
        "data": [
          {
            "place": {
              "name": "Somewhere",
              "coordinate": {
                "latitude": 665,
                "longitude": 42
              },
              "address": "1 Nowhere Place"
            }
          },
          {
            "place": {
              "name": "Somewhere",
              "coordinate": {
                "latitude": 665,
                "longitude": 42
              },
              "address": "1 Nowhere Place",
              "url": "https://apparebit.com"
            }
          },
        ]
      },
      {
        "data": [
          {
            "media": {
              "uri": "photo.jpg",
              "creation_timestamp": 111,
              "media_metadata": {
                "photo_metadata": {
                  "camera_make": "",
                  "camera_model": "",
                  "orientation": 1,
                  "upload_ip": "2600:1010:b00f:3630:d02:42a:880d:a301"
                }
              },
              "thumbnail": {
                "uri": "thumbnail.jpg"
              },
              "title": "Mobile Uploads",
              "description": "Ooh pretty!"
            }
          },
          {
            "media": {
              "uri": "video.mp4",
              "creation_timestamp": 222,
              "media_metadata": {
                "video_metadata": {
                  "upload_ip": "2600:1010:b00f:3630:d02:42a:880d:a301"
                }
              },
              "title": "Mobile Uploads",
              "comments": [
                {
                  "author": "Robert",
                  "comment": "Pretty!",
                  "timestamp": 444
                },
                {
                  "author": "Otto",
                  "comment": "Ugly!",
                  "timestamp": 445
                }
              ],
              "description": "A contested video"
            }
          }
        ]
      }
    ],
    "data": [
      {
        "post": "Ooh pretty!"
      }
    ],
    "title": "Photo and Video",
    "tags": [
      "pretty",
      "ugly"
    ]
  }, filename='valid-post')

  post = ingest_post(data)

  assert len(post.media) == 2

  media = post.media[0]
  assert media.creation_timestamp == 111
  assert media.description is None  # Removed because duplicate of post text.
  assert media.media_type == MediaType.PHOTO
  assert media.metadata == MediaMetaData(
    camera_make = '',
    camera_model = '',
    orientation = 1,
  )
  assert media.thumbnail == 'thumbnail.jpg'
  assert media.title == 'Mobile Uploads'
  assert media.upload_ip == '2600:1010:b00f:3630:d02:42a:880d:a301'
  assert media.upload_timestamp == None
  assert media.uri == 'photo.jpg'

  media = post.media[1]
  assert media.creation_timestamp == 222
  assert media.description == 'A contested video'
  assert media.media_type == MediaType.VIDEO
  assert media.metadata == None
  assert media.thumbnail is None
  assert media.title == 'Mobile Uploads'
  assert media.upload_ip == '2600:1010:b00f:3630:d02:42a:880d:a301'
  assert media.upload_timestamp == None
  assert media.uri == 'video.mp4'

  assert len(media.comments) == 2
  comment = media.comments[0]
  assert comment.author == 'Robert'
  assert comment.comment == 'Pretty!'
  assert comment.timestamp == 444
  comment = media.comments[1]
  assert comment.author == 'Otto'
  assert comment.comment == 'Ugly!'
  assert comment.timestamp == 445

  assert post.backdated_timestamp is None
  assert post.event is None
  assert isinstance(post.external_context, ExternalContext)
  assert post.external_context.url == 'https://apparebit.com'
  assert post.name is None
  assert post.places == (Location(
    name='Somewhere',
    latitude=665.0,
    longitude=42.0,
    address='1 Nowhere Place',
    url='https://apparebit.com',
  ),)
  assert post.post == "Ooh pretty!"
  assert post.tags == ("pretty", "ugly")
  assert len(post.text ) == 0
  assert post.timestamp == 665
  assert post.title == "Photo and Video"
  assert post.update_timestamp == None

# ------------------------------------------------------------------------------

TEST_CASES = [
  (42, 'malformed is not an object'),
  ({ 'answer': 42 }, 'malformed contains unexpected field answer'),
  ({ 'timestamp': '665' }, 'malformed.timestamp is not an integer'),

  # attachments
  ({ 'attachments': { 'data': [] }}, 'malformed.attachments is not a list'),
  ({ 'attachments': [{ 'data': 42 }]},
  'malformed.attachments[0].data is not a list'),

  # event attachment
  ({ 'attachments': [{ 'data': [{ 'event': 42 }]}]},
  'malformed.attachments[0].data[0].event is not an object'),
  ({ 'attachments': [{ 'data': [{ 'event': { 'name': 42 } }]}]},
  'malformed.attachments[0].data[0].event.name is not a string'),
  ({ 'attachments': [{ 'data': [{ 'event':
    { 'name': 'test', 'start_timestamp': '665' } }]}]},
  'malformed.attachments[0].data[0].event.start_timestamp is not an integer'),
  ({ 'attachments': [{ 'data': [{ 'event':
    { 'name': 'test', 'start_timestamp': 665, 'end_timestamp': '0' } }]}]},
  'malformed.attachments[0].data[0].event.end_timestamp is not an integer'),
  ({ 'timestamp': 1, 'attachments': [{ 'data': [{ 'event':
    { 'name': 'test', 'start_timestamp': 665, 'end_timestamp': 0 } }]}]},
  lambda p: (
      p.event.name == 'test'
      and p.event.start_timestamp == 665
      and p.event.end_timestamp == 0
  )),

  # external_context attachment
  ({ 'attachments': [{ 'data': [{ 'external_context': 665 }]}]},
  'malformed.attachments[0].data[0].external_context is not an object'),
  ({ 'attachments': [{ 'data': [{ 'external_context': { 'url': 0 }}]}]},
  'malformed.attachments[0].data[0].external_context.url is not a string'),
  ({ 'timestamp': 1, 'attachments': [{ 'data': [{ 'external_context':
    { 'url': 'https://apparebit.com' }}]}]},
  lambda p: p.external_context.url == 'https://apparebit.com'),
  ({ 'attachments': [{ 'data': [{ 'external_context':
    { 'url': 'https://apparebit.com', 'source': 13 }}]}]},
  'malformed.attachments[0].data[0].external_context.source is not a string'),
  ({ 'timestamp': 1, 'attachments': [{ 'data': [{ 'external_context':
    { 'url': 'https://apparebit.com', 'source': 'Apparebit' }}]}]},
  lambda p: p.external_context.source == 'Apparebit'),
  ({ 'attachments': [{ 'data': [{ 'external_context':
    { 'url': 'https://apparebit.com', 'name': 13 }}]}]},
  'malformed.attachments[0].data[0].external_context.name is not a string'),
  ({ 'timestamp': 1, 'attachments': [{ 'data': [{ 'external_context':
    { 'url': 'https://apparebit.com', 'name': 'Apparebit' }}]}]},
  lambda p: p.external_context.name == 'Apparebit'),

  # media attachment
  ({ 'attachments': [{ 'data': [{ 'media': 665 }]}]},
  'malformed.attachments[0].data[0].media is not an object'),

  # comments on media attachment
  ({ 'attachments': [{ 'data': [{ 'media': { 'comments': None } }]}]},
  'malformed.attachments[0].data[0].media.comments is not a list'),
  ({ 'attachments': [{ 'data': [{ 'media': { 'comments': [{
    'author': None }]}}]}]},
  'malformed.attachments[0].data[0].media.comments[0].author is not a string'),
  ({ 'attachments': [{ 'data': [{ 'media': { 'comments': [{
    'author': 'Robert', 'comment': 13 }]}}]}]},
  'malformed.attachments[0].data[0].media.comments[0].comment is not a string'),
  ({ 'attachments': [{ 'data': [{ 'media': { 'comments': [{
    'author': 'Robert', 'comment': 'says', 'timestamp': 'time' }]}}]}]},
  'malformed.attachments[0].data[0].media.comments[0].timestamp is not an integer'),

  # creation_timstamp on media attachment
  ({ 'attachments': [{ 'data': [{ 'media': {
    'comments': [{ 'author': 'Robert', 'comment': 'says', 'timestamp': 665 }],
    'creation_timestamp': None,
    }}]}]},

  # description on media attachment
  'malformed.attachments[0].data[0].media.creation_timestamp is not an integer'),
  ({ 'attachments': [{ 'data': [{ 'media': {
    'comments': [{ 'author': 'Robert', 'comment': 'says', 'timestamp': 665 }],
    'creation_timestamp': 2000,
    'description': None
    }}]}]},
  'malformed.attachments[0].data[0].media.description is not a string'),

  # media_metadata on media attachment (part 1)
  ({ 'attachments': [{ 'data': [{ 'media': {
    'comments': [{ 'author': 'Robert', 'comment': 'says', 'timestamp': 665 }],
    'creation_timestamp': 2000,
    'description': 'ooh, a photo',
    'media_metadata': 'boo'
    }}]}]},
  'malformed.attachments[0].data[0].media.media_metadata is not an object'),
  ({ 'attachments': [{ 'data': [{ 'media': {
    'comments': [{ 'author': 'Robert', 'comment': 'says', 'timestamp': 665 }],
    'creation_timestamp': 2000,
    'media_metadata': { 'thing_metadata': {}}
    }}]}]},
  'malformed.attachments[0].data[0].media.media_metadata '
    'contains unexpected field thing_metadata'),
  ({ 'attachments': [{ 'data': [{ 'media': {
    'comments': [{ 'author': 'Robert', 'comment': 'says', 'timestamp': 665 }],
    'creation_timestamp': 2000,
    'media_metadata': { 'photo_metadata': 13 }
    }}]}]},
  'malformed.attachments[0].data[0].media.media_metadata.photo_metadata '
    'is not an object'),
  ({ 'attachments': [{ 'data': [{ 'media': {
    'comments': [{ 'author': 'Robert', 'comment': 'says', 'timestamp': 665 }],
    'creation_timestamp': 2000,
    'media_metadata': { 'photo_metadata': { 'upload_ip': None } }
    }}]}]},
  'malformed.attachments[0].data[0].media.media_metadata.'
    'photo_metadata.upload_ip is not a string'),

  # thumbnail on media attachment
  ({ 'attachments': [{ 'data': [{ 'media': {
    'comments': [{ 'author': 'Robert', 'comment': 'says', 'timestamp': 665 }],
    'creation_timestamp': 2000,
    'media_metadata': { 'photo_metadata': { 'upload_ip': '127.0.0.1' }},
    'thumbnail': ''
    }}]}]},
  'malformed.attachments[0].data[0].media.thumbnail is not an object'),
  ({ 'attachments': [{ 'data': [{ 'media': {
    'comments': [{ 'author': 'Robert', 'comment': 'says', 'timestamp': 665 }],
    'creation_timestamp': 2000,
    'media_metadata': { 'photo_metadata': { 'upload_ip': '127.0.0.1' }},
    'thumbnail': { 'uri': 42 }
    }}]}]},
  'malformed.attachments[0].data[0].media.thumbnail.uri is not a string'),

  # title on media attachment
  ({ 'attachments': [{ 'data': [{ 'media': {
    'comments': [{ 'author': 'Robert', 'comment': 'says', 'timestamp': 665 }],
    'creation_timestamp': 2000,
    'media_metadata': { 'photo_metadata': { 'upload_ip': '127.0.0.1' }},
    'thumbnail': { 'uri': 'thumbnail.jpg' },
    'title': 1968,
    }}]}]},
  'malformed.attachments[0].data[0].media.title is not a string'),

  # uri on media attachment
  ({ 'attachments': [{ 'data': [{ 'media': {
    'comments': [{ 'author': 'Robert', 'comment': 'says', 'timestamp': 665 }],
    'creation_timestamp': 2000,
    'media_metadata': { 'photo_metadata': { 'upload_ip': '127.0.0.1' }},
    'title': 'an image',
    'uri': None
    }}]}]},
  'malformed.attachments[0].data[0].media.uri is not a string'),

  # media attachment
  ({ 'timestamp': 1,
    'attachments': [{ 'data': [{ 'media': {
    'comments': [{ 'author': 'Robert', 'comment': 'says', 'timestamp': 665 }],
    'creation_timestamp': 2000,
    'media_metadata': { 'photo_metadata': { 'upload_ip': '127.0.0.1' }},
    'title': 'an image',
    'uri': 'photo.jpg'
    }}]}]},
  lambda p: (
    p.media[0].comments[0].author == 'Robert'
    and p.media[0].comments[0].comment == 'says'
    and p.media[0].comments[0].timestamp == 665
    and p.media[0].creation_timestamp == 2000
    and p.media[0].media_type == MediaType.PHOTO
    and p.media[0].metadata is None
    and p.media[0].title == 'an image'
    and p.media[0].upload_ip == '127.0.0.1'
    and p.media[0].uri == 'photo.jpg'
  )),

  # media_metadata on media attachment (part 2)
  ({ 'attachments': [{ 'data': [{ 'media': {
    'creation_timestamp': 2000, 'title': 'image', 'uri': 'photo.jpg',
    'media_metadata': { 'photo_metadata': { 'upload_ip': '127.0.0.1',
      'upload_timestamp': None
    }}}}]}]},
  'malformed.attachments[0].data[0].media.media_metadata.photo_metadata'
    '.upload_timestamp is not an integer'),
  ({ 'attachments': [{ 'data': [{ 'media': {
    'creation_timestamp': 2000, 'title': 'image', 'uri': 'photo.jpg',
    'media_metadata': { 'photo_metadata': { 'upload_ip': '127.0.0.1',
      'upload_timestamp': 2001,
      'camera_make': 665,
    }}}}]}]},
  'malformed.attachments[0].data[0].media.media_metadata.photo_metadata'
    '.camera_make is not a string'),
  ({ 'attachments': [{ 'data': [{ 'media': {
    'creation_timestamp': 2000, 'title': 'image', 'uri': 'photo.jpg',
    'media_metadata': { 'photo_metadata': { 'upload_ip': '127.0.0.1',
      'camera_make': '',
      'camera_model': 665
    }}}}]}]},
  'malformed.attachments[0].data[0].media.media_metadata.photo_metadata'
    '.camera_model is not a string'),
  ({ 'attachments': [{ 'data': [{ 'media': {
    'creation_timestamp': 2000, 'title': 'image', 'uri': 'photo.jpg',
    'media_metadata': { 'photo_metadata': { 'upload_ip': '127.0.0.1',
      'camera_model': '',
      'exposure': None
    }}}}]}]},
  'malformed.attachments[0].data[0].media.media_metadata.photo_metadata'
    '.exposure is not a string'),
  ({ 'attachments': [{ 'data': [{ 'media': {
    'creation_timestamp': 2000, 'title': 'image', 'uri': 'photo.jpg',
    'media_metadata': { 'photo_metadata': { 'upload_ip': '127.0.0.1',
      'exposure': '',
      'f_stop': None
    }}}}]}]},
  'malformed.attachments[0].data[0].media.media_metadata.photo_metadata'
    '.f_stop is not a string'),
  ({ 'attachments': [{ 'data': [{ 'media': {
    'creation_timestamp': 2000, 'title': 'image', 'uri': 'photo.jpg',
    'media_metadata': { 'photo_metadata': { 'upload_ip': '127.0.0.1',
      'f_stop': '',
      'iso_speed': '',
    }}}}]}]},
  'malformed.attachments[0].data[0].media.media_metadata.photo_metadata'
    '.iso_speed is not an integer'),
  ({ 'attachments': [{ 'data': [{ 'media': {
    'creation_timestamp': 2000, 'title': 'image', 'uri': 'photo.jpg',
    'media_metadata': { 'photo_metadata': { 'upload_ip': '127.0.0.1',
      'iso_speed': 665,
      'latitude': 'lat'
    }}}}]}]},
  'malformed.attachments[0].data[0].media.media_metadata.photo_metadata'
    '.latitude is neither integer nor float'),
  ({ 'attachments': [{ 'data': [{ 'media': {
    'creation_timestamp': 2000, 'title': 'image', 'uri': 'photo.jpg',
    'media_metadata': { 'photo_metadata': { 'upload_ip': '127.0.0.1',
      'latitude': 11,
      'longitude': 'long'
    }}}}]}]},
  'malformed.attachments[0].data[0].media.media_metadata.photo_metadata'
    '.longitude is neither integer nor float'),
  ({ 'attachments': [{ 'data': [{ 'media': {
    'creation_timestamp': 2000, 'title': 'image', 'uri': 'photo.jpg',
    'media_metadata': { 'photo_metadata': { 'upload_ip': '127.0.0.1',
      'longitude': 3.14,
      'modified_timestamp': None
    }}}}]}]},
  'malformed.attachments[0].data[0].media.media_metadata.photo_metadata'
    '.modified_timestamp is not an integer'),
  ({ 'attachments': [{ 'data': [{ 'media': {
    'creation_timestamp': 2000, 'title': 'image', 'uri': 'photo.jpg',
    'media_metadata': { 'photo_metadata': { 'upload_ip': '127.0.0.1',
      'modified_timestamp': 2002,
      'orientation': 'gay'
    }}}}]}]},
  'malformed.attachments[0].data[0].media.media_metadata.photo_metadata'
    '.orientation is not an integer'),
  ({ 'attachments': [{ 'data': [{ 'media': {
    'creation_timestamp': 2000, 'title': 'image', 'uri': 'photo.jpg',
    'media_metadata': { 'photo_metadata': { 'upload_ip': '127.0.0.1',
      'orientation': 1,
      'original_height': None
    }}}}]}]},
  'malformed.attachments[0].data[0].media.media_metadata.photo_metadata'
    '.original_height is not an integer'),
  ({ 'attachments': [{ 'data': [{ 'media': {
    'creation_timestamp': 2000, 'title': 'image', 'uri': 'photo.jpg',
    'media_metadata': { 'photo_metadata': { 'upload_ip': '127.0.0.1',
      'original_height': 3000,
      'original_width': None,
    }}}}]}]},
  'malformed.attachments[0].data[0].media.media_metadata.photo_metadata'
    '.original_width is not an integer'),
  ({ 'attachments': [{ 'data': [{ 'media': {
    'creation_timestamp': 2000, 'title': 'image', 'uri': 'photo.jpg',
    'media_metadata': { 'photo_metadata': { 'upload_ip': '127.0.0.1',
      'original_width': 2000,
      'taken_timestamp': None,
    }}}}]}]},
  'malformed.attachments[0].data[0].media.media_metadata.photo_metadata'
    '.taken_timestamp is not an integer'),
  ({ 'timestamp': 1,
    'attachments': [{ 'data': [{ 'media': {
    'creation_timestamp': 2000, 'title': 'image', 'uri': 'photo.jpg',
    'media_metadata': { 'photo_metadata': { 'upload_ip': '127.0.0.1',
      'taken_timestamp': 1999
    }}}}]}]},
  lambda p: p.media[0].metadata.taken_timestamp == 1999),

  # name attachment
  ({ 'attachments': [{ 'data': [{ 'name': 665 }]}]},
  'malformed.attachments[0].data[0].name is not a string'),
  ({ 'timestamp': 1, 'attachments': [{ 'data': [{ 'name': 'Rob' }]}]},
  lambda p: p.name == 'Rob'),

  # place attachment
  ({ 'attachments': [{ 'data': [{ 'place': 665 }]}]},
  'malformed.attachments[0].data[0].place is not an object'),
  ({ 'attachments': [{ 'data': [{ 'place': { 'name': 13 } }]}]},
  'malformed.attachments[0].data[0].place.name is not a string'),
  ({ 'timestamp': 1,
    'attachments': [{ 'data': [{ 'place': { 'name': 'somewhere' } }]}]},
  lambda p: p.places[0].name == 'somewhere'),
  ({ 'attachments': [{ 'data': [{ 'place': {
    'name': 'somewhere', 'address': 42 } }]}]},
  'malformed.attachments[0].data[0].place.address is not a string'),
  ({ 'timestamp': 1,
    'attachments': [{ 'data': [{ 'place': {
    'name': 'somewhere', 'address': 'an avenue' } }]}]},
  lambda p: p.places[0].address == 'an avenue'),
  ({ 'attachments': [{ 'data': [{ 'place': {
    'name': 'somewhere', 'coordinate': 42 } }]}]},
  'malformed.attachments[0].data[0].place.coordinate is not an object'),
  ({ 'attachments': [{ 'data': [{ 'place': {
    'name': 'somewhere', 'coordinate': { 'latitude': 'long' }}}]}]},
  'malformed.attachments[0].data[0].place.coordinate.latitude '
  'is neither integer nor float'),
  ({ 'attachments': [{ 'data': [{ 'place': {
    'name': 'somewhere', 'coordinate': { 'latitude': 1.5, 'longitude': 'lat' }}}]}]},
  'malformed.attachments[0].data[0].place.coordinate.longitude '
  'is neither integer nor float'),
  ({ 'attachments': [{ 'data': [{ 'place': {
    'name': 'somewhere', 'coordinate': { }}}]}]},
  'malformed.attachments[0].data[0].place.coordinate '
  'is missing required field latitude'),
  ({ 'attachments': [{ 'data': [{ 'place': {
    'name': 'somewhere', 'coordinate': { 'value': 665 }}}]}]},
  'malformed.attachments[0].data[0].place.coordinate '
  'contains unexpected field value'),
  ({ 'timestamp': 1,
    'attachments': [{ 'data': [{ 'place': {
    'name': 'somewhere', 'coordinate': { 'latitude': 1.5, 'longitude': 3.2 }}}]}]},
  lambda p: p.places[0].latitude == 1.5 and p.places[0].longitude == 3.2),

  # text attachment
  ({ 'attachments': [{ 'data': [{ 'text': 42 }]}]},
  'malformed.attachments[0].data[0].text is not a string'),
  ({ 'timestamp': 1, 'attachments': [{ 'data': [{ 'text': 'textual' }]}]},
  lambda p: p.text[0] == 'textual'),
  ({ 'timestamp': 1,
    'attachments': [{ 'data': [{ 'text': 'textual' }, { 'text': 'texture' }]}]},
  lambda p: p.text[1] == 'texture'),

  # data
  ({ 'data': 42 }, 'malformed.data is not a list'),

  # backdated_timestamp data
  ({ 'data': [{ 'backdated_timestamp': 'tik' }]},
  'malformed.data[0].backdated_timestamp is not an integer'),
  ({ 'timestamp': 1, 'data': [{ 'backdated_timestamp': 665 }]},
  lambda p: p.backdated_timestamp == 665),

  # post data
  ({ 'data': [{ 'post': 13 }]}, 'malformed.data[0].post is not a string'),
  ({ 'timestamp': 1, 'data': [{ 'post': 'body' }]}, lambda p: p.post == 'body'),

  # update_timestamp data
  ({ 'data': [{ 'update_timestamp': 'tok' }]},
  'malformed.data[0].update_timestamp is not an integer'),
  ({ 'timestamp': 1, 'data': [{ 'update_timestamp': 42 }]},
  lambda p: p.update_timestamp == 42),

  # tags
  ({ 'tags': 42 }, 'malformed.tags is not a list'),
  ({ 'tags': [42] }, 'malformed.tags[0] is not a string'),
  ({ 'timestamp': 1, 'tags': ['#tag'] }, lambda p: p.tags[0] == '#tag'),

  # title
  ({ 'timestamp': 1, 'title': 42 }, 'malformed.title is not a string'),
  ({ 'timestamp': 1, 'title': 'The Title' }, lambda p: p.title == 'The Title'),
]

def test_per_field_validation():
  for structured_data, validation in TEST_CASES:
    if isinstance(validation, str):
      with pytest.raises(DefaceError) as exception_info:
        ingest_post(Validator[Any](structured_data, filename='malformed'))
      actual_message = exception_info.value.args[0]
      assert actual_message == validation
    else:
      post = ingest_post(Validator[Any](structured_data, filename='wellformed'))
      assert validation(post)

# ------------------------------------------------------------------------------

def test_ingest_many_posts():
  input = [
    # Repeated identical posts are recognized as well:
    { 'timestamp': 4, 'title': 'four' },
    { 'timestamp': 4, 'title': 'four' },
    { 'timestamp': 4, 'title': 'four' },
    # Two different posts with same timestamp remain two posts:
    { 'timestamp': 2, 'title': 'one' },
    { 'timestamp': 2, 'title': 'two' },
    # A single post remains a single post:
    { 'timestamp': 1 },
    # Two posts only differing on media become one post with two media:
    { 'timestamp': 3, 'attachments': [{ 'data': [{ 'media': {
      'creation_timestamp': 1,
      'media_metadata': { 'photo_metadata': { 'upload_ip': '127.0.0.1' }},
      'title': 'photo',
      'uri': 'one.jpg'
    }}]}]},
    { 'timestamp': 3, 'attachments': [{ 'data': [{ 'media': {
      'creation_timestamp': 2,
      'media_metadata': { 'photo_metadata': { 'upload_ip': '127.0.0.1' }},
      'title': 'photo',
      'uri': 'two.jpg'
    }}]}]},
    # A repetition of the previous post is recognized even after merging:
    { 'timestamp': 3, 'attachments': [{ 'data': [{ 'media': {
      'creation_timestamp': 2,
      'media_metadata': { 'photo_metadata': { 'upload_ip': '127.0.0.1' }},
      'title': 'photo',
      'uri': 'two.jpg'
    }}]}]},
  ]

  history = PostHistory()
  errors = ingest_into_history(
    Validator[Any](input, filename='history'),
    history
  )
  assert len(errors) == 0
  timeline = history.timeline()
  assert len(timeline) == 5

  print(timeline)
  assert timeline[0].timestamp == 1
  assert timeline[1].timestamp == 2
  assert timeline[2].timestamp == 2
  assert timeline[3].timestamp == 3
  assert timeline[4].timestamp == 4

