#!/usr/bin/python
# Copyright 2014 Google Inc. All Rights Reserved.
#
# This software is provided 'as-is', without any express or implied
# warranty.  In no event will the authors be held liable for any damages
# arising from the use of this software.
# Permission is granted to anyone to use this software for any purpose,
# including commercial applications, and to alter it and redistribute it
# freely, subject to the following restrictions:
# 1. The origin of this software must not be misrepresented; you must not
# claim that you wrote the original software. If you use this software
# in a product, an acknowledgment in the product documentation would be
# appreciated but is not required.
# 2. Altered source versions must be plainly marked as such, and must not be
# misrepresented as being the original software.
# 3. This notice may not be removed or altered from any source distribution.

"""Linux example build script.

Builds a tiny example using cmake.

Run 'build.py --help' for options.
"""

import argparse
import os
import sys

# sys.path[0] points to the script directory, when available.
sys.path.append(os.path.join(sys.path[0], '..', '..', '..'))

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
