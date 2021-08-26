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

from deface import __version__
from deface.json_data import JsonData, read_json
from deface.ingest import ingest_into_history
from deface.logger import Logger
from deface.model import PostHistory

def main():
  prog = 'deface'
  version = f'{prog} {__version__}'
  description = 'Clean and consolidate posts exported from Facebook.'

  parser = argparse.ArgumentParser(prog=prog, description=description)
  parser.add_argument('filenames', metavar='FILE', nargs='+')
  parser.add_argument('-V', '--version', action='version', version=version)
  args = parser.parse_args()

  logger = Logger()
  history = PostHistory()
  for filename in args.filenames:
    try:
      json_data = read_json(filename)
    except Exception as err:
      logger.error(err)
      continue

    data = JsonData(json_data, filename=filename)
    errors = ingest_into_history(data, history)

    for err in errors:
      logger.error(err)

  sign_off = f'Ingested {len(history.list())} posts'
  if logger.error_count > 0:
    sign_off += f', encountered {logger.error_count} errors'
  sign_off += '.'
  logger.done(sign_off)
