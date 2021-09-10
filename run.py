#!/usr/bin/env python3

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

import argparse
import functools
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Callable, Union

# This is not a module!
__all__ = []

# ------------------------------------------------------------------------------
# Utilities: Logging

is_tracing = False
sgr = lambda c: f'\x1b[{c}m'
log_prefix = f'{sys.argv[0]} >> '

def trace(message: str, *args: Any, **kwargs: Any) -> None:
  """Write the formatted message to standard error in verbose mode."""
  if is_tracing:
    sys.stderr.write(
      sgr('1')
      + log_prefix + message.format(*args, **kwargs)
      + sgr('0')
      + '\n'
    )

def announce(message: str) -> None:
  """Write the message to standard error."""
  sys.stderr.write(
    sgr('1;97;45')
    + log_prefix + message
    + sgr('0;39;49')
    + '\n'
  )

# ------------------------------------------------------------------------------
# Utilities: Program Execution

def exec(
  command: Union[str, list[str]], **kwargs: Any
) -> subprocess.CompletedProcess:
  """Run the given command in a subprocess."""
  if isinstance(command, list):
    command = [str(c) for c in command]
    trace(' '.join(command))
  else:
    command = str(command)
    trace(command)
  return subprocess.run(command, check=True, **kwargs)

# ------------------------------------------------------------------------------
# Utilities: File and Directory Manipulation

class Env:
  """The environment."""
  def __init__(self):
    self.cwd = Path(__file__).resolve().parent
    self.dist = self.cwd / 'dist'
    self.docs = self.cwd / 'docs'
    self.docs_build = self.docs / '_build'
    self.docs_html = self.docs_build / 'html'
    self.html_index = self.docs_html / 'index.html'
env = Env()

def make_directory(*pathsegments):
  """Ensure that the given directory exists."""
  path = Path(*pathsegments)
  trace('make_directory {}', path)
  os.makedirs(path, exist_ok=True)

def copy(source, destination):
  """Copy files from source path too destination path."""
  trace('copy {} {}', source, destination)
  shutil.copytree(
    source, destination,
    ignore=shutil.ignore_patterns('.DS_Store', '__pycache__')
  )

def delete_directory(*pathsegments):
  """Delete the given directory."""
  path = Path(*pathsegments)
  trace('delete_directory {}', path)
  shutil.rmtree(path, ignore_errors=True)

def delete_contents(*pathsegments):
  """Delete all entries from the given directory."""
  path = Path(*pathsegments)
  trace('delete_contents {}', path)
  for item in path:
    if item.is_dir():
      shutil.rmtree(item, ignore_errors=True)
    else:
      item.unlink(missing_ok=True)

def open_file(*pathsegments):
  """Open a file in a suitable application."""
  path = Path(*pathsegments)
  trace('open_file {}', path)
  # FIXME: This works on macOS only.
  subprocess.run(['open', path], check=True)

# ------------------------------------------------------------------------------
# @command

commands = {}
def command(fn: Callable[[], None]) -> Callable[[], None]:
  """Turn a function into a command."""
  name = fn.__name__

  @functools.wraps(fn)
  def wrapper():
    announce(name)
    fn()

  commands[name] = wrapper
  return fn

# ------------------------------------------------------------------------------
# The Commands

@command
def clean():
  """delete build artifacts"""
  delete_directory(env.dist)
  delete_directory(env.docs_build)
  make_directory(env.docs_build)

@command
def mypy():
  """check types"""
  exec('mypy')

@command
def pytest():
  """run unit tests"""
  exec('pytest')

@command
def docs():
  """build documentation"""
  exec(['sphinx-build', '-M', 'html', env.docs, env.docs_build])
  open_file(env.html_index)

@command
def github_pages():
  """update GitHub pages"""
  with tempfile.TemporaryDirectory(prefix='run-github-pages') as temp:
    copy(env.docs_html, temp)
    exec(['git', 'checkout', 'gh-pages'])
    delete_contents(env.cwd)
    copy(temp, env.cwd)
  exec(['git', 'add', '.'])
  exec(['git', 'commit', '-m', 'Update gh-pages'])
  #exec(['git', 'push'])
  exec(['git', 'checkout', 'master'])

@command
def build():
  """check code and build documentation"""
  mypy()
  pytest()
  docs()

@command
def release():
  """release a new version"""
  exec(['flit', 'build', '--no-setup-py'])
  exec(['flit', 'publish'])

# ------------------------------------------------------------------------------
# The Argument Parser

name_width = len('--color, --no-color  ')
description = 'supported commands:\n  ' + '\n  '.join([
  f'{name.ljust(name_width)}{command.__doc__}'
  for name, command in commands.items()
])
parser = argparse.ArgumentParser(
  description=description,
  formatter_class=argparse.RawDescriptionHelpFormatter
)
parser.add_argument(
  'commands',
  metavar='COMMAND', nargs='+', choices=commands.keys(),
  help='execute the command'
)
parser.add_argument(
  '--color',
  action=argparse.BooleanOptionalAction, default=sys.stderr.isatty(),
  help='enable / disable use of color in output'
)
parser.add_argument(
  '-v', '--verbose',
  action='store_true', default=False,
  help="enable verbose mode"
)

# ------------------------------------------------------------------------------
# Run the given commands.

args = parser.parse_args()
if not args.color:
  sgr = lambda c: ''
if args.verbose:
  is_tracing = True
for command in args.commands:
  commands[command]()
