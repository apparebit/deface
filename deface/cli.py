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
import sys
from typing import Any

from deface import __version__
from deface.json_io import dumps, loads
from deface.ingest import ingest_into_history
from deface.logger import Logger
from deface.model import PostHistory, find_simultaneous_posts
from deface.validator import Validator

def create_parser() -> ArgumentParser:
  """Create the argument parser for the deface command line tool."""
  prog = 'deface'
  version = f'{prog} {__version__}'
  description = 'Clean and consolidate posts exported from Facebook.'
  file_help = 'Path of ``your_posts_n.json`` file extracted from data archive'

  parser = ArgumentParser(prog=prog, description=description, add_help=False)
  about = parser.add_argument_group('tool options')
  about.add_argument(
    '-h', '--help', action='help',
    help='show detailed help message and exit'
  )
  about.add_argument('-V', '--version', action='version', version=version)

  this_run = parser.add_argument_group('output options')
  this_run.add_argument(
    '-f', '--format',
    nargs=1, default='ndjson', choices=['ndjson', 'json', 'pretty'],
    help='Set output format to ``ndjson`` for newline-delimited JSON, '
    '``json`` for regular JSON, or ``pretty`` for nicely indented JSON.'
  )

  parser.add_argument('filenames', metavar='FILE', nargs='+', help=file_help)

  return parser

def main() -> None:
  """
  A command line tool to convert Facebook posts from their personal archive
  format to a simpler, cleaner version. The tool reads in one or more files with
  possibly overlapping post data, simplifies the structure of the data,
  eliminates redundant information, reconciles the records into a single
  timeline, and then exports that timeline of posts as JSON.
  """
  args = create_parser().parse_args()

  # Make errors and warnings appear in line-terminated comments. While they are
  # printed to standard error instead of standard out, that nonetheless helps to
  # visually offset them from the JSON output and smart users may just want to
  # pipe them into the output as well.
  logger = Logger(prefix = '// ')

  # Collect posts.
  history = PostHistory()
  for filename in args.filenames:
    try:
      with open(filename, 'rb') as file:
        json_data = loads(file.read())
    except Exception as read_err:
      logger.error(read_err)
      continue

    wrapped_data = Validator[Any](json_data, filename=filename)
    errors = ingest_into_history(wrapped_data, history)
    for err in errors:
      logger.error(err)

  # Extract timeline.
  timeline = history.timeline()
  timeline_length = len(timeline)

  # Warn about multiple posts with the same timestamp. They do happen. But they
  # do happen so rarely that they deserve manual validation.
  simultaneous_posts = find_simultaneous_posts(timeline)
  for index_range in simultaneous_posts:
    post = timeline[index_range.start]
    count = index_range.stop - index_range.start
    logger.warn(f'There are {count} posts with timestamp {post.timestamp}')

  # Emit the timeline of posts.
  if args.format != 'ndjson':
    sys.stdout.write('[\n')

  for index, post in enumerate(timeline):
    if args.format != 'pretty':
      sys.stdout.write(dumps(post))
    else:
      sys.stdout.write(dumps(post, indent=2))
    if args.format != 'ndjson' and index < timeline_length - 1:
      sys.stdout.write(',\n')
    else:
      sys.stdout.write('\n')

  if args.format != 'ndjson':
    sys.stdout.write(']\n')
  sys.stdout.flush()

  # Sign off.
  sign_off = f'Ingested {timeline_length} posts'
  if logger.error_count > 0:
    sign_off += f' while also encountering {logger.error_count} errors'
  sign_off += '.'
  logger.done(sign_off)
