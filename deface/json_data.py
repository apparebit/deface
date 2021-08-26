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

from __future__ import annotations

import json
import re

from binascii import unhexlify
from contextlib import AbstractContextManager
from typing import NoReturn, Optional, overload, Tuple, TypeVar, Union

from deface.error import ValidationError

JsonDataType = Union[
  type(None),
  bool,
  int,
  float,
  str,
  list['JsonDataType'],
  dict[str, 'JsonDataType']
]

_T = TypeVar('T') # type: ignore
_U = TypeVar('U') # type: ignore

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

def read_json(path: str) -> JsonDataType:
  """
  Read the file with the given path as a JSON file with personal data exported
  from Facebook. This function undoes Facebook's faulty encoding and then parses
  the JSON.
  """
  with open(path, 'rb') as file:
    return json.loads(restore_utf8(file.read()))

class JsonData(AbstractContextManager):
  """
  A wrapper class for parsed JSON data that helps with traversing, validating,
  and converting the data.

  Use Python's ``[]`` index operator to select an item from a list or a field
  from an object and Python's ``with`` statement to make that indexing operation
  stick::

    data = JsonData(json.loads('{ "key": "value" }'))

    with data['key']:
      print(data.value)                     # displays: value

  Use the various ``to_type()`` methods to coerce the current value to a
  specific type. The ``to_object()`` and ``to_single_field()`` methods
  optionally take a list of valid field names::

    data = JsonData(json.loads('{ "answer": 42 }'))

    data.to_object(['answer'])              # passes

    with data['answer']:
      print(data.to_integer())              # displays: 42

    print(data['answer'].to_integer())      # also displays: 42

    data['answer'].to_string()              # raises ValidationError
  """

  def __init__(self, value: JsonDataType, filename: str = ''):
    """
    Create a new wrapper for the given ``value``. The optional ``filename``
    helps generate more informative error messages.
    """
    self._filename: str = filename
    self._keys: list[Union[int, str]] = []
    self._values: list[JsonDataType] = [value]
    self._pending: Optional[Union[int, str]] = None

  @property
  def keypath(self) -> str:
    """
    Return the keypath for the current value. It starts with the filename given
    to the constructor and is followed by zero or more index expressions. List
    indices are formatted as, for example, ``[42]``. Field indices are formatted
    as, say, ``.answer`` for Python identifiers or as ``["42"]`` for all other
    field names.
    """
    def format(key: Union[int, str]) -> str:
      if isinstance(key, str) and key.isidentifier():
        return f'.{key}'
      return f'[{json.dumps(key)}]'
    keys: list[str] = [format(key) for key in self._keys]
    if self._pending is not None:
      keys.append(format(self._pending))
      self._pending = None
    return ''.join(keys)

  @property
  def value(self) -> JsonDataType:
    """
    Return the current value.
    """
    value = self._values[-1]
    if self._pending is not None:
      value = value[self._pending]
      self._pending = None
    return value

  def signal(self, message: str) -> NoReturn:
    """
    Signal that the current value is malformed. The error message is
    automatically appended to the filename and current keypath.
    """
    keypath = self.keypath  # Clears _pending.
    raise ValidationError(f'{self._filename}{keypath} {message}')

  def __getitem__(self, key: Union[int, str]) -> JsonData:
    """
    Make the indexed list item or object field the current value.

    This method indexes a list item by its positive position and a field by its
    name. The indexed value then serves as current value only for the next
    method invocation of this wrapper instance. To make an indexing operation
    "stick", ``__enter__()`` should be invoked next, albeit not directly from
    code but rather implicitly through a ``with`` statement.

    If the current value is neither list nor object, is a list and the key is
    not an integer, or is an object and the key is not a string, this method
    raises a ``TypeError``. If the integer key for a list value is not a valid
    item position, this method raises an ``IndexError``. Similarly, if the
    string key for an object value names a non-existent field, this method
    raises a ``KeyError``. As the exception types already indicate, these
    conditions are considered bugs in the validation logic. ``to_list_range()``
    validates the current value as a list. ``to_object()`` and
    ``to_singleton_object()`` validate the current value as an object; their
    optional ``keys`` arguments specify valid field names.
    """
    # Remove pending key so that any error raised below uses correct keypath.
    # This is safe to do because we intend to overwrite pending key.
    self._pending = None

    value = self._values[-1]
    if isinstance(value, dict):
      if not isinstance(key, str):
        raise TypeError(f'Non-string key "{key}" cannot index dict')
      elif key not in value:
        raise KeyError(f'Value "{value}" does not have field "{key}"')
    elif isinstance(value, list):
      if not isinstance(key, int):
        raise TypeError(f'Non-integer key "{key}" cannot index list')
      elif key < 0:
        raise IndexError(f'List index {key} is negative')
      elif key >= len(value):
        raise IndexError(f'List index {key} >= length {len(value)}')
    else:
      raise TypeError(f'Value "{value}" cannot be indexed')

    self._pending = key
    return self

  def __enter__(self) -> JsonDataType:
    """
    Make an immediately preceding indexing operation stick.
    """
    key = self._pending
    if key is None:
      raise KeyError('No key to enter')
    self._pending = None

    value = self._values[-1][key]

    self._keys.append(key)
    self._values.append(value)
    return value

  def __exit__(self, *exc) -> bool:
    """
    Undo the most recent invocation to ``__enter__()``, restoring the parent
    value of the immediately preceding indexing operation.
    """
    self._pending = None
    self._keys.pop()
    self._values.pop()
    return False

  @overload
  def _to_type(self, typ: Tuple[_T, _U], description: str = '') -> Union[_T, _U]:
    ...

  def _to_type(self, typ: type[_T], description: str) -> _T:
    """
    Perform the actual type coercion without clearing the last indexing
    operation if the coercion is successful.
    """
    key = self._pending
    value = self._values[-1]
    if key is not None:
      value = value[key]

    if not isinstance(value, typ):
      self.signal(description)

    return value

  @overload
  def to_type(self, typ: Tuple[_T, _U], description: str = '') -> Union[_T, _U]:
    ...

  def to_type(self, typ: _T, description: str = 'is invalid') -> _T:
    """
    Coerce the current value to the given type and return it. If the current
    value is not of the expected type, this method raises a ``ValidationError``
    with the given ``description`` for message. The ``typ`` argument may be a
    tuple of types.
    """
    value = self._to_type(typ, description)
    self._pending = None
    return value

  def to_integer(self) -> int:
    """
    Coerce the current value to an integer and return it.
    """
    return self.to_type(int, 'is not an integer')

  def to_float(self) -> float:
    """
    Coerce the current value to a floating point number and return it. This
    method accepts and converts integers.
    """
    value = self.to_type((int, float), 'is not a floating point number')
    return float(value)

  def to_string(self) -> str:
    """
    Coerce the current value to a string and return it.
    """
    return self.to_type(str, 'is not a string')

  def to_list_range(self) -> range:
    """
    Coerce the current value to a list and return the range of its indices. This
    may, at first, seem like an odd interface for validating lists. However, it
    is directly enables the preferred idiom for validating list elements, too::

      for index in data.to_list_range():
        with data[index]:
          ...
    """
    value = self.to_type(list, 'is not a list')
    return range(len(value))

  def to_object(
    self, keys: Optional[list[str]] = None
  ) -> dict[str, JsonDataType]:
    """
    Coerce the current value to an object (or dict) and return it. If ``keys``
    are present, this method validates each field name against the keys.
    """
    value = self._to_type(dict, 'is not an object')  # Don't clear _pending yet.
    if keys is not None:
      for key in value:
        if key not in keys:
          self.signal(f'contains unknown field "{key}"')
    self._pending = None
    return value

  def to_singleton_object(self, keys: Optional[list[str]] = None) -> str:
    """
    Coerce the current value to an object with a single field and return the
    name of that field. If ``keys`` are present, this method validates the field
    name against the keys.
    """
    value = self._to_type(dict, 'is not an object')  # Don't clear _pending yet.

    count = len(value)
    if count == 0:
      self.signal('is object with no fields')
    elif count > 1:
      self.signal('is object with more than one field')

    key = next(iter(value))
    if keys is not None and key not in keys:
      self.signal(f'is object with unknown only field "{key}"')

    self._pending = None
    return key
