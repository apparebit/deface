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

from deface.serde import dumps, loads, restore_utf8

def test_restore_from_mojibake():
  text = restore_utf8(
    b'Instagram Post by Ro\\u00cc\\u0081isi\\u00cc\\u0081n Murphy '
    b'\\u00e2\\u0080\\u00a2 May  6, 2020 at 05:42AM EDT'
  ).decode('utf8')

  assert text == 'Instagram Post by Róisín Murphy • May  6, 2020 at 05:42AM EDT'

def test_loads_dumps():
  json = loads(b'{"answer": 42}')

  assert isinstance(json, dict)
  assert json['answer'] == 42

  json['some_noise'] = None
  json['noise'] = []
  json['more_noise'] = ()

  text = dumps(json)

  assert text == '{"answer": 42}'
