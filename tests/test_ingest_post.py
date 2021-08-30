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

from deface.error import ValidationError
from deface.model import ExternalContext, Location, MediaType
from deface.ingest import ingest_post
from deface.validator import Validator

def test_ingest_post():
  data = Validator({
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
  assert media.metadata == {
    'upload_ip': '2600:1010:b00f:3630:d02:42a:880d:a301'
  }
  assert media.thumbnail == 'thumbnail.jpg'
  assert media.title == 'Mobile Uploads'
  assert media.uri == 'photo.jpg'

  media = post.media[1]
  assert media.creation_timestamp == 222
  assert media.description == 'A contested video'
  assert media.media_type == MediaType.VIDEO
  assert media.metadata == {
    'upload_ip': '2600:1010:b00f:3630:d02:42a:880d:a301'
  }
  assert media.thumbnail is None
  assert media.title == 'Mobile Uploads'
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
  assert post.place == (Location(
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

def test_fail_validation():
  with pytest.raises(ValidationError) as exception_info:
    ingest_post(Validator({ 'timestamp': '665' }, filename='malformed1'))
  assert exception_info.value.args[0] == 'malformed1.timestamp is not an integer'
