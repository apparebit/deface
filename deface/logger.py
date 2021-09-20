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

import enum
import sys

from deface import serde
from types import MethodType
from typing import Any, TextIO, Union

__all__ = ['pluralize', 'Level', 'Logger']

def pluralize(count: int, noun: str, suffix: str = 's') -> str:
  return noun + suffix if count != 1 else noun

def _sgr(_: str, code: str) -> str:
  return f'\x1b[{code}m'

class Level(enum.Enum):
  ERROR = '🛑 '
  WARN = '⚠️ '
  INFO = 'ℹ️ '

class Logger:
  """
  A simple console logger. By default, the logger prefixes messages with the
  given ``prefix`` followed by appropriate emoji. If the underlying ``stream``
  is a TTY, it also uses ANSI escape codes to style messages. The use of color
  or emoji can be disabled by setting the corresponding argument to false.
  """
  def __init__(
    self,
    stream: TextIO = sys.stderr,
    prefix: str = '',
    use_color: bool = True,
    use_emoji: bool = True,
  ) -> None:
    self._line_count: int = 0
    self._error_count: int = 0
    self._warn_count: int = 0
    self._stream: TextIO = stream
    if stream.isatty() and use_color:
      self._sgr = MethodType(_sgr, self) # type: ignore
    self._prefix: str = prefix
    self._use_emoji: bool = use_emoji

  def print(self, text: str = '') -> None:
    """Log the given text followed by a newline."""
    self._line_count += text.count('\n') + 1
    text = self._prefix + text.replace('\n', '\n' + self._prefix) + '\n'
    self._stream.write(text)

  def print_json(self, value: Any, **kwargs: Any) -> None:
    """Log a nicely indented JSON representation of the given value"""
    self.print(serde.dumps(value, indent=2, **kwargs))

  def _sgr(self, _: str) -> str:
    return ''

  def print_bold(self, text: str) -> None:
    """Log the text in bold followed by a newline."""
    self.print(self._sgr('1') + text + self._sgr('22'))

  def print_in_green(self, text: str) -> None:
    """Log the text in green followed by a newline."""
    self.print(self._sgr('32;4;1') + text + self._sgr('39;22'))

  def print_in_red(self, text: str) -> None:
    """Log the text in red followed by a newline."""
    self.print(self._sgr('31;1') + text + self._sgr('39;22'))

  def _print_entry(
    self, level: Level, err: Union[str, Exception], *extras: Any
  ) -> None:
    starting_line = self._line_count

    args = (err.args if isinstance(err, Exception) else (err,)) + extras
    for index, arg in enumerate(args):
      if isinstance(arg, str):
        if index == 0:
          if self._use_emoji:
            arg = level.value + arg
          self.print_bold(arg)
        else:
          self.print(arg)
      else:
        self.print_json(arg)

    if self._line_count - starting_line > 5:
      self.print()

  @property
  def error_count(self) -> int:
    """The number of errors reported with :py:meth:`error` so far."""
    return self._error_count

  def error(self, err: Union[str, Exception], *extras: Any) -> None:
    """
    Log the given error message followed by the JSON representation of any
    additional exception arguments as well as additional method arguments.
    """
    self._error_count += 1
    self._print_entry(Level.ERROR, err, *extras)

  def warn(self, warning: Union[str, Warning], *extras: Any) -> None:
    """
    Print a warning message.
    """
    self._warn_count += 1
    self._print_entry(Level.WARN, warning, *extras)

  def info(self, message: str, *extras: Any) -> None:
    """Print an informational message."""
    self._print_entry(Level.INFO, message, *extras)

  def done(self, message: str) -> None:
    """
    Print a summarizing message at completion of a tool run. If the output
    stream is a TTY, the message is highlighted in red or green, depending on
    whether any errors have been reported.
    """
    if self.error_count > 0:
      self.print_in_red(message)
    else:
      self.print_in_green(message)
