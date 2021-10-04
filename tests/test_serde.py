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
  assert restore_utf8(
    rb'Instagram Post by Ro\u00cc\u0081isi\u00cc\u0081n Murphy '
    rb'\u00e2\u0080\u00a2 May  6, 2020 at 05:42AM EDT'
  ).decode('utf8') == 'Instagram Post by Róisín Murphy • May  6, 2020 at 05:42AM EDT'

  assert restore_utf8(
    rb'Yay Cyrillic: \u00d0\u009d\u00d0\u00b5\u00d1\u0082!'
  ).decode('utf8') == 'Yay Cyrillic: Нет!'

  # An additional backslash turns a unicode escape into the text of a unicode escape.
  assert restore_utf8(
    rb"sequences such as '\\u00e2\\u009c\\u0094\\u00ef\\u00b8\\u008f'"
  ).decode('utf8') == r"sequences such as '\\u00e2\\u009c\\u0094\\u00ef\\u00b8\\u008f'"


def test_loads_dumps():
  json = loads(b'{"answer": 42}')

  assert isinstance(json, dict)
  assert json['answer'] == 42

  json['some_noise'] = None
  json['noise'] = []
  json['more_noise'] = ()

  text = dumps(json)

  assert text == '{"answer": 42}'
