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
import os
import platform
import sys
import unittest
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir))
import buildutil.android as android
import buildutil.common as common
import buildutil.common_test as common_test
import buildutil.linux as linux

_saved_walk = os.walk

class FileMock(object):

  def __init__(self, string):
    self.string = string

  def close(self):
    pass

  def read(self, nbytes):
    r = self.string[0:nbytes]
    self.string = self.string[nbytes:]
    return r


class BuildAndroidLibrariesMock(object):

  def __init__(self, test):
    self.test = test
    self.subprojects = []
    self.output = None

  def verify(self, subprojects, output=None):
    self.test.assertEqual(self.output, output)
    self.test.assertListEqual(sorted(self.subprojects), sorted(subprojects))

  def expect(self, subprojects, output='libs'):
    self.subprojects = subprojects
    self.output = output


class BuildAndroidAPKMock(object):

  def __init__(self, test):
    self.test = test
    self.path = None
    self.output = None
    self.fail_if_called = False

  def fail(self, fail=True):
    self.fail_if_called = fail

  def verify(self, path='.', output=None):
    self.test.assertFalse(self.fail_if_called)
    self.test.assertEqual(self.output, output)
    self.test.assertEqual(self.path, path)

  def expect(self, path, output='apks'):
    self.path = path
    self.output = output


class FileNode(object):

  def __init__(self, name, parent=None):
    self.name = name
    self.parent = parent
    if parent:
      self.name = os.path.join(parent.name, name)

    self.files = []
    self.dirs = []

  def add_files(self, namelist):
    self.files += namelist

  def add_subdir(self, name):
    node = FileNode(name, self)
    self.dirs.append(node)
    return node


class OsWalkMock(object):

  def __init__(self, test):
    self.root = None
    self.test = test
    self.project = None

  def expect(self, path):
    self.project = path

  def set_root(self, root):
    self.root = root

  def walk(self, path):
    self.test.assertEqual(self.project, path)
    # Perform a BFS traversal as a generator to mimic how topdown os.walk works.
    nodes = [self.root]
    while len(nodes):
      n = nodes.pop(0)
      rc = (n.name, [os.path.basename(m.name) for m in n.dirs], n.files)
      yield rc
      # Pick up changes to the dirlist, per how os.walk works in real life.
      name, dirs, unused_files = rc
      nodes += [d for d in n.dirs if os.path.basename(d.name) in dirs]


class AndroidBuildUtilTest(unittest.TestCase):
  """Android-specific unit tests."""

  def tearDown(self):
    # Undo mocks.
    os.walk = _saved_walk

  def test_build_defaults(self):
    d = android.BuildEnvironment.build_defaults()
    # Verify that the android ones are set.
    self.assertIn(android._NDK_HOME, d)
    self.assertIn(android._SDK_HOME, d)
    self.assertIn(android._ANT_PATH, d)
    self.assertIn(android._ANT_FLAGS, d)
    self.assertIn(android._ANT_TARGET, d)
    self.assertIn(android._APK_KEYSTORE, d)
    self.assertIn(android._APK_PASSFILE, d)
    self.assertIn(android._APK_KEYALIAS, d)
    self.assertIn(android._SIGN_APK, d)
    # Verify that a mandatory superclass one gets set.
    self.assertIn(common._PROJECT_DIR, d)
    # Verify that the Linux ones do not get set.
    self.assertNotIn(linux._CMAKE_FLAGS, d)
    self.assertNotIn(linux._CMAKE_PATH, d)

  def test_init(self):
    d = android.BuildEnvironment.build_defaults()
    b = android.BuildEnvironment(d)
    # Verify that the Android ones are set.
    self.assertEqual(b.ndk_home, d[android._NDK_HOME])
    self.assertEqual(b.sdk_home, d[android._SDK_HOME])
    self.assertEqual(b.ant_path, d[android._ANT_PATH])
    self.assertEqual(b.ant_flags, d[android._ANT_FLAGS])
    self.assertEqual(b.ant_target, d[android._ANT_TARGET])
    self.assertEqual(b.apk_keystore, d[android._APK_KEYSTORE])
    self.assertEqual(b.apk_passfile, d[android._APK_PASSFILE])
    self.assertEqual(b.apk_keyalias, d[android._APK_KEYALIAS])
    self.assertEqual(b.sign_apk, d[android._SIGN_APK])
    # Verify that a mandatory superclass one gets set.
    self.assertEqual(b.project_directory, d[common._PROJECT_DIR])
    # Verify that the Linux ones do not get set.
    self.assertNotIn(linux._CMAKE_FLAGS, vars(b))
    self.assertNotIn(linux._CMAKE_PATH, vars(b))

  def test_add_arguments(self):
    p = argparse.ArgumentParser()
    android.BuildEnvironment.add_arguments(p)
    args = ['--' + android._SDK_HOME, 'a',
            '--' + android._NDK_HOME, 'b',
            '--' + android._ANT_PATH, 'c',
            '--' + android._ANT_FLAGS, 'd',
            '--' + android._ANT_TARGET, 'e',
            '--' + android._APK_KEYSTORE, 'f',
            '--' + android._APK_PASSFILE, 'g',
            '--' + android._APK_KEYALIAS, 'h',
            '--' + android._SIGN_APK]
    argobj = p.parse_args(args)
    d = vars(argobj)

    self.assertEqual('a', d[android._SDK_HOME])
    self.assertEqual('b', d[android._NDK_HOME])
    self.assertEqual('c', d[android._ANT_PATH])
    self.assertEqual('d', d[android._ANT_FLAGS])
    self.assertEqual('e', d[android._ANT_TARGET])
    self.assertEqual('f', d[android._APK_KEYSTORE])
    self.assertEqual('g', d[android._APK_PASSFILE])
    self.assertEqual('h', d[android._APK_KEYALIAS])
    self.assertTrue(d[android._SIGN_APK])

    self.assertEqual(os.getcwd(), d[common._PROJECT_DIR])
    # Verify that the Linux ones do not get set.
    self.assertNotIn(linux._CMAKE_FLAGS, d)
    self.assertNotIn(linux._CMAKE_PATH, d)

  def test_construct_android_manifest(self):
    m = android.AndroidManifest(None)
    self.assertEqual(m.min_sdk, 0)
    self.assertEqual(m.target_sdk, 0)
    self.assertIsNone(m.path)
    with self.assertRaises(common.ConfigurationError):
      android.AndroidManifest('/non existent/bogus_path')

  def test_manifest_parse_trivial(self):
    f = FileMock(
        '<manifest '
        '  xmlns:android="http://schemas.android.com/apk/res/android"\n'
        '  package="com.google.fpl.libfplutil_test">\n'
        '  <uses-sdk android:minSdkVersion="1"/>\n'
        '  <application>\n'
        '    <activity android:name="android.app.NativeActivity">\n'
        '      <meta-data android:name="android.app.lib_name"\n'
        '                 android:value="test"/>\n'
        '    </activity>\n'
        '  </application>\n'
        '</manifest>')
    m = android.AndroidManifest(None)
    m._parse(f)
    self.assertEqual(m.min_sdk, 1)
    self.assertEqual(m.target_sdk, m.min_sdk)

  def test_manifest_parse_native_activity_no_lib(self):
    f = FileMock(
        '<manifest '
        '  xmlns:android="http://schemas.android.com/apk/res/android"\n'
        '  package="com.google.fpl.libfplutil_test">\n'
        '  <uses-sdk android:minSdkVersion="1"/>\n'
        '  <application>\n'
        '    <activity android:name="android.app.NativeActivity">\n'
        '    </activity>\n'
        '  </application>\n'
        '</manifest>')
    m = android.AndroidManifest(None)
    with self.assertRaises(common.ConfigurationError):
      m._parse(f)

  def test_manifest_parse_with_target(self):
    f = FileMock(
        '<manifest '
        '  xmlns:android="http://schemas.android.com/apk/res/android"\n'
        '  package="com.google.fpl.libfplutil_test">\n'
        '  <uses-sdk android:minSdkVersion="1" '
        '            android:targetSdkVersion="2"/>\n'
        '  <application>\n'
        '    <activity android:name="android.app.NativeActivity">\n'
        '      <meta-data android:name="android.app.lib_name"\n'
        '                 android:value="test"/>\n'
        '    </activity>\n'
        '  </application>\n'
        '</manifest>')
    m = android.AndroidManifest(None)
    m._parse(f)
    self.assertEqual(m.min_sdk, 1)
    self.assertEqual(m.target_sdk, 2)

  def test_manifest_parse_with_bad_target(self):
    f = FileMock(
        '<manifest \n'
        '  xmlns:android="http://schemas.android.com/apk/res/android"\n'
        '  package="com.google.fpl.libfplutil_test">\n'
        '  <uses-sdk android:minSdkVersion="1" '
        '            android:targetSdkVersion="-2"/>\n'
        '  <application>\n'
        '    <activity android:name="android.app.NativeActivity">\n'
        '      <meta-data android:name="android.app.lib_name"\n'
        '                 android:value="test"/>\n'
        '    </activity>\n'
        '  </application>\n'
        '</manifest>')
    m = android.AndroidManifest(None)
    m._parse(f)
    self.assertEqual(m.min_sdk, 1)
    # this is an error but we want to catch in processing, not parsing
    self.assertEqual(m.target_sdk, -2)

  def test_manifest_parse_missing_min_version(self):
    f = FileMock(
        '<manifest '
        'xmlns:android="http://schemas.android.com/apk/res/android">\n'
        '<uses-sdk/>\n'
        '</manifest>')
    m = android.AndroidManifest(None)
    with self.assertRaises(common.ConfigurationError):
      m._parse(f)

  def test_manifest_parse_missing_uses_sdk(self):
    f = FileMock(
        '<manifest '
        'xmlns:android="http://schemas.android.com/apk/res/android">\n'
        '</manifest>')
    m = android.AndroidManifest(None)
    with self.assertRaises(common.ConfigurationError):
      m._parse(f)

  def test_manifest_parse_error(self):
    f = FileMock('<manifest ')
    m = android.AndroidManifest(None)
    with self.assertRaises(common.ConfigurationError):
      m._parse(f)

  def test_construct_buildxml(self):
    b = android.BuildXml(None)
    self.assertIsNone(b.path)
    self.assertIsNone(b.project_name)
    with self.assertRaises(common.ConfigurationError):
      android.BuildXml('/non existent/bogus_path')

  def test_buildxml_parse_trivial(self):
    f = FileMock('<project name="foo"/>')
    b = android.BuildXml(None)
    b._parse(f)
    self.assertEqual(b.project_name, 'foo')
    self.assertIsNone(b.path)

  def test_buildxml_missing_name(self):
    f = FileMock('<project/>')
    b = android.BuildXml(None)
    with self.assertRaises(common.ConfigurationError):
      b._parse(f)

  def test_buildxml_missing_project(self):
    f = FileMock('<not-project name="foo"/>')
    b = android.BuildXml(None)
    with self.assertRaises(common.ConfigurationError):
      b._parse(f)

  def test_build_libraries(self):
    d = android.BuildEnvironment.build_defaults()
    b = android.BuildEnvironment(d)
    m = common_test.RunCommandMock(self)
    b.run_subprocess = m
    ndk_build = os.path.join(b.ndk_home, 'ndk-build')
    l = 'libfoo'
    lpath = os.path.abspath(os.path.join(b.project_directory, l))
    expect = [ndk_build, '-j' + str(b.cpu_count), '-C', lpath]
    m.expect(expect)
    b.build_android_libraries([l])
    b.verbose = True
    expect.append('V=1')
    m.expect(expect)
    b.build_android_libraries([l])
    expect.append('NDK_OUT=%s' % lpath)
    m.expect(expect)
    b.build_android_libraries([l], output=l)
    b.make_flags = '-DFOO -DBAR -DBAZ'
    flaglist = ['-DFOO', '-DBAR', '-DBAZ']
    expect += flaglist
    m.expect(expect)
    b.build_android_libraries([l], output=l)
    b.ndk_home = '/dev/null'
    with self.assertRaises(common.ToolPathError):
      b.build_android_libraries([l], output=l)
      b._parse(f)

  def test_clean_libraries(self):
    d = android.BuildEnvironment.build_defaults()
    b = android.BuildEnvironment(d)
    b.clean = True
    m = common_test.RunCommandMock(self)
    b.run_subprocess = m
    ndk_build = os.path.join(b.ndk_home, 'ndk-build')
    l = 'libfoo'
    lpath = os.path.abspath(os.path.join(b.project_directory, l))
    expect = [ndk_build, '-j' + str(platform.mac_ver()[0] and 1 or
                                    b.cpu_count),
              '-C', lpath, 'clean']
    m.expect(expect)
    b.build_android_libraries([l])
    b.verbose = True
    expect.append('V=1')
    m.expect(expect)
    b.build_android_libraries([l])
    expect.append('NDK_OUT=%s' % lpath)
    m.expect(expect)
    b.build_android_libraries([l], output=l)
    b.make_flags = '-DFOO -DBAR -DBAZ'
    flaglist = ['-DFOO', '-DBAR', '-DBAZ']
    expect += flaglist
    m.expect(expect)
    b.build_android_libraries([l], output=l)
    b.ndk_home = '/dev/null'
    with self.assertRaises(common.ToolPathError):
      b.build_android_libraries([l], output=l)
      b._parse(f)

  def test_find_android_sdk(self):
    d = android.BuildEnvironment.build_defaults()
    b = android.BuildEnvironment(d)
    m = common_test.RunCommandMock(self)
    b.run_subprocess = m
    expect = ['android', 'list', 'target', '--compact']
    m.expect(expect)
    m.returns('android-3\n'
              'android-5\n'
              'meaningless\n'
              'android-10\n'
              'android-L\n')
    got = b._find_best_android_sdk('android', 1, 5)
    self.assertEqual(got, 'android-5')
    got = b._find_best_android_sdk('android', 5, 15)
    self.assertEqual(got, 'android-10')
    got = b._find_best_android_sdk('android', 1, 2)
    self.assertEqual(got, 'android-10')
    with self.assertRaises(common.ConfigurationError):
      b._find_best_android_sdk('android', 11, 20)
    m.returns('android-10\n'
              'android-15\n'
              'android-7\n')
    got = b._find_best_android_sdk('android', 5, 15)
    self.assertEqual(got, 'android-15')

  def _build_all_test_setup(self):
    d = android.BuildEnvironment.build_defaults()
    b = android.BuildEnvironment(d)
    apk_mock = BuildAndroidAPKMock(self)
    lib_mock = BuildAndroidLibrariesMock(self)
    b.build_android_libraries = lib_mock.verify
    b.build_android_apk = apk_mock.verify
    walk_mock = OsWalkMock(self)
    os.walk = walk_mock.walk
    return (b, apk_mock, lib_mock, walk_mock)

  def test_build_all_trivial(self):
    (b, apk_mock, lib_mock, walk_mock) = self._build_all_test_setup()
    project = b.project_directory
    tree = FileNode(project)
    jni = tree.add_subdir('jni')
    jni.add_files(['Android.mk', 'Application.mk'])
    walk_mock.expect(project)
    walk_mock.set_root(tree)
    lib_mock.expect([tree.name])
    apk_mock.fail()  # should not be called
    b.build_all()

  def test_build_all_exclude(self):
    (b, apk_mock, lib_mock, walk_mock) = self._build_all_test_setup()
    project = b.project_directory
    tree = FileNode(project)
    jni = tree.add_subdir('jni')
    jni.add_files(['Android.mk', 'Application.mk'])
    fooz = tree.add_subdir('fooz')
    fooz.add_files(['Android.mk', 'Application.mk'])
    walk_mock.expect(project)
    walk_mock.set_root(tree)
    lib_mock.expect([tree.name])  # should not pass fooz
    apk_mock.fail()  # should not be called
    b.build_all(exclude_dirs=['fooz'])

  def test_build_all_exclude_defaults(self):
    (b, apk_mock, lib_mock, walk_mock) = self._build_all_test_setup()
    project = b.project_directory
    tree = FileNode(project)
    jni = tree.add_subdir('jni')
    jni.add_files(['Android.mk', 'Application.mk'])
    for name in ['apks', 'libs', 'bin', 'obj', 'res']:
      n = tree.add_subdir(name)
      n.add_files(['Android.mk', 'Application.mk'])
    walk_mock.expect(project)
    walk_mock.set_root(tree)
    lib_mock.expect([tree.name])  # should not pass any of the default excludes
    apk_mock.fail()  # should not be called
    b.build_all()

  def test_build_all_even_more_trivial(self):
    (b, apk_mock, lib_mock, walk_mock) = self._build_all_test_setup()
    project = b.project_directory
    tree = FileNode(project)
    tree.add_files(['Android.mk'])  # test handling top level Android.mk
    walk_mock.expect(project)
    walk_mock.set_root(tree)
    lib_mock.expect([tree.name])
    apk_mock.fail()  # should not be called
    b.build_all()

  def test_build_all_app(self):
    (b, apk_mock, lib_mock, walk_mock) = self._build_all_test_setup()
    project = b.project_directory
    tree = FileNode(project)
    tree.add_files(['AndroidManifest.xml'])
    jni = tree.add_subdir('jni')
    jni.add_files(['Android.mk', 'Application.mk'])
    walk_mock.expect(project)
    walk_mock.set_root(tree)
    lib_mock.expect([])
    apk_mock.expect(tree.name)
    b.build_all()

  def test_build_all_both(self):
    (b, apk_mock, lib_mock, walk_mock) = self._build_all_test_setup()
    project = b.project_directory
    tree = FileNode(project)
    app = tree.add_subdir('app')
    app.add_files(['AndroidManifest.xml'])
    jni = app.add_subdir('jni')
    jni.add_files(['Android.mk', 'Application.mk'])
    src = tree.add_subdir('src')
    jni = src.add_subdir('jni')
    jni.add_files(['Android.mk', 'Application.mk'])
    walk_mock.expect(project)
    walk_mock.set_root(tree)
    lib_mock.expect([src.name])
    apk_mock.expect(app.name)
    b.build_all()


if __name__ == '__main__':
  unittest.main()
