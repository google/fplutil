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
#

import argparse
import distutils.spawn
import os
import sys
import unittest
sys.path.append('..')
import buildutil.common as common

mock_path = ''
mock_path_exists = True
saved_find_executable = distutils.spawn.find_executable
saved_path_exists = os.path.exists


def mock_os_path_exists(unused_path):
  return mock_path_exists


def mock_find_executable(unused_name):
  return mock_path


class CommonBuildUtilTest(unittest.TestCase):
  """Common base buildutil unit tests."""

  def setUp(self):
    self.git_clean_ran = False
    self.git_reset_ran = False

  def tearDown(self):
    distutils.spawn.find_executable = saved_find_executable
    os.path.exists = saved_path_exists

  def test_build_defaults(self):
    d = common.BuildEnvironment.build_defaults()
    self.assertIn(common._PROJECT_DIR, d)
    self.assertIn(common._CPU_COUNT, d)
    self.assertIn(common._MAKE_PATH, d)
    self.assertIn(common._GIT_PATH, d)
    self.assertIn(common._MAKE_FLAGS, d)
    self.assertIn(common._GIT_CLEAN, d)
    self.assertIn(common._VERBOSE, d)
    self.assertIn(common._OUTPUT_DIR, d)

  def test_init(self):
    d = common.BuildEnvironment.build_defaults()
    b = common.BuildEnvironment(d)
    self.assertEqual(b.project_directory, d[common._PROJECT_DIR])
    self.assertEqual(b.cpu_count, d[common._CPU_COUNT])
    self.assertEqual(b.make_path, d[common._MAKE_PATH])
    self.assertEqual(b.git_path, d[common._GIT_PATH])
    self.assertEqual(b.make_flags, d[common._MAKE_FLAGS])
    self.assertEqual(b.enable_git_clean, d[common._GIT_CLEAN])
    self.assertEqual(b.verbose, d[common._VERBOSE])
    self.assertEqual(b.output_directory, d[common._OUTPUT_DIR])

  def test_add_arguments(self):
    p = argparse.ArgumentParser()
    common.BuildEnvironment.add_arguments(p)
    args = ['--' + common._PROJECT_DIR, 'a',
            '--' + common._CPU_COUNT, 'b',
            '--' + common._MAKE_PATH, 'c',
            '--' + common._GIT_PATH, 'd',
            '--' + common._MAKE_FLAGS, 'e',
            '--' + common._GIT_CLEAN,
            '--' + common._VERBOSE,
            '--' + common._OUTPUT_DIR, 'f']

    argobj = p.parse_args(args)
    d = vars(argobj)

    self.assertEqual('a', d[common._PROJECT_DIR])
    self.assertEqual('b', d[common._CPU_COUNT])
    self.assertEqual('c', d[common._MAKE_PATH])
    self.assertEqual('d', d[common._GIT_PATH])
    self.assertEqual('e', d[common._MAKE_FLAGS])
    self.assertTrue(d[common._GIT_CLEAN])
    self.assertTrue(d[common._VERBOSE])
    self.assertEqual('f', d[common._OUTPUT_DIR])

  def test_find_path_from_binary(self):
    test_data = [
        (os.path.join(os.path.sep, 'a', 'b', 'c'), 0,
         os.path.join(os.path.sep, 'a', 'b', 'c')),
        (os.path.join(os.path.sep, 'a', 'b', 'c'), 1,
         os.path.join(os.path.sep, 'a', 'b')),
        (os.path.join(os.path.sep, 'a', 'b', 'c'), 2,
         os.path.join(os.path.sep, 'a')),
        (os.path.join(os.path.sep, 'a', 'b', 'c'), 3, os.path.sep),
        (os.path.join(os.path.sep, 'a', 'b', 'c'), 4, None),
        (os.path.join(os.path.sep, 'a', 'b', 'c'), -1,
         os.path.join(os.path.sep, 'a', 'b', 'c')),
        (os.path.join(os.path.sep, 'a'), 0, os.path.join(os.path.sep, 'a')),
        (os.path.join(os.path.sep, 'a'), 1, os.path.sep),
        (os.path.join(os.path.sep, 'a'), 2, None)]

    global mock_path
    distutils.spawn.find_executable = mock_find_executable  # reset in tearDown
    for (path, levels, expect) in test_data:
      mock_path = path
      result = common.BuildEnvironment._find_path_from_binary('foo', levels)
      self.assertEqual(result, expect)

  def test_run_make(self):
    d = common.BuildEnvironment.build_defaults()
    b = common.BuildEnvironment(d)
    # Mock the call to run_subprocess.
    b.run_subprocess = self.make_verifier
    b.make_flags = 'c d'
    b.project_directory = 'e'
    b.run_make()

  def make_verifier(self, args, cwd=None):
    """BuildEnvironment.run_subprocess mock for test_run_make.

    Args:
      args: Argument list as normally passed to run_subprocess.
      cwd: Working directory arg as normally passed to run_subprocess.
    """
    d = common.BuildEnvironment.build_defaults()
    # If the implementation changes arguments, this mock needs updating as well.
    expected = [d[common._MAKE_PATH],
                '-j', d[common._CPU_COUNT], '-C', 'e', 'c', 'd']
    self.assertListEqual(args, expected)
    if cwd:
      self.assertEqual(cwd, d[common._PROJECT_DIR])

  def test_git_clean(self):
    d = common.BuildEnvironment.build_defaults()
    b = common.BuildEnvironment(d)
    # Mock the call to run_subprocess.
    b.run_subprocess = self.git_clean_verifier
    global mock_path_exists
    os.path.exists = mock_os_path_exists  # reset in tearDown

    # first, unless enabled, git_clean() should do nothing.
    b.git_clean()
    self.assertFalse(self.git_clean_ran)
    self.assertFalse(self.git_reset_ran)
    b.enable_git_clean = True

    # next, should do nothing if not in git dir
    mock_path_exists = False
    b.git_clean()
    self.assertFalse(self.git_clean_ran)
    self.assertFalse(self.git_reset_ran)
    mock_path_exists = True

    # finally, should run
    b.project_directory = 'e'
    b.git_clean()
    self.assertTrue(self.git_clean_ran)
    self.assertTrue(self.git_reset_ran)

  def git_clean_verifier(self, args, cwd=None):
    """BuildEnvironment.run_subprocess mock for test_git_clean.

    Args:
      args: Argument list as normally passed to run_subprocess.
      cwd: Working directory arg as normally passed to run_subprocess.
    """
    d = common.BuildEnvironment.build_defaults()
    expected = None
    if 'clean' in args:
      self.git_clean_ran = True
      expected = [d[common._GIT_PATH], '-C', 'e', 'clean', '-d', '-f']
    else:
      if 'reset' in args:
        self.git_reset_ran = True
        expected = [d[common._GIT_PATH], '-C', 'e', 'reset', '--hard']
    self.assertIsNotNone(expected)
    self.assertListEqual(args, expected)
    if cwd:
      self.assertEqual(cwd, d[common._PROJECT_DIR])

  # TBD, these are highly dependent high level functions that may need refactor
  # to unit-test well, as they are currently difficult to mock. At the moment
  # the examples serve as functional tests for these.
  def test_make_archive(self):
    pass

  def test_write_archive(self):
    pass
