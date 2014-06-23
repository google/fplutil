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

"""Simple Android build script that builds everything recursively.

This script will build all Android projects and libraries under the current
directory with the build settings specified on the command line, or the defaults
for those not specified.

Run 'build_all_android.py --help' for options.
"""

import argparse
import os
import sys

# sys.path[0] points to the script directory, when available.
sys.path.append(os.path.join(sys.path[0], '..'))

import buildutil.android
import buildutil.common


def main():
  parser = argparse.ArgumentParser()
  buildutil.android.BuildEnvironment.add_arguments(parser)
  args = parser.parse_args()

  env = buildutil.android.BuildEnvironment(args)

  (rc, errmsg) = env.build_all()
  if (rc != 0):
    print >> sys.stderr, errmsg

  return rc

if __name__ == '__main__':
  sys.exit(main())
