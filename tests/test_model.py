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

from deface.error import MergeError
from deface.model import (
  Comment, ExternalContext, Location, Media, MediaType, Post
)
from deface.serde import dumps, loads

def test_json():
  post1 = Post(
    timestamp=665,
    title='Alice',
    post='But what did the Dormouse say?',
    external_context=ExternalContext(
      url='https://gutenberg.org/cache/epub/28885/pg28885-images.html'
    ),
    media=tuple([
      Media(
        comments=tuple([
          Comment(
            author='Queen',
            comment='Nearly two miles high',
            timestamp=667,
          ),
          Comment(
            author='Alice',
            comment='Stuff and nonsense!',
            timestamp=669,
          ),
        ]),
        media_type=MediaType.PHOTO,
        upload_ip='127.0.0.1',
        uri='alice.jpg',
      ),
    ]),
    places=tuple([
      Location(
        name='Wonderland',
      ),
    ]),
    tags=tuple(['Hatter', 'Queen']),
    text=tuple(),
  )
  json_text = dumps(post1).encode('utf8')
  post2 = Post.from_dict(loads(json_text))
  assert post1 == post2

def test_merge_media() -> None:
  media1 = Media(
    comments=tuple(),
    media_type=MediaType.PHOTO,
    upload_ip='192.168.1.1',
    uri='somewhere.jpg',
    description="a picture",
    upload_timestamp=665,
  )

  media2 = Media(
    comments=tuple(),
    media_type=MediaType.PHOTO,
    upload_ip='192.168.1.1',
    uri='somewhere.jpg',
    description="a picture",
    upload_timestamp=665,
  )

  media3 = Media(
    comments=tuple([
      Comment(author='Alice', comment='wow', timestamp=1999),
    ]),
    media_type=MediaType.PHOTO,
    upload_ip='192.168.1.1',
    uri='somewhere.jpg',
    description="a picture",
    upload_timestamp=665,
  )

  media4 = Media(
    comments=tuple([
      Comment(author='Alice', comment='wow', timestamp=1999),
      Comment(author='Bob', comment='meh', timestamp=2000),
    ]),
    media_type=MediaType.PHOTO,
    upload_ip='192.168.1.1',
    uri='somewhere.jpg',
    description="a picture",
    upload_timestamp=665,
  )

  assert media1.is_mergeable_with(media1)
  assert media1.is_mergeable_with(media2)
  assert media1.is_mergeable_with(media3)
  assert media1.is_mergeable_with(media4)

  assert media2.is_mergeable_with(media2)
  assert media2.is_mergeable_with(media3)
  assert media2.is_mergeable_with(media4)

  assert media3.is_mergeable_with(media3)
  assert not media3.is_mergeable_with(media4)

  assert media1.merge(media2) == media1
  assert media1.merge(media3) == media3
  assert media3.merge(media1) == media3

  with pytest.raises(MergeError) as x:
    media3.merge(media4)
  assert x.value.args[0].startswith('Unable to merge media descriptors')
