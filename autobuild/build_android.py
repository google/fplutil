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

"""Android automated build script.

This script may be used for turnkey android builds of fplutil.

Optional environment variables:

ANDROID_SDK_HOME = Path to the Android SDK. Required if it is not passed on the
command line.
NDK_HOME = Path to the Android NDK. Required if it is not in passed on the
command line.
MAKE_FLAGS = String to override the default make flags with for ndk-build.
ANT_PATH = Path to ant executable. Required if it is not in $PATH or passed on
the command line.
"""

import argparse
import os
import sys

# sys.path[0] points to the script directory, when available.
sys.path.append(os.path.join(sys.path[0], '..'))

import buildutil.android
import buildutil.common

GOOGLETEST_DEFAULT_PATH = os.path.abspath('..')

def main():
  parser = argparse.ArgumentParser()
  buildutil.android.BuildEnvironment.add_arguments(parser)

  parser.add_argument('-G', '--gtest_path',
                        help='Path to Google Test', dest='gtest_path',
                        default=GOOGLETEST_DEFAULT_PATH)

  args = parser.parse_args()

  retval = -1

  env = buildutil.android.BuildEnvironment(args)

  gtest_arg = 'GOOGLETEST_PATH="%s"' % args.gtest_path
  if env.make_flags:
    env.make_flags = '%s %s' % (env.make_flags, gtest_arg)
  else:
    env.make_flags = gtest_arg

  try:
    env.git_clean()
    env.build_android_libraries(['libfplutil'], output='libs')
    env.build_android_apk(path='examples/libfplutil_example', output='apks')
    env.build_android_apk(path='libfplutil/tests', output='apks')
    env.make_archive(['libs', 'apks', 'libfplutil/include',
      'libfplutil/jni'], 'output.zip', exclude=['objs', 'objs-debug'])
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
