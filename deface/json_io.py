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

JsonT = Union[None, bool, int, float, str, list[Any], dict[str, Any]]

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

def loads(data: bytes, **kwargs: Any) -> JsonT:
  """
  Return the result of deserializing a value from the given JSON text. This
  function simply wraps an invocation of the eponymous function in Python's
  ``json`` package — after applying :py:func:`restore_utf8` to the given
  ``data``. It passes the keyword arguments through.
  """
  return json.loads(restore_utf8(data), **kwargs)

def default(value: Any) -> Union[str, dict[str, Any]]:
  """
  Convert the given value, which cannot be encoded as JSON, to an equivalent
  value that can be encoded as JSON. For enum constants, this function returns
  their names. For dataclasses, it returns a dictionary with their non-``None``
  attributes. Similarly for objects with a ``__dict__`` attribute, it returns a
  dictionary with their non-``None`` attributes.

  :raises TypeError: indicates that the value does not match any of the above
    cases.
  """
  if isinstance(value, enum.Enum):
    return value.name

  dct: dict[str, Any]
  if dataclasses.is_dataclass(value):
    dct = dataclasses.asdict(value)
  elif hasattr(value, '__dict__'):
    dct = value.__dict__
  else:
    raise TypeError(f'Value "{value}" cannot be encoded as JSON')
  return { k: v for k, v in dct.items() if v is not None }

def dumps(value: Any, **kwargs: Any) -> str:
  """
  Return the result of serializing the given value as JSON text. This function
  simply wraps an invocation of the eponymous function in Python's ``json``
  package. It uses :py:func:`default` as the ``default`` argument while passing
  any other keyword arguments through.
  """
  return json.dumps(value, default=default, **kwargs)
