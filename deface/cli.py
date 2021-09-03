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

from argparse import ArgumentParser

from deface import __version__
from deface.jsonio import read_json
from deface.ingest import ingest_into_history
from deface.logger import Logger
from deface.model import PostHistory
from deface.validator import Validator

def create_parser() -> ArgumentParser:
  """Create the argument parser for the deface command line tool."""
  prog = 'deface'
  version = f'{prog} {__version__}'
  description = 'Clean and consolidate posts exported from Facebook.'

  parser = ArgumentParser(prog=prog, description=description)
  parser.add_argument('filenames', metavar='FILE', nargs='+')
  parser.add_argument('-V', '--version', action='version', version=version)

  return parser

def main():
  """
  A command line tool to convert Facebook posts from their personal archive
  format to a simpler, cleaner version. The tool reads in one or more files with
  possibly overlapping post data, simplifies the structure of the data,
  eliminates redundant information, reconciles the records into a single
  timeline, and then exports that timeline of posts as JSON.
  """
  args = create_parser().parse_args()

  logger = Logger()
  history = PostHistory()
  for filename in args.filenames:
    try:
      json_data = read_json(filename)
    except Exception as err:
      logger.error(err)
      continue

    wrapped_data = Validator(json_data, filename=filename)
    errors = ingest_into_history(wrapped_data, history)
    for err in errors:
      logger.error(err)

  posts = history.posts()
  sign_off = f'Ingested {len(posts)} posts'
  if logger.error_count > 0:
    sign_off += f', encountered {logger.error_count} errors'
  sign_off += '.'
  logger.done(sign_off)
