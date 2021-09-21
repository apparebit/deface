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
from typing import Any, Callable, Optional, TextIO, Union

class Context:
  def __init__(self) -> None:
    self._logger: Optional['Logger'] = None
    self._fs: Optional[FS] = None
    self._venv: Optional[VEnv] = None

  @property
  def logger(self) -> 'Logger':
    if self._logger is None:
      raise ValueError('cannot access logger before it has been created')
    return self._logger

  @logger.setter
  def logger(self, logger: 'Logger') -> None:
    self._logger = logger

  @property
  def fs(self) -> 'FS':
    if self._fs is None:
      raise ValueError('cannot access file system object before it has been created')
    return self._fs

  @fs.setter
  def fs(self, fs: 'FS') -> None:
    self._fs = fs

  @property
  def venv(self) -> 'VEnv':
    if self._venv is None:
      raise ValueError(
        'cannot access virtual environment object before it has been created'
      )
    return self._venv

  @venv.setter
  def venv(self, venv: 'VEnv') -> None:
    self._venv = venv


context = Context()

# --------------------------------------------------------------------------------------
# Utilities: Logging

# Is needed before Logger instance can be created.
RUN_DOT_PY: str = p[2:] if (p := sys.argv[0]).startswith('./') else p

class Logger:
  """A console logger. It may print in color and in detail, to stderr by default"""
  def __init__(
    self,
    *,
    in_color: Optional[bool] = None,
    is_verbose: bool = False,
    stream: TextIO = sys.stderr,
  ) -> None:
    self.is_tracing: bool = is_verbose
    self.stream: TextIO = stream

    if in_color is None:
      in_color = stream.isatty()
    self.sgr: Callable[[str], str] = self._do_sgr if in_color else self._do_not_sgr

  def _do_sgr(self, code: str) -> str:
    return f'\x1b[{code}m'

  def _do_not_sgr(self, _: str) -> str:
    return ''

  def println(self, on: str, message: str, off: str) -> None:
    """Print the ANSI escape code ``on``, message, and escape code ``off``."""
    self.stream.write(f'{self.sgr(on)}{RUN_DOT_PY} >> {message}{self.sgr(off)}\n')

  def trace(self, message: str, *args: Any, **kwargs: Any) -> None:
    """If in verbose mode, write the formatted message to standard error."""
    if self.is_tracing:
      self.println('1', message.format(*args, **kwargs), '0')

  def announce(self, message: str) -> None:
    """Write the highlighted announcement message to standard error."""
    self.println('1;45;38;5;231', message, '0;49;39')

  def warning(self, message: str) -> None:
    """Write the warning message to standard error."""
    self.println('1;103', message, '0;49')

  def error(self, message: str) -> None:
    """Write the error message to standard error."""
    self.println('1;31', message, '0;39')

# --------------------------------------------------------------------------------------
# Utilities: Program Execution

_exec_env: dict[str, str] = {
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
  context.logger.trace(' '.join(cmd))

  # Merge environment variables, then spawn subprocess with command.
  kwargs['env'] = _exec_env | kwargs.get('env', {})
  return subprocess.run(cmd, check=True, **kwargs)

# --------------------------------------------------------------------------------------
# Utilities: File System

class TemporaryDirectory(tempfile.TemporaryDirectory):
  """Context manager for temporary directory named by path object."""
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

  def open_file(self, path: Path) -> None:
    """Open the file in a suitable application."""
    context.logger.trace('open file {}', path)
    if sys.platform == 'darwin':
      exec('open', path)
    elif sys.platform == 'linux':
      if not shutil.which('xdg-open'):
        raise NotImplementedError('unable to locate xdg-open command')
      exec('xdg-open', path)
    elif sys.platform.startswith('win32'):
      os.startfile(path) # Only available on Windows
    else:
      raise NotImplementedError(f'open_file() does not support {sys.platform}')

# --------------------------------------------------------------------------------------
# Virtual Environment

class VEnv:
  BIN = 'Scripts' if sys.platform == 'win32' else 'bin'
  CONFIG = 'pyvenv.cfg'
  DIR = '.venv'
  SEP = re.compile(r'=')
  PYPROJECT = 'pyproject.toml'
  DEV_GROUPS = {'dev', 'doc', 'test'}

  def __init__(self, project: Optional[Path] = None, venv: Optional[Path] = None):
    if project is None:
      project = context.fs.root
    if venv is None:
      venv = project / VEnv.DIR
    self.project_root = project
    self.root = venv

  def is_venv_running(self) -> bool:
    """Test whether this Python is running within a PEP 405 virtual environment."""
    return sys.prefix != getattr(sys, 'base_prefix', sys.prefix)

  def load_venv_config(self) -> dict[str, str]:
    """Parse a virtual environment's configuration."""
    with open(self.root / VEnv.CONFIG, encoding='utf8') as file:
      lines = file.read().splitlines()
    pairs = [VEnv.SEP.split(l) for l in lines if l.strip()]
    return { k.strip(): v.strip() for [k, v] in pairs}

  def validate_as_venv(self) -> Optional[dict[str, str]]:
    """Validate given path as virtual environment, returning its configuration."""
    if self.root.exists() and (cfg_path := self.root / VEnv.CONFIG).exists():
      try:
        cfg = self.load_venv_config()
        if 'home' in cfg:
          return cfg
      except Exception as x:
        context.logger.error(f'error loading {cfg_path}: {x.args[0]}')
    return None

  def check_active_venv(self) -> None:
    """Check that given path identifies active virtual environment."""
    sys_prefix = exec(
      'python3', '-c', 'import sys; print(sys.prefix)',
      capture_output=True, encoding='utf8',
    ).stdout.strip()
    if sys_prefix != str(self.root):
      raise RuntimeError(
        f"Python claims '{sys_prefix}' as venv instead of '{self.root}'"
      )

  def activate_venv(self) -> None:
    """Activate the virtual environment."""
    context.fs.venv = self.root
    _exec_env['PATH'] = str(self.root / VEnv.BIN) + os.pathsep + os.environ['PATH']
    _exec_env['VIRTUAL_ENV'] = str(self.root)

  def install_venv(self) -> None:
    """Create a new virtual environment."""
    exec('python3', '-m', 'venv', self.root)

  def lookup_dependencies(self) -> list[str]:
    """Extract project's optional dependencies."""
    cfg_text = (self.project_root / VEnv.PYPROJECT).read_text('utf8')
    # Recent versions of pip include tomli, older versions include toml.
    from importlib import import_module
    try:
      cfg = import_module('pip._vendor.tomli').loads(cfg_text) # type: ignore
    except ModuleNotFoundError:
      cfg = import_module('pip._vendor.toml').loads(cfg_text) # type: ignore
    groups = cfg.get('project', {}).get('optional-dependencies', {})
    return [deps for g in groups if g in VEnv.DEV_GROUPS for deps in groups[g]]

  def python(self, *args: Union[str, Path], **kwargs: Any) -> None:
    """invoke python on the arguments"""
    exec('python3', *args, **kwargs)

  def bootstrap(self) -> None:
    """install virtual environment and development dependencies"""
    context.logger.announce(f"install venv '{self.root}'")
    self.install_venv()
    self.activate_venv()
    self.check_active_venv()

    dependencies = self.lookup_dependencies()
    context.logger.announce('ensure packages are installed')
    context.logger.trace(', '.join(dependencies[:7]))
    context.logger.trace(', '.join(dependencies[7:]))
    self.python('-m', 'pip', 'install', *dependencies)

  def virtualize(self) -> None:
    """Ensure that subprocesses use virtual environment."""
    if self.is_venv_running():
      return
    if not self.root.exists():
      self.bootstrap()
    elif self.validate_as_venv():
      self.activate_venv()
      self.check_active_venv()
    else:
      raise RuntimeError(
        f"virtual environment obstructed by {self.root}; please delete"
      )

# --------------------------------------------------------------------------------------
# @command

CommandT = Callable[..., None]

special_commands: set[str] = set()
commands: dict[str, Callable[..., None]] = {}

def command(
  fn: CommandT, *, name: Optional[str] = None, force_simple: bool = False
) -> CommandT:
  """Turn a function into a command."""
  cmd_name: str = fn.__name__ if name is None else name

  @functools.wraps(fn)
  def wrapper(*args: str) -> None:
    context.logger.announce(cmd_name + ' ' + ', '.join(args) if args else cmd_name)
    fn(*args)

  if (not force_simple) and len(signature(fn).parameters) > 0:
    special_commands.add(cmd_name)
  commands[cmd_name] = wrapper
  return fn

# --------------------------------------------------------------------------------------
# The Commands

@command
def bootstrap() -> None:
  """install virtual environment and development dependencies"""
  context.venv.bootstrap()

@command
def python(*args: Union[str, Path]) -> None:
  """invoke Python on arguments in virtual environment"""
  context.venv.python(*args)

@command
def pip(*args: Union[str, Path]) -> None:
  "invoke pip on arguments in virtual environment"
  context.venv.python('-m', 'pip', *args)

@command
def clean() -> None:
  """delete build artifacts"""
  context.fs.delete_directory(context.fs.dist)
  context.fs.delete_directory(context.fs.docs / '_build')
  context.fs.make_directory(context.fs.docs / '_build')

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
  exec('sphinx-build', '-M', 'html', context.fs.docs, context.fs.docs / '_build')
  context.fs.open_file(context.fs.docs / '_build' / 'html' / 'index.html')

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
  with context.fs.temporary_directory(prefix='publish-docs') as tmpdir:
    context.fs.copy(context.fs.docs / '_build' / 'html', tmpdir)
    exec('git', 'checkout', 'gh-pages')
    context.fs.delete_contents(
      context.fs.root,
      excludes=set(['.git', '.gitignore', '.venv'])
    )
    context.fs.copy(tmpdir, context.fs.root)

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

  context.logger = Logger(
    in_color=args.color, is_verbose=args.verbose, stream=sys.stderr
  )
  context.fs = FS()
  context.venv = VEnv()

  # The first exception terminates command processing!
  try:
    # Ensure that spawned processes run within virtual environment.
    if args.commands[0] != 'bootstrap':
      context.venv.virtualize()
    context.logger.trace('current Python prefix {}', sys.prefix)
    context.logger.trace('subprocess prefix {}', context.fs.venv)

    # Execute commands.
    for command_name in args.commands:
      commands[command_name](*args.extras)
  except Exception as x:
    import traceback
    context.logger.error(f'{command_name} failed: {x.args[0]}')
    if context.logger.is_tracing:
      context.logger.trace('error traceback:')
      traceback.print_tb(x.__traceback__, file=context.logger.stream)

if __name__ == '__main__':
  main()
