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
import io
import json
import sys

from types import MethodType
from typing import Union

def _default(value):
  if isinstance(value, enum.Enum):
    return value.name
  elif dataclasses.is_dataclass(value):
    return dataclasses.asdict(value)
  else:
    return value

class Logger:
  def __init__(self, stream: io.TextIOBase = sys.stderr):
    self._line_count: int = 0
    self._error_count: int = 0
    self._stream: io.TextIOBase = stream
    if stream.isatty():
      self._sgr = MethodType(lambda self, code: f'\x1b[{code}m', self)

  def _print(self, text: str = '') -> None:
    self._line_count += text.count('\n') + 1
    self._stream.write(text + '\n')

  def _sgr(self, _: str) -> str:
    return ''

  def _print_bold(self, text: str) -> str:
    self._print(self._sgr('1') + text + self._sgr('22'))

  def _print_in_green(self, text: str) -> str:
    self._print(self._sgr('32;4;1') + text + self._sgr('39;22'))
    self._print(self._sgr('42') + (' ' * len(text)) + self._sgr('49'))

  def _print_in_red(self, text: str) -> str:
    self._print(self._sgr('31;1') + text + self._sgr('39;22'))
    self._print(self._sgr('41') + (' ' * len(text)) + self._sgr('49'))

  def _print_object(self, value):
    self._print(json.dumps(value, default=_default, indent=2))

  @property
  def error_count(self):
    return self._error_count

  def error(self, err: Union[str, Exception]):
    self._error_count += 1
    starting_line = self._line_count

    args = err.args if isinstance(err, Exception) else [err]
    for index, arg in enumerate(args):
      if isinstance(arg, str):
        if index == 0:
          self._print_bold(arg)
        else:
          self._print(arg)
      else:
        self._print_object(arg)

    if self._line_count - starting_line > 5:
      self._print()

  def done(self, message: str) -> None:
    if self.error_count > 0:
      self._print_in_red(message)
    else:
      self._print_in_green(message)
