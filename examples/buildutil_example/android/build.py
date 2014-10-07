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

"""@file build.py Android example build script.

Copies an NDK sample to the current directory and builds it.

Run 'build.py --help' for options.
"""

import argparse
import os
import shutil
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir,
                             os.pardir))
import buildutil.android
import buildutil.common


def main():
  # Parse arguments and create the build environment.
  parser = argparse.ArgumentParser()
  buildutil.android.BuildEnvironment.add_arguments(parser)
  args = parser.parse_args()
  env = buildutil.android.BuildEnvironment(args)

  # Clean the git working copy.
  env.git_clean()

  # Copy one of the NDK samples here and build it
  samplename = 'native-plasma'
  samplepath = os.path.join(env.ndk_home, 'samples', samplename)
  shutil.rmtree(samplename, True)
  shutil.copytree(samplepath, samplename)

  # Build the sample.
  (rc, errmsg) = env.build_all()
  if (rc == 0):
    # Archive the sample built in the apks directory to output.zip.
    env.make_archive(['apks'], 'output.zip', exclude=['objs', 'objs-debug'])
  else:
    print >> sys.stderr, errmsg

  return rc

if __name__ == '__main__':
  sys.exit(main())
