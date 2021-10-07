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
from subprocess import CompletedProcess, run as subprocess_run
import sys
import tempfile
from typing import Any, Callable, Optional, TextIO, Union

# --------------------------------------------------------------------------------------
# The Global Context for Namespacing All Utilities

class Context:
  """The context for global state and utility functions"""
  def __init__(self, *, logger: 'Logger', fs: 'FS', venv: 'VEnv') -> None:
    self.logger = logger
    self.fs = fs
    self.venv = venv
    self._exec_env: dict[str, str] = {
      'PATH': os.environ['PATH'],
      'TERM': os.environ['TERM'],
      'VIRTUAL_ENV': sys.prefix,
    }

  def activate_venv(self, path: Path) -> None:
    """Update context to use path as virtual environment path."""
    self.fs.venv = path
    # Venv.BIN must be defined by time this method is invoked from VEnv instance.
    self._exec_env['PATH'] = str(path / VEnv.BIN) + os.pathsep + os.environ['PATH']
    self._exec_env['VIRTUAL_ENV'] = str(path)

  def exec(self, *command: Union[str, Path], **kwargs: Any) -> CompletedProcess:
    """Run the given command in a subprocess."""
    # Stringify command, as trace(), subprocess.run() don't accept path objects.
    cmd = [str(c) for c in command]
    context.logger.trace(' '.join(cmd))

    # Merge environment variables, then spawn subprocess with command.
    kwargs['env'] = self._exec_env | kwargs.get('env', {})
    if 'capture_output' in kwargs and 'encoding' not in kwargs:
      kwargs['encoding'] = 'utf8'
    return subprocess_run(cmd, check=True, **kwargs)

context: Context

# --------------------------------------------------------------------------------------
# Utilities: Logger

# Program name is needed in argument parser, whose results configure logger.
RUN_DOT_PY: str = sys.argv[0][2:] if sys.argv[0].startswith('./') else sys.argv[0]

class Logger:
  """A console logger. It may print in color and in detail, to stderr by default"""
  def __init__(
    self,
    *,
    in_color: Optional[bool] = None,
    is_verbose: bool = False,
    stream: TextIO = sys.stderr,
  ) -> None:
    self.is_verbose: bool = is_verbose
    self.stream: TextIO = stream

    if in_color is None:
      in_color = stream.isatty()
    self.sgr: Callable[[str], str] = self._do_sgr if in_color else self._do_not_sgr

  def _do_sgr(self, code: str) -> str:
    return f'\x1b[{code}m'

  def _do_not_sgr(self, _: str) -> str:
    return ''

  def _println(self, on: str, message: str, off: str) -> None:
    """Print the ANSI escape code ``on``, message, and escape code ``off``."""
    self.stream.write(f'{self.sgr(on)}{RUN_DOT_PY} >> {message}{self.sgr(off)}\n')

  def trace(self, message: str, *args: Any, **kwargs: Any) -> None:
    """If in verbose mode, write the formatted message to standard error."""
    if self.is_verbose:
      self._println('1', message.format(*args, **kwargs), '0')

  def announce(self, message: str) -> None:
    """Write the highlighted announcement message to standard error."""
    self._println('1;45;38;5;231', message, '0;49;39')

  def warning(self, message: str) -> None:
    """Write the warning message to standard error."""
    self._println('1;103', message, '0;49')

  def error(self, message: str) -> None:
    """Write the error message to standard error."""
    self._println('1;31', message, '0;39')

# --------------------------------------------------------------------------------------
# Utilities: File System

class TemporaryDirectory(tempfile.TemporaryDirectory):
  """Context manager for temporary directory named by *path object* (not string)."""
  def __enter__(self) -> Path:
    return Path(super().__enter__())

class FS:
  """File system utilities bundled in a namespace."""

  def __init__(self, root: Optional[Path] = None) -> None:
    self.root: Path = Path(__file__).resolve().parent if root is None else root
    self.dist: Path = self.root / 'dist'
    self.docs: Path = self.root / 'docs'
    self.venv: Path = Path(sys.prefix)

  def temporary_directory(self, *args: Any, **kwargs: Any) -> TemporaryDirectory:
    """Create temporary directory, return context manager that binds to path."""
    return TemporaryDirectory(*args, **kwargs)

  def make_directory(self, path: Path) -> None:
    """Ensure that the given directory exists."""
    context.logger.trace('make directory {}', path)
    os.makedirs(path, exist_ok=True)

  def copy(self, source: Path, destination: Path) -> None:
    """Copy files from source path too destination path."""
    context.logger.trace('copy {} {}', source, destination)
    shutil.copytree(
      source, destination,
      ignore=shutil.ignore_patterns('.DS_Store', '__pycache__'),
      dirs_exist_ok=True,
    )

  def delete_directory(self, path: Path) -> None:
    """Delete the given directory."""
    context.logger.trace('delete directory {}', path)
    shutil.rmtree(path, ignore_errors=True)

  def delete_contents(self, path: Path, excludes: set[str]) -> None:
    """Delete all entries from the given directory."""
    context.logger.trace('delete directory contents {}', path)
    context.logger.trace('excluding {}', excludes)
    for entry in path.iterdir():
      if entry.name in excludes or str(entry) in excludes:
        continue
      if entry.is_symlink() or entry.is_file():
        entry.unlink(missing_ok=True)
      elif entry.is_dir():
        shutil.rmtree(entry, ignore_errors=True)

  def open_in_app(self, path: Path) -> None:
    """Open the file in a suitable application."""
    context.logger.trace('open file {}', path)
    if sys.platform == 'darwin':
      context.exec('open', path)
    elif sys.platform == 'linux':
      if not shutil.which('xdg-open'):
        raise NotImplementedError('unable to locate xdg-open command')
      context.exec('xdg-open', path)
    elif sys.platform.startswith('win32'):
      os.startfile(path) # Only available on Windows
    else:
      raise NotImplementedError(f'open_in_app() does not support {sys.platform}')

# --------------------------------------------------------------------------------------
# Utilities: Virtual Environment

class _RUNTIME_DEPENDENCIES_TYPE:
  pass
RUNTIME = _RUNTIME_DEPENDENCIES_TYPE()

class VEnv:
  BIN = 'Scripts' if sys.platform == 'win32' else 'bin'
  CONFIG = 'pyvenv.cfg'
  DIR = '.venv'
  SEP = re.compile(r'=')
  PYPROJECT = 'pyproject.toml'

  def __init__(self, project: Path, prefix: Optional[Path] = None):
    self.project_root = project
    self.prefix = project / VEnv.DIR if prefix is None else prefix

  def is_running_in_venv(self) -> bool:
    """Test whether this Python is running within a PEP 405 virtual environment."""
    return sys.prefix != getattr(sys, 'base_prefix', sys.prefix)

  def load_config(self) -> dict[str, str]:
    """Parse a virtual environment's configuration."""
    with open(self.prefix / VEnv.CONFIG, encoding='utf8') as file:
      pairs = [l.split('=', maxsplit=1) for l in file if '=' in l]
    return { k.strip(): v.strip() for [k, v] in pairs}

  def validate_as_venv(self) -> Optional[dict[str, str]]:
    """Validate given path as virtual environment, returning its configuration."""
    try:
      cfg = self.load_config()
      if 'home' in cfg:
        return cfg
    except FileNotFoundError:
      pass
    except Exception as x:
      context.logger.error(f'error loading {self.prefix / VEnv.CONFIG}: {x.args[0]}')
    return None

  def check_active_venv(self) -> None:
    """Check that given path identifies active virtual environment."""
    sys_prefix = context.exec(
      'python3', '-c', 'import sys; print(sys.prefix)', capture_output=True
    ).stdout.strip()
    if sys_prefix != str(self.prefix):
      raise RuntimeError(
        f"Python claims '{sys_prefix}' as venv instead of '{self.prefix}'"
      )

  def lookup_dependencies(
    self, *group_names: Union[_RUNTIME_DEPENDENCIES_TYPE, str]
  ) -> list[str]:
    """Extract project's dependencies."""
    cfg_text = (self.project_root / VEnv.PYPROJECT).read_text('utf8')
    # Recent versions of pip include tomli, older versions include toml.
    from importlib import import_module
    try:
      cfg = import_module('pip._vendor.tomli').loads(cfg_text) # type: ignore
    except ModuleNotFoundError:
      cfg = import_module('pip._vendor.toml').loads(cfg_text) # type: ignore
    project = cfg.get('project', {})
    groups = project.get('optional-dependencies', {})
    groups[RUNTIME] = project.get('dependencies', [])
    return [d for g in group_names for d in groups.get(g, [])]

  def lookup_installed(self) -> dict[str, str]:
    """Determine all packages installed in the virtual environment."""
    import json
    pairs = json.loads(context.exec(
      'python3', '-m', 'pip', 'list', '--format', 'json', capture_output=True
    ).stdout)
    return { entry['name'].lower(): entry['version'] for entry in pairs }

  def check_installed(self, packages: list[str]) -> None:
    """Check that the dependencies are in fact installed"""
    installed = self.lookup_installed()
    missing = set(packages) - set(installed)
    if len(missing) > 0:
      s = ', '.join(missing)
      raise RuntimeError(
        (f"dependency {s} is" if len(missing) == 1 else f"dependencies {s} are")
        + f" not installed; please delete '{self.prefix}' and run 'bootstrap' again."
      )

  def bootstrap(self) -> None:
    """install virtual environment and development dependencies"""
    logger = context.logger
    logger.announce(f"install venv '{self.prefix}'")
    context.exec('python3', '-m', 'venv', self.prefix)
    context.activate_venv(self.prefix)
    self.check_active_venv()

    context.exec('python3', '-m', 'pip', 'install', '--upgrade', 'pip')

    dependencies = self.lookup_dependencies('dev', 'doc', 'test')
    logger.announce('ensure dev dependencies are installed')
    logger.trace(', '.join(dependencies))
    context.exec('python3', '-m', 'pip', 'install', *dependencies)
    self.check_installed(dependencies)

  def virtualize(self) -> None:
    """Ensure that subprocesses use virtual environment."""
    if self.is_running_in_venv():
      return
    if not self.prefix.exists():
      self.bootstrap()
    elif self.validate_as_venv():
      context.activate_venv(self.prefix)
      self.check_active_venv()
    else:
      raise RuntimeError(
        f"virtual environment obstructed by {self.prefix}; please delete"
      )

# --------------------------------------------------------------------------------------
# @command Decorator: Adds logging wrapper. Registers command.

CommandT = Callable[..., None]

special_commands: set[str] = set()
commands: dict[str, Callable[..., None]] = {}

def command(fn: CommandT) -> CommandT:
  """Turn a function into a command."""
  cmd_name: str = fn.__name__

  @functools.wraps(fn)
  def wrapper(*args: str) -> None:
    # Context's logger is not known when @command decorator runs. Only in wrapper.
    context.logger.announce(cmd_name + ' ' + ', '.join(args) if args else cmd_name)
    fn(*args)

  if len(signature(fn).parameters) > 0:
    special_commands.add(cmd_name)
  commands[cmd_name] = wrapper
  return fn

# --------------------------------------------------------------------------------------
# Actual Commands

@command
def bootstrap() -> None:
  """install virtual environment and development dependencies"""
  context.venv.bootstrap()

@command
def python(*args: Union[str, Path]) -> None:
  """invoke Python on arguments in virtual environment"""
  context.exec('python3', *args)

@command
def deface(*args: Union[str, Path]) -> None:
  """Run deface with the given arguments"""
  context.exec('python3', '-m', 'deface', *args)

@command
def clean() -> None:
  """delete build artifacts"""
  fs = context.fs
  fs.delete_directory(fs.dist)
  fs.delete_directory(fs.docs / '_build')
  fs.make_directory(fs.docs / '_build')

@command
def check() -> None:
  """run static code inspections"""
  context.exec('mypy', '--color-output')

@command
def test() -> None:
  """run tests while also determining coverage"""
  command = ['pytest', '--cov=deface']
  if context.logger.is_verbose:
    command.append('-vv')
  context.exec(*command)

@command
def document() -> None:
  """build documentation"""
  fs = context.fs
  context.exec('sphinx-build', '-M', 'html', fs.docs, fs.docs / '_build')
  fs.open_in_app(fs.docs / '_build' / 'html' / 'index.html')

@command
def build() -> None:
  """build binary and source distributions"""
  context.exec('flit', 'build')

@command
def publish_docs() -> None:
  """update documentation on GitHub pages"""
  # Build documentation.
  clean()
  check()
  test()
  document()

  # Copy documentation aside.
  fs = context.fs
  with fs.temporary_directory(prefix='publish-docs') as tmpdir:
    fs.copy(fs.docs / '_build' / 'html', tmpdir)
    context.exec('git', 'checkout', 'gh-pages')
    fs.delete_contents(fs.root, excludes=set(['.git', '.gitignore', '.venv']))
    fs.copy(tmpdir, context.fs.root)

  # Commit documentation to gh-pages
  context.exec('git', 'add', '.')
  context.exec('git', 'commit', '-m', 'Update gh-pages')
  context.exec('git', 'push')
  context.exec('git', 'checkout', 'boss')

@command
def release() -> None:
  """release a new version"""
  clean()
  check()
  test()
  document()
  context.exec('flit', 'publish')

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
    f"\n{RUN_DOT_PY} automatically creates a new virtual environment if one ",
    "doesn't\nexist. It runs all Python code in that virtual environment.\n"
  ])

  # Instantiate parser
  parser = argparse.ArgumentParser(
    prog=RUN_DOT_PY, epilog=''.join(lines), allow_abbrev=False,
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
  # Parse arguments and instantiate context.
  args = parse_arguments()

  logger = Logger(in_color=args.color, is_verbose=args.verbose, stream=sys.stderr)
  fs = FS()
  global context
  context = Context(logger=logger, fs=fs, venv=VEnv(fs.root))

  # The first exception terminates command processing!
  try:
    # Ensure that spawned processes run within virtual environment.
    if args.commands[0] != 'bootstrap':
      context.venv.virtualize()
    logger.trace('current Python prefix {}', sys.prefix)
    logger.trace('subprocess prefix {}', context.fs.venv)

    # Execute commands.
    for command_name in args.commands:
      commands[command_name](*args.extras)
  except Exception as x:
    import traceback
    logger.error(f'{command_name} failed: {x.args[0]}')
    if logger.is_verbose:
      logger.trace('error traceback:')
      traceback.print_tb(x.__traceback__, file=logger.stream)

if __name__ == '__main__':
  main()
