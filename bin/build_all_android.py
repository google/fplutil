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
