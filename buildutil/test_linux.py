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
#

import argparse
import os
import sys
import unittest
sys.path.append('..')
import buildutil.android as android
import buildutil.common as common
import buildutil.linux as linux


class LinuxBuildUtilTest(unittest.TestCase):
  """Linux-specific unit tests."""

  def test_build_defaults(self):
    d = linux.BuildEnvironment.build_defaults()
    # Verify that the linux ones are set.
    self.assertIn(linux._CMAKE_FLAGS, d)
    self.assertIn(linux._CMAKE_PATH, d)
    # Verify that a mandatory superclass one gets set.
    self.assertIn(common._PROJECT_DIR, d)
    # Verify that a required Android one does not get set.
    self.assertNotIn(android._NDK_HOME, d)

  def test_init(self):
    d = linux.BuildEnvironment.build_defaults()
    b = linux.BuildEnvironment(d)
    # Verify that the linux ones are set.
    self.assertEqual(b.cmake_flags, d[linux._CMAKE_FLAGS])
    self.assertEqual(b.cmake_path, d[linux._CMAKE_PATH])
    # Verify that a mandatory superclass one gets set.
    self.assertEqual(b.project_directory, d[common._PROJECT_DIR])
    # Verify that a required Android one does not get set.
    self.assertNotIn(android._NDK_HOME, vars(b))

  def test_add_arguments(self):
    p = argparse.ArgumentParser()
    linux.BuildEnvironment.add_arguments(p)
    args = ['--' + linux._CMAKE_FLAGS, 'a', '--' + linux._CMAKE_PATH, 'b']
    argobj = p.parse_args(args)
    d = vars(argobj)
    self.assertEqual('a', d[linux._CMAKE_FLAGS])
    self.assertEqual('b', d[linux._CMAKE_PATH])
    self.assertEqual(os.getcwd(), d[common._PROJECT_DIR])
    self.assertNotIn(android._NDK_HOME, d)

  def test_run_cmake(self):
    d = linux.BuildEnvironment.build_defaults()
    b = linux.BuildEnvironment(d)
    # Mock the call to run_subprocess.
    b.run_subprocess = self.cmake_verifier
    b.cmake_flags = 'c d'
    b.project_directory = 'e'
    b.run_cmake(gen='b')

  def cmake_verifier(self, args, cwd):
    """BuildEnvironment.run_subprocess mock for test_run_cmake.

    Args:
      args: Argument list as normally passed to run_subprocess.
      cwd: Working directory arg as normally passed to run_subprocess.
    """
    d = linux.BuildEnvironment.build_defaults()
    # If the implementation changes arguments, this mock needs updating as well.
    expected = [d[linux._CMAKE_PATH], '-G', 'b', 'c', 'd', 'e']
    self.assertListEqual(args, expected)
    self.assertEqual(cwd, 'e')

if __name__ == '__main__':
  unittest.main()
