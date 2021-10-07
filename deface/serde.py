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

__all__ = [
  'JsonT',
  'restore_utf8',
  'loads',
  'prepare',
  'dumps'
]

JsonT = Union[None, bool, int, float, str, list[Any], dict[str, Any]]

_ACTUAL_ESCAPE = re.compile(rb'''
  (?<!\\)                    # No leading backslash,
  ((\\\\)*)                  # followed by an even number of backslashes,
  \\u00([0-9a-f][0-9a-f])    # followed by a unicode escape.
  ''',
  re.VERBOSE | re.IGNORECASE
)

def restore_utf8(data: bytes) -> bytes:
  """
  Restore the UTF-8 encoding for files exported from Facebook. Such files may
  appear to be valid JSON at first but nonetheless encode all non-ASCII
  characters incorrectly. Notably, what should just be UTF-8 byte values are
  Unicode escape sequences of the form ``\\u00xx``. This function replaces such
  sequences with the byte value given by the last two hexadecimal digits. It
  leaves all other escape sequences in place.

  NB: If an arbitrary but *odd* number of backslashes precedes ``u00xx``, the
  final backslash together with the ``u00xx`` forms a unicode escape sequence.
  However, if an *even* number of backslashes precedes ``u00xx``, there is *no*
  unicode escape sequence but text discussing unicode escape sequences.

  This function should be invoked on the bytes of JSON text, before parsing.
  """
  return re.sub(
    _ACTUAL_ESCAPE,
    lambda match: match.group(1) + unhexlify(match.group(3)),
    data
  )

def loads(data: bytes, **kwargs: Any) -> JsonT:
  """
  Return the result of deserializing a value from the given JSON text. This
  function simply wraps an invocation of the eponymous function in Python's
  ``json`` package — after applying :py:func:`restore_utf8` to the given
  ``data``. It passes the keyword arguments through.
  """
  return json.loads(restore_utf8(data), **kwargs)

_EMPTY_LIST: list[Any] = []
_EMPTY_TUPLE: tuple[Any, ...] = ()

def _is_void(value: Any) -> bool:
  return value is None or value == _EMPTY_LIST or value == _EMPTY_TUPLE

def prepare(data: Any) -> Any:
  """
  Prepare the given value for serialization to JSON. This function recursively
  replaces enumeration constants with their names, lists and tuples with
  equivalent lists, and dataclasses and dictionaries with equivalent
  dictionaries. While generating equivalent dictionaries, it also filters out
  entries that are ``None``, the empty list ``[]``, or the empty tuple ``()``.
  All other values remain unchanged.
  """
  if dataclasses.is_dataclass(data):
    result = {}
    for field in dataclasses.fields(data):
      value = getattr(data, field.name)
      if not _is_void(value):
        result[field.name] = prepare(value)
    return result
  elif isinstance(data, dict):
    return { k: prepare(v) for k, v in data.items() if not _is_void(v) }
  elif isinstance(data, (list, tuple)):
    return [prepare(v) for v in data]
  elif isinstance(data, enum.Enum):
    return data.name
  else:
    return data

def dumps(data: Any, **kwargs: Any) -> str:
  """
  Return the result of serializing the given value as JSON text. This function
  simply wraps an invocation of the eponymous function in Python's ``json``
  package — after applying :py:func:`prepare` to the given ``data``. It passes
  the keyword arguments through.
  """
  return json.dumps(prepare(data), **kwargs)
