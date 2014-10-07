#!/usr/bin/python
# Copyright 2014 Google Inc. All rights reserved.
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

"""@file build.py Linux example build script.

Builds a tiny example using cmake.

Run 'build.py --help' for options.
"""

import argparse
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir,
                             os.pardir))
import buildutil.common
import buildutil.linux


def main():
  parser = argparse.ArgumentParser()
  buildutil.linux.BuildEnvironment.add_arguments(parser)
  args = parser.parse_args()

  retval = -1

  env = buildutil.linux.BuildEnvironment(args)

  # Add cmake flags specific to our test build.
  env.cmake_flags = '-DMESSAGE="Hello, World!"'

  try:
    env.git_clean()
    env.run_cmake()
    env.run_make()
    env.make_archive(['Hello'], 'output.zip')

    retval = 0

  except buildutil.common.Error as e:
    print >> sys.stderr, 'Caught buildutil error: %s' % e.error_message
    retval = e.error_code

  except IOError as e:
    print >> sys.stderr, 'Caught IOError for file %s: %s' % (e.filename,
                                                             e.strerror)
    retval = -1

  return retval

if __name__ == '__main__':
  sys.exit(main())
