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

import functools
import inspect
import operator
import os
import subprocess
import sys

from typing import Any, Optional

# The code in this module is inspired by:
# https://github.com/scikit-learn/scikit-learn/blob/main/doc/sphinxext/github_link.py
# https://github.com/chezou/tabula-py/blob/master/docs/conf.py

def _eprint(*args: Any) -> None:
  """Print the arguments to standard error."""
  for arg in args:
    print(arg, file=sys.stderr)

def _lookup_git_head() -> Optional[str]:
  """Look up git's current HEAD revision."""
  try:
    return subprocess.run(
      # Don't use HEAD since that may include local commits.
      ['git', 'rev-parse', 'origin/HEAD'],
      check=True,
      encoding='utf8',
      stdout=subprocess.PIPE,
    ).stdout.strip()
  except subprocess.SubprocessError as err:
    _eprint('Could not determine git commit id for HEAD:', err)
    return None

def _linkcode_resolve(
  domain: str,
  info: dict[str, str],
  organization: str,
  project: str,
  revision: Optional[str]
) -> Optional[str]:
  """
  Resolve the given Python module and fully-qualified entity name to a URL for
  the the entity's source code.
  """
  if revision is None:
    return None
  if domain != 'py':
    return None
  if 'module' not in info or 'fullname' not in info:
    return None

  modulename = info['module']
  fullname = info['fullname']
  # fullname must have at least one component, which is the module-level entity.
  basename = fullname.split('.')[0]

  try:
    # Without fromlist, __import__ returns top level module.
    module = __import__(modulename, fromlist=[basename])
    # attrgetter() fails for the attributes of dataclasses.
    obj = operator.attrgetter(fullname)(module)
  except Exception:
    return None

  try:
    filename = inspect.getsourcefile(obj)
  except Exception:
    filename = None
  if filename is None:
    return None

  try:
    lineno = inspect.getsourcelines(obj)[1]
  except Exception:
    return None

  # The repository root is three dirname() away.
  rootpath = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
  relpath = os.path.relpath(filename, start=rootpath)

  url = f'https://github.com/{organization}/{project}/blob'
  url += f'/{revision}/{relpath}#L{lineno}'
  return url

def make_linkcode_resolve(organization: str, project: str):
  return functools.partial(
    _linkcode_resolve,
    organization=organization,
    project=project,
    revision=_lookup_git_head()
  )
