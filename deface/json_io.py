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
import enum
import json
import re

from binascii import unhexlify
from typing import Any, Union

JsonT = Union[None, bool, int, float, str, ]

_BROKEN_ESCAPE = re.compile(rb'\\u00([0-9a-f][0-9a-f])', re.I)

def restore_utf8(data: bytes) -> bytes:
  """
  Restore the UTF-8 encoding for files exported from Facebook. Such files may
  appear to be valid JSON at first but nonetheless encode all non-ASCII
  characters incorrectly. That is the result of Facebook first generating JSON
  text in UTF-8 with only double-quotes and newlines escaped (as ``\\"`` and
  ``\\n``, respectively) and thereafter encoding all bytes that aren't also
  valid ASCII as faux unicode escapes of the form ``\\u00xx``. This function
  undoes that second faulty encoding step. Its result can safely be parsed as
  UTF-8-encoded JSON text.
  """
  return re.sub(_BROKEN_ESCAPE, lambda match: unhexlify(match.group(1)), data)

def read_json(path: str) -> JsonT:
  """
  Read the file with the given path as a JSON file with personal data exported
  from Facebook. This function undoes Facebook's faulty encoding and then parses
  the JSON.
  """
  with open(path, 'rb') as file:
    return json.loads(restore_utf8(file.read()))

def default(value: Any) -> Union[str, dict[str, Any]]:
  """
  Convert the given value, which cannot be encoded as JSON, to an equivalent
  value that can be encoded as JSON. This function returns the name of enum
  constants and the equivalent dictionary for dataclasses. For all other values,
  it raises a :py:class:`TypeError`.
  """
  if isinstance(value, enum.Enum):
    return value.name
  elif dataclasses.is_dataclass(value):
    return dataclasses.asdict(value)
  raise TypeError(f'Value "{value}" cannot be encoded as JSON')

def dumps(value: Any, **kwargs: Any) -> str:
  return json.dumps(value, default=default, **kwargs)
