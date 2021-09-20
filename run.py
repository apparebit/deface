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
from inspect import signature
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Callable, Optional, Union

# --------------------------------------------------------------------------------------
# Utilities: Logging

run_dot_py = p[2:] if (p := sys.argv[0]).startswith('./') else p
is_tracing: bool = False

sgr: Callable[[str], str] = lambda c: f'\x1b[{c}m'

def println(on: str, message: str, off: str) -> None:
  """Print the ANSI escape code ``on``, message, and escape code ``off``."""
  sys.stderr.write(f'{sgr(on)}{run_dot_py} >> {message}{sgr(off)}\n')

def trace(message: str, *args: Any, **kwargs: Any) -> None:
  """If in verbose mode, write the formatted message to standard error."""
  if is_tracing:
    println('1', message.format(*args, **kwargs), '0')

def announce(message: str) -> None:
  """Write the highlighted announcement message to standard error."""
  println('1;45;38;5;231', message, '0;49;39')

def warning(message: str) -> None:
  """Write the warning message to standard error."""
  println('1;103', message, '0;49')

def error(message: str) -> None:
  """Write the error message to standard error."""
  println('1;31', message, '0;39')

# --------------------------------------------------------------------------------------
# Utilities: File and Directory Manipulation

class temporary_directory(tempfile.TemporaryDirectory):
  """Create temporary directory, return context manager that binds to path."""
  def __enter__(self) -> Path:
    return Path(super().__enter__())

def make_directory(path: Path) -> None:
  """Ensure that the given directory exists."""
  trace('make directory {}', path)
  os.makedirs(path, exist_ok=True)

def copy(source: Path, destination: Path) -> None:
  """Copy files from source path too destination path."""
  trace('copy {} {}', source, destination)
  shutil.copytree(
    source, destination,
    ignore=shutil.ignore_patterns('.DS_Store', '__pycache__'),
    dirs_exist_ok=True,
  )

def delete_directory(path: Path) -> None:
  """Delete the given directory."""
  trace('delete directory {}', path)
  shutil.rmtree(path, ignore_errors=True)

def delete_contents(path: Path, excludes: set[str]) -> None:
  """Delete all entries from the given directory."""
  trace('delete directory contents {}', path)
  trace('excluding {}', excludes)
  for entry in path.iterdir():
    if entry.name in excludes or str(entry) in excludes:
      continue
    if entry.is_symlink() or entry.is_file():
      entry.unlink(missing_ok=True)
    elif entry.is_dir():
      shutil.rmtree(entry, ignore_errors=True)

def open_file(path: Path) -> None:
  """Open the file in a suitable application."""
  trace('open file {}', path)
  if sys.platform.startswith('darwin'):
    subprocess.run(['open', path], check=True)
  elif sys.platform.startswith('win32'):
    os.startfile(path) # Only available on Windows
  else:
    raise NotImplementedError(f'open_file() does not support {sys.platform}')

# --------------------------------------------------------------------------------------
# Utilities: Program Execution

exec_env: dict[str, str] = {
  'PATH': os.environ['PATH'],
  'TERM': os.environ['TERM'],
  'VIRTUAL_ENV': sys.prefix,
}

def exec(
  *command: Union[str, Path], **kwargs: Any
) -> subprocess.CompletedProcess:
  """Run the given command in a subprocess."""
  # Stringify command, as trace(), subprocess.run() don't accept path objects.
  cmd = [str(c) for c in command]
  trace(' '.join(cmd))

  # Merge environment variables, then spawn subprocess with command.
  kwargs['env'] = exec_env | kwargs.get('env', {})
  return subprocess.run(cmd, check=True, **kwargs)

# --------------------------------------------------------------------------------------
# Utilities: File System Paths

class FS:
  """Useful file system paths."""
  def __init__(self) -> None:
    self.cwd = Path(__file__).resolve().parent
    self.dist = self.cwd / 'dist'
    self.docs = self.cwd / 'docs'
    self.venv = Path(sys.prefix)
fs = FS()

# --------------------------------------------------------------------------------------
# Virtual Environment

VENV_BIN = 'Scripts' if sys.platform == 'win32' else 'bin'
VENV_CONFIG = 'pyvenv.cfg'
VENV_DIR = '.venv'
VENV_SEP = re.compile(r'\s*=\s*')

PY_PROJECT = 'pyproject.toml'
PY_PROJECT_GROUPS = {'dev', 'doc', 'test'}

def is_venv_running() -> bool:
  """Test whether Python is running within a PEP 405 virtual environment."""
  return sys.prefix != getattr(sys, 'base_prefix', sys.prefix)

def load_venv_config(path: Path) -> dict[str, str]:
  """Parse a virtual environment's configuration."""
  with open(path, encoding='utf8') as file:
    lines = file.read().splitlines()
  pairs = [VENV_SEP.split(l) for l in lines if l.strip()]
  return { k.strip(): v.strip() for [k, v] in pairs}

def validate_as_venv(path: Path) -> Optional[dict[str, str]]:
  """Validate given path as virtual environment, returning its configuration."""
  if path.exists() and (cfg_path := path / VENV_CONFIG).exists():
    try:
      cfg = load_venv_config(cfg_path)
      if 'home' in cfg:
        return cfg
    except Exception as x:
      error(f'error loading {cfg_path}: {x.args[0]}')
  return None

def activate_venv(venv: Path) -> None:
  """Activate the virtual environment."""
  fs.venv = venv
  exec_env['PATH'] = str(venv / VENV_BIN) + os.pathsep + os.environ['PATH']
  exec_env['VIRTUAL_ENV'] = str(venv)

def install_venv(venv: Path) -> None:
  """Create a new virtual environment."""
  exec('python3', '-m', 'venv', venv)

def lookup_dependencies(pyproject: Path) -> list[str]:
  """Extract project's optional dependencies."""
  cfg_text = pyproject.read_text('utf8')
  # Recent versions of pip include tomli, older versions include toml.
  from importlib import import_module
  try:
    cfg = import_module('pip._vendor.tomli').loads(cfg_text) # type: ignore
  except ModuleNotFoundError:
    cfg = import_module('pip._vendor.toml').loads(cfg_text) # type: ignore
  groups = cfg.get('project', {}).get('optional-dependencies', {})
  return [deps for g in groups if g in PY_PROJECT_GROUPS for deps in groups[g]]

def python(*arguments: Union[str, Path]) -> None:
  """invoke python on the arguments"""
  exec('python3', *arguments)

def pip(*arguments: Union[str, Path]) -> None:
  """invoke pip on the arguments"""
  exec('python3', '-m', 'pip', *arguments)

def bootstrap(project_root: Path = fs.cwd) -> None:
  """install virtual environment and development dependencies"""
  venv = project_root / VENV_DIR
  announce(f'ensure virtual environment exists: {venv}')
  install_venv(venv)
  activate_venv(venv)

  dependencies = lookup_dependencies(project_root / PY_PROJECT)
  announce('ensure packages are installed')
  trace(', '.join(dependencies[:7]))
  trace(', '.join(dependencies[7:]))
  pip('install', *dependencies)

def virtualize() -> None:
  """Ensure that subprocesses use virtual environment."""
  if is_venv_running():
    return
  venv = fs.cwd / VENV_DIR
  if not venv.exists():
    bootstrap(fs.cwd)
  elif validate_as_venv(venv):
    activate_venv(venv)
  else:
    error(f'please delete {venv} obstructing virtual environment')
    raise RuntimeError(f'virtual environment obstructed by {venv}')

# --------------------------------------------------------------------------------------
# @command

CommandT = Callable[..., None]

special_commands: set[str] = set()
commands: dict[str, Callable[..., None]] = {}

def make_command(
  fn: CommandT, *, name: Optional[str] = None, force_simple: bool = False
) -> CommandT:
  """Turn a function into a command."""
  cmd_name: str = fn.__name__ if name is None else name

  @functools.wraps(fn)
  def wrapper(*args: str) -> None:
    announce(cmd_name + ' ' + ', '.join(args) if args else cmd_name)
    fn(*args)

  if (not force_simple) and len(signature(fn).parameters) > 0:
    special_commands.add(cmd_name)
  commands[cmd_name] = wrapper
  return fn

command = make_command
command(bootstrap, force_simple=True)
command(python)
command(pip)

# --------------------------------------------------------------------------------------
# The Commands

@command
def clean() -> None:
  """delete build artifacts"""
  delete_directory(fs.dist)
  delete_directory(fs.docs / '_build')
  make_directory(fs.docs / '_build')

@command
def check() -> None:
  """run static code inspections"""
  exec('mypy', '--color-output')

@command
def test() -> None:
  """run tests while also determining coverage"""
  exec('pytest', '--cov=deface')

@command
def document() -> None:
  """build documentation"""
  exec('sphinx-build', '-M', 'html', fs.docs, fs.docs / '_build')
  open_file(fs.docs / '_build' / 'html' / 'index.html')

@command
def build() -> None:
  """build binary and source distributions"""
  exec('flit', 'build')

@command
def publish_docs() -> None:
  """update documentation on GitHub pages"""
  # Build documentation.
  clean()
  check()
  test()
  document()

  # Copy documentation aside.
  with temporary_directory(prefix='publish-docs') as tmpdir:
    copy(fs.docs / '_build' / 'html', tmpdir)
    exec('git', 'checkout', 'gh-pages')
    delete_contents(fs.cwd, excludes=set(['.git', '.gitignore', '.venv']))
    copy(tmpdir, fs.cwd)

  # Commit documentation to gh-pages
  exec('git', 'add', '.')
  exec('git', 'commit', '-m', 'Update gh-pages')
  exec('git', 'push')
  exec('git', 'checkout', 'boss')

@command
def release() -> None:
  """release a new version"""
  clean()
  check()
  test()
  document()
  exec('flit', 'publish')

# --------------------------------------------------------------------------------------
# Command Line Arguments

def create_parser(*, with_commands: bool = True) -> argparse.ArgumentParser:
  # Prepare command descriptions
  width = len('--color, --no-color  ')

  lines: list[str] = ['special commands (one per invocation):\n']
  for name, command in commands.items():
    if name in special_commands:
      lines.append('  ' + f'{name} ARG ...'.ljust(width) + f'{command.__doc__}\n')
  lines.append('\nsimple commands (one or more per invocation):\n')
  for name, command in commands.items():
    if not name in special_commands:
      lines.append('  ' + f'{name}'.ljust(width) + f'{command.__doc__}\n')
  lines.extend([
    f"\n{run_dot_py} automatically creates a new virtual environment if one doesn't\n",
    "exist. It runs all Python code in that virtual environment.\n"
  ])

  # Instantiate parser
  parser = argparse.ArgumentParser(
    prog=run_dot_py, epilog=''.join(lines), allow_abbrev=False,
    formatter_class=argparse.RawDescriptionHelpFormatter,
  )
  parser.add_argument(
    '--color',
    action=argparse.BooleanOptionalAction, default=None,
    help='enable / disable use of color in output'
  )
  parser.add_argument(
    '-v', '--verbose',
    action='store_true', default=False,
    help="enable verbose mode"
  )
  if with_commands:
    parser.add_argument(
      'commands', metavar='COMMAND', nargs='+', choices=commands.keys(),
      help='execute comand as described above'
    )
  return parser

def parse_arguments() -> argparse.Namespace:
  result = argparse.Namespace(commands=[], extras=None)
  arguments = sys.argv[1:]

  # Handle special commands, which consume rest of arguments
  for index, argument in enumerate(arguments):
    if argument in special_commands:
      result.commands.append(argument)
      result.extras = arguments[index + 1:]
      arguments = arguments[:index]
      break
    elif not argument.startswith('-'):
      break

  # Parse arguments
  parser = create_parser(with_commands=result.extras is None)
  parser.parse_args(args=arguments, namespace=result)
  result.extras = [] if result.extras is None else result.extras
  return result

# --------------------------------------------------------------------------------------
# The main function

def main() -> None:
  """Parse command line arguments as commands and then run the requested commands."""
  global sgr
  global is_tracing

  # Parse arguments.
  args = parse_arguments()
  if args.color is None:
    args.color = sys.stderr.isatty()
  if not args.color:
    args.color = lambda _: ''
  if args.verbose:
    is_tracing = True

  # Ensure we are running inside virtual environment.
  virtualize()
  trace('current Python prefix {}', sys.prefix)
  trace('subprocess prefix {}', fs.venv)

  # Execute the requested commands. The first exception terminates all commands.
  try:
    for command_name in args.commands:
      commands[command_name](*args.extras)
  except subprocess.CalledProcessError:
    pass
  except Exception as x:
    import traceback
    error(f'{command_name} failed: {x.args[0]}')
    if is_tracing:
      trace('error traceback:')
      traceback.print_tb(x.__traceback__, file=sys.stderr)

if __name__ == '__main__':
  main()
