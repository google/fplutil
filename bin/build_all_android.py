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
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir))
import buildutil.android
import buildutil.common

_SEARCH_PATH = 'search_path'
_APK_OUTPUT_DIR = 'apk_output_dir'
_LIB_OUTPUT_DIR = 'lib_output_dir'
_EXCLUDE_DIRS = 'exclude_dirs'

class BuildAllEnvironment(buildutil.android.BuildEnvironment):

  """Class representing the build environment of multiple Android projects.

  Attributes:
    search_path: Path to start searching for projects to build.
  """

  def __init__(self, arguments):
    """Setup the environment to build projects under the working directory.

    Args:
      arguments: The argument object returned from ArgumentParser.parse_args().
    """

    super(BuildAllEnvironment, self).__init__(arguments)

    if type(arguments) is dict:
      args = arguments
    else:
      args = vars(arguments)

    self.search_path = args[_SEARCH_PATH]

  @staticmethod
  def build_defaults():
    """Helper function to set build defaults.

    Returns:
      A dict containing appropriate defaults for a build.
    """
    args = buildutil.android.BuildEnvironment.build_defaults()

    args[_SEARCH_PATH] = '.'
    args[_APK_OUTPUT_DIR] = 'apks'
    args[_LIB_OUTPUT_DIR] = 'libs'
    args[_EXCLUDE_DIRS] = ''
    return args

  @staticmethod
  def add_arguments(parser):
    """Add module-specific command line arguments to an argparse parser.

    This will take an argument parser and add arguments appropriate for this
    module. It will also set appropriate default values.

    Args:
      parser: The argparse.ArgumentParser instance to use.
    """
    defaults = BuildAllEnvironment.build_defaults()

    buildutil.android.BuildEnvironment.add_arguments(parser)

    parser.add_argument('-R', '--' + _SEARCH_PATH,
                        help='Path to search for Android projects.',
                        dest=_SEARCH_PATH, default=defaults[_SEARCH_PATH])
    parser.add_argument('-O', '--' + _APK_OUTPUT_DIR,
                        help='Directory to place built apks.',
                        dest=_APK_OUTPUT_DIR,
                        default=defaults[_APK_OUTPUT_DIR])
    parser.add_argument('-L', '--' + _LIB_OUTPUT_DIR,
                        help='Directory to place built shared libraries.',
                        dest=_LIB_OUTPUT_DIR,
                        default=defaults[_LIB_OUTPUT_DIR])
    parser.add_argument('-E', '--' + _EXCLUDE_DIRS,
                        help='List of directory names (not paths) to exclude '
                        'from the Android project search.',
                        dest=_EXCLUDE_DIRS, default=defaults[_EXCLUDE_DIRS],
                        nargs='+')

def main():
  parser = argparse.ArgumentParser()
  BuildAllEnvironment.add_arguments(parser)
  args = parser.parse_args()

  env = buildutil.android.BuildEnvironment(args)

  (rc, errmsg) = env.build_all(path=args.search_path,
                               apk_output=args.apk_output_dir,
                               lib_output=args.lib_output_dir,
                               exclude_dirs=args.exclude_dirs)
  if (rc != 0):
    print >> sys.stderr, errmsg

  return rc

if __name__ == '__main__':
  sys.exit(main())
