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

"""
The command line interface to *deface*.
"""

from argparse import ArgumentParser, BooleanOptionalAction
import sys
from typing import Any

from deface import __version__
from deface.serde import dumps, loads
from deface.ingest import find_simultaneous_posts, PostHistory
from deface.logger import Logger, pluralize
from deface.validator import Validator

__all__ = ['create_parser', 'main']

def create_parser() -> ArgumentParser:
  """Create the argument parser for the deface command line tool."""
  prog = 'deface'
  version = f'{prog} {__version__}'
  description = 'Clean and consolidate posts exported from Facebook.'
  file_help = 'path of ``your_posts_n.json`` file extracted from data archive'

  parser = ArgumentParser(
    prog=prog,
    description=description,
    # The epilog consists of U+3164, the Hangul filler, to force a blank line.
    # It's necessary because Python ignores various space characters.
    epilog='ㅤ',
    add_help=False,
  )

  # Tool options
  about = parser.add_argument_group('tool options')
  about.add_argument(
    '-h', '--help',
    action='help',
    help='show detailed help message and exit'
  )
  about.add_argument(
    '-V', '--version',
    action='version', version=version
  )

  # Output options
  this_run = parser.add_argument_group('output options')
  this_run.add_argument(
    '--color',
    action=BooleanOptionalAction, default=True,
    help='enable or disable the use of color in the output'
  )
  this_run.add_argument(
    '-f', '--format',
    choices=['json', 'ndjson', 'pretty', 'none'], default='ndjson',
    help='export data as plain, newline-delimited, or pretty-printed JSON, '
    ' or not at all'
  )

  # Positional arguments
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
  parser = create_parser()
  args = parser.parse_args()
  if sys.version_info < (3, 9,):
    parser.exit(status=2, message='deface requires Python 3.9 or later')

  # Make errors and warnings appear in line-terminated comments. While they are
  # printed to standard error instead of standard output, that nonetheless helps
  # to visually offset them from the JSON output. Besides, some users may just
  # want to include errors or warnings in the output as well.
  logger = Logger(prefix = '// ', use_color=args.color)

  # Iterate over files and collect posts.
  processed = 0
  malformed = 0

  history = PostHistory()
  for filename in args.filenames:
    logger.info(f'Processing file "{filename}"')
    try:
      with open(filename, 'rb') as file:
        json_data = loads(file.read())
    except Exception as read_err:
      logger.error(read_err)
      continue
    if isinstance(json_data, dict) and 'status_updates' in json_data:
      json_data = json_data['status_updates']
    if isinstance(json_data, list):
      processed += len(json_data)

    wrapped_data = Validator[Any](json_data, filename=filename)
    errors = history.ingest(wrapped_data)
    malformed += len(errors)
    for err in errors:
      logger.error(err)

  # Extract timeline.
  timeline = history.timeline()
  ingested = len(timeline)

  # Warn about multiple posts with the same timestamp. They do happen. But they
  # do happen so rarely that they deserve manual validation.
  simultaneous_times = 0
  simultaneous_posts = 0
  for timeline_range in find_simultaneous_posts(timeline):
    count = timeline_range.stop - timeline_range.start
    simultaneous_times += 1
    simultaneous_posts += count
    posts = [timeline[index] for index in timeline_range]
    logger.warn(
      f'There are {count} posts with timestamp {posts[0].timestamp}',
      *posts
    )

  # Emit the timeline of posts.
  if args.format in ['json', 'pretty']:
    sys.stdout.write('[\n')

  if args.format != 'none':
    for index, post in enumerate(timeline):
      if args.format != 'pretty':
        sys.stdout.write(dumps(post))
      else:
        sys.stdout.write(dumps(post, indent=2))
      if args.format != 'ndjson' and index < ingested - 1:
        sys.stdout.write(',\n')
      else:
        sys.stdout.write('\n')

  if args.format in ['json', 'pretty']:
    sys.stdout.write(']\n')
  sys.stdout.flush()

  # Sign off.
  filecount = len(args.filenames)
  message = f'Processed {filecount:,} {pluralize(filecount, "file")} '
  message += f'with {processed:,} {pluralize(processed, "raw post")}'
  if malformed:
    message += f', including {malformed:,} {pluralize(malformed, "malformed one")}'
  message += f';\nyielded {ingested:,} {pluralize(ingested, "cleaned post")}'
  if simultaneous_times:
    message += f', including {simultaneous_posts} that share '
    message += f'{simultaneous_times} timestamps with other posts'
  message += '.'
  logger.done(message)
