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

from collections.abc import Iterator, KeysView
from typing import Any, cast, Generic, NoReturn, Optional, TypeVar, Union
from deface.error import ValidationError

__all__ = ['KeyT', 'T', 'Validator']

KeyT = Union[int, str]
T = TypeVar('T')

class Validator(Generic[T]):
  def __init__(
    self,
    value: T,
    filename: str = '',
    key: Optional[KeyT] = None,
    parent: Optional[Validator[T]] = None,
  ) -> None:
    """
    Create a new validator instance with the given key and value. When directly
    creating the root validator for a JSON document, provide the ``value`` and
    possibly ``filename`` as arguments. The latter improves error reporting.
    When indirectly creating a new child validator through an indexing operator,
    the ``parent`` and ``key`` can't be ``None``::

      parent._value[key] == value

    This equality holds for all derived validators but not for the root
    validator (whose parent is itself).
    """
    self._filename: str = parent._filename if parent is not None else filename
    self._key: KeyT = key if key is not None else ''
    self._value: T = value
    self._parent: Validator[T] = parent if parent is not None else self

  @property
  def filename(self) -> str:
    """Get the filename for the file with the JSON data."""
    return self._filename

  @property
  def only_key(self) -> str:
    """
    Get the only key. If the current value is a singleton object, this method
    returns the only key. Otherwise, it raises an assertion error.
    """
    value = self._value
    assert isinstance(value, dict)
    keys: KeysView[str] = value.keys()
    assert len(keys) == 1
    return next(iter(keys))

  @property
  def keypath(self) -> str:
    """
    Determine the key path for this validator value. The key path is composed
    from list items, formatted as say ``[42]``, and object fields, formatted
    like ``.answer`` for fields named with Python identifiers or like ``["42"]``
    otherwise.
    """
    def format(key: KeyT) -> str:
      if isinstance(key, str) and key.isidentifier():
        return f'.{key}'
      return f'[{json.dumps(key)}]'

    path: list[str] = []
    current = self
    while current != current._parent:
      path.append(format(current._key))
      current = current._parent
    path.reverse()
    return ''.join(path)

  @property
  def value(self) -> T:
    """Get the current value."""
    return self._value

  def raise_invalid(self, message: str) -> NoReturn:
    """
    Raise a validation error for the current value. The error message is
    automatically formatted as the character sequence consisting of filename,
    keypath, a space, and the given message string.

    :raises ValidationError: indicates a malformed JSON object.
    """
    keypath = self.keypath
    raise ValidationError(f'{self._filename}{keypath} {message}')

  def to_integer(self) -> Validator[int]:
    """
    Coerce the current value to an integer.

    :raises ValidationError: indicates that the current value is not an integer.
    """
    if not isinstance(self._value, int):
      self.raise_invalid('is not an integer')
    return cast(Validator[int], self)

  def to_float(self) -> Validator[float]:
    """
    Coerce the current value to an integral or floating point number.

    :raises ValidationError: indicates that the current value is neither an
      integer nor a floating point number.
    """
    if not isinstance(self._value, (int, float)):
      self.raise_invalid('is neither integer nor float')
    return cast(Validator[float], self)

  def to_string(self) -> Validator[str]:
    """
    Coerce the current value to a string.

    :raises ValidationError: indicates that the current value is not a string.
    """
    if not isinstance(self._value, str):
      self.raise_invalid('is not a string')
    return cast(Validator[str], self)

  def to_list(self) -> Validator[list[Any]]:
    """
    Coerce the current value to a list.

    :raises ValidationError: indicates that the current value is not a list.
    """
    if not isinstance(self._value, list):
      self.raise_invalid('is not a list')
    return cast(Validator[list[Any]], self)

  def items(self) -> Iterator[Validator[T]]:
    """
    Get an iterator over the current list value's items. Each item is wrapped in
    the appropriate validator to continue validating the JSON data. If the
    current value is not a list, this method raises an assertion error.
    """
    value: Any = self._value
    assert isinstance(value, list)
    for index, item in enumerate(cast(list[Any], value)):
      yield Validator(item, key=index, parent=self)

  def to_object(
    self,
    valid_keys: Optional[set[str]] = None,
    singleton: bool = False
  ) -> Validator[dict[str,Any]]:
    """
    Coerce the current value to an object. If ``valid_keys`` are given, this
    method validates the object's fields against the given field names. If
    ``singleton`` is ``True``, the object must have exactly one field.

    :raises ValidationError: indicates that the current value is not an object,
      not an object with a single key, or has a field with unknown name.
    """
    if not isinstance(self._value, dict):
      self.raise_invalid('is not an object')
    keys = cast(dict[str,Any], self._value).keys()
    if singleton and len(keys) != 1:
      self.raise_invalid('is not an object with a single field')
    if valid_keys is not None:
      for key in keys:
        if key not in valid_keys:
          self.raise_invalid(f'contains unexpected field {key}')
    return cast(Validator[dict[str,Any]], self)

  def __getitem__(self, key: KeyT) -> Validator[Any]:
    """
    Index the current value with the given key to create a new child validator.
    The given key becomes the new validator's key and the result of the indexing
    operation becomes the new validator's value. This validator becomes the new
    validator's parent.

    :raises TypeError: indicates that the current value is neither list nor
      object, that the key is not an integer even though the current value is a
      list, or that the key is not a string even though the current value is an
      object.

    :raises IndexError: indicates that the integer key is out of bounds for the
      current list value.

    :raises ValidationError: indicates that the required field named by the
      given key for the current object value is missing.
    """
    value = self._value
    if isinstance(value, list):
      list_value = cast(list[Any], value)
      if not isinstance(key, int):
        raise TypeError(f'Non-integer key "{key}" cannot index list')
      elif key < 0:
        raise IndexError(f'List index {key} is negative')
      elif key >= len(list_value):
        raise IndexError(f'List index {key} >= length {len(list_value)}')
      else:
        return Validator[Any](list_value[key], key=key, parent=self)
    elif isinstance(value, dict):
      if not isinstance(key, str):
        raise TypeError(f'Non-string key "{key}" cannot index dict')
      elif key not in value:
        self.raise_invalid(f'is missing required field {key}')
      else:
        return Validator[Any](value[key], key=key, parent=self)
    else:
      raise TypeError(f'Scalar value "{value}" cannot be indexed')
