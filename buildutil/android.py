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

"""Android-specific BuildEnvironment sub-module.

Optional environment variables:

ANT_PATH = Path to ant binary. Required if ant is not in $PATH,
or not passed on command line.
ANDROID_SDK_HOME = Path to the Android SDK. Required if it is not passed on the
command line.
NDK_HOME = Path to the Android NDK. Required if it is not in passed on the
command line.
"""

import distutils.spawn
import errno
import os
import random
import shlex
import shutil
import stat
import xml.etree.ElementTree
import buildutil.common as common
import re

_SDK_HOME_ENV_VAR = 'ANDROID_SDK_HOME'
_NDK_HOME_ENV_VAR = 'NDK_HOME'
_SDK_HOME = 'sdk_home'
_NDK_HOME = 'ndk_home'
_ANT_PATH_ENV_VAR = 'ANT_PATH'
_ANT_PATH = 'ant_path'
_ANT_FLAGS = 'ant_flags'
_ANT_TARGET = 'ant_target'
_APK_KEYSTORE = 'apk_keystore'
_APK_PASSFILE = 'apk_passfile'
_APK_KEYALIAS = 'apk_keyalias'
_SIGN_APK = 'sign_apk'
_MANIFEST_FILE = 'AndroidManifest.xml'
_NDK_MAKEFILE = 'Android.mk'

_MATCH_DEVICES = re.compile(r'^(List of devices attached\s*\n)|(\n)$')


class XMLFile(object):
  """XML file base class factored for testability.

  Subclasses implement process(self, etree) to process the parsed XML.
  On error, they should raise common.ConfigurationError.

  Attributes:
    path: Path to XML file as set in initializer.
  """

  def __init__(self, path):
    """Constructs the XMLFile for a specified path.

    Args:
      path: The absolute path to the manifest file.

    Raises:
      ConfigurationError: Manifest file missing.
    """
    if path and not os.path.exists(path):
      raise common.ConfigurationError(path, os.strerror(errno.ENOENT))

    self.path = path

  def parse(self):
    """Parse the XML file and extract useful information.

    Raises:
      ConfigurationError: Elements were missing or incorrect in the file.
      IOError: Could not open XML file.
    """
    with open(self.path, 'r') as xmlfile:
      self._parse(xmlfile)

  def _parse(self, xmlfile):
    try:
      etree = xml.etree.ElementTree.parse(xmlfile)
      self.process(etree)
    except xml.etree.ElementTree.ParseError as pe:
      raise common.ConfigurationError(self.path, 'XML parse error: ' + str(pe))


class AndroidManifest(XMLFile):

  """Class that extracts build information from an AndroidManifest.xml.

  Attributes:
    min_sdk: Minimum SDK version from the uses-sdk element.
    target_sdk: Target SDK version from the uses-sdk element, or min_sdk if it
      is not set.
    package_name: Name of the package.
    activity_name: Name of the activity from the android:name element.
  """

  def __init__(self, path):
    """Constructs the AndroidManifest for a specified path.

    Args:
      path: The absolute path to the manifest file.

    Raises:
      ConfigurationError: Manifest file missing.
    """
    super(AndroidManifest, self).__init__(path)

    self.min_sdk = 0
    self.target_sdk = 0
    self.package_name = ''
    self.activity_name = ''

  def process(self, etree):
    """Process the parsed AndroidManifest to extract SDK version info.

    Args:
      etree: An xml.etree.ElementTree object of the parsed XML file.

    Raises:
      ConfigurationError: Required elements were missing or incorrect.
    """
    root = etree.getroot()

    self.package_name = root.get('package')

    sdk_element = root.find('uses-sdk')

    if sdk_element is None:
      raise common.ConfigurationError(self.path, 'uses-sdk element missing')

    min_sdk_version = sdk_element.get(
        '{http://schemas.android.com/apk/res/android}minSdkVersion')
    target_sdk_version = sdk_element.get(
        '{http://schemas.android.com/apk/res/android}targetSdkVersion')

    app_element = root.find('application')
    if app_element is None:
      raise common.ConfigurationError(self.path, 'application missing')
    activity_element = app_element.find('activity')
    if activity_element is None:
      raise common.ConfigurationError(self.path, 'activity missing')

    self.activity_name = activity_element.get(
        '{http://schemas.android.com/apk/res/android}name')

    if not min_sdk_version:
      raise common.ConfigurationError(self.path, 'minSdkVersion missing')
    if not target_sdk_version:
      target_sdk_version = min_sdk_version
    if not self.package_name:
      raise common.ConfigurationError(self.path, 'package missing')
    if not self.activity_name:
      raise common.ConfigurationError(self.path,
                                      'activity android:name missing')

    self.min_sdk = int(min_sdk_version)
    self.target_sdk = int(target_sdk_version)


class BuildXml(XMLFile):

  """Class that extracts build information from an ant build.xml.

  Attributes:
    project_name: The name of the project, used by ant to name output files.
  """

  def __init__(self, path):
    """Constructs the BuildXml for a specified path.

    Args:
      path: The absolute path to the build.xml file.

    Raises:
      ConfigurationError: build.xml file missing.
    """
    super(BuildXml, self).__init__(path)

    self.project_name = None

  def process(self, etree):
    """Process the parsed build.xml to extract project info.

    Args:
      etree: An xml.etree.ElementTree object of the parsed XML file.

    Raises:
      ConfigurationError: Required elements were missing or incorrect.
    """
    project_element = etree.getroot()

    if project_element.tag != 'project':
      raise common.ConfigurationError(self.path, 'project element missing')

    self.project_name = project_element.get('name')

    if not self.project_name:
      raise common.ConfigurationError(self.path, 'project name missing')


class BuildEnvironment(common.BuildEnvironment):

  """Class representing an Android build environment.

  This class adds Android-specific functionality to the common
  BuildEnvironment.

  Attributes:
    ndk_home: Path to the Android NDK, if found.
    sdk_home: Path to the Android SDK, if found.
    ant_path: Path to the ant binary, if found.
    ant_flags: Flags to pass to the ant binary, if used.
    ant_target: Ant build target name.
    sign_apk: Enable signing of Android APKs.
    apk_keystore: Keystore file path to use when signing an APK.
    apk_keyalias: Alias of key to use when signing an APK.
    apk_passfile: Path to file containing a password to use when signing an
      APK.
  """

  def __init__(self, arguments):
    """Constructs the BuildEnvironment with basic information needed to build.

    The build properties as set by argument parsing are also available
    to be modified by code using this object after construction.

    It is required to call this function with a valid arguments object,
    obtained either by calling argparse.ArgumentParser.parse_args() after
    adding this modules arguments via BuildEnvironment.add_arguments(), or
    by passing in an object returned from BuildEnvironment.build_defaults().

    Args:
      arguments: The argument object returned from ArgumentParser.parse_args().
    """

    super(BuildEnvironment, self).__init__(arguments)

    if type(arguments) is dict:
      args = arguments
    else:
      args = vars(arguments)

    self.ndk_home = args[_NDK_HOME]
    self.sdk_home = args[_SDK_HOME]
    self.ant_path = args[_ANT_PATH]
    self.ant_flags = args[_ANT_FLAGS]
    self.ant_target = args[_ANT_TARGET]
    self.sign_apk = args[_SIGN_APK]
    self.apk_keystore = args[_APK_KEYSTORE]
    self.apk_keyalias = args[_APK_KEYALIAS]
    self.apk_passfile = args[_APK_PASSFILE]

  @staticmethod
  def build_defaults():
    """Helper function to set build defaults.

    Returns:
      A dict containing appropriate defaults for a build.
    """
    args = common.BuildEnvironment.build_defaults()

    args[_SDK_HOME] = (os.getenv(_SDK_HOME_ENV_VAR) or
                       common.BuildEnvironment._find_path_from_binary(
                           'android', 2))
    args[_NDK_HOME] = (os.getenv(_NDK_HOME_ENV_VAR) or
                       common.BuildEnvironment._find_path_from_binary(
                           'ndk-build', 1))
    args[_ANT_PATH] = (os.getenv(_ANT_PATH_ENV_VAR) or
                       distutils.spawn.find_executable('ant'))
    args[_ANT_FLAGS] = '-quiet'
    args[_ANT_TARGET] = 'release'
    args[_APK_KEYSTORE] = None
    args[_APK_KEYALIAS] = None
    args[_APK_PASSFILE] = None
    args[_SIGN_APK] = False

    return args

  @staticmethod
  def add_arguments(parser):
    """Add module-specific command line arguments to an argparse parser.

    This will take an argument parser and add arguments appropriate for this
    module. It will also set appropriate default values.

    Args:
      parser: The argparse.ArgumentParser instance to use.
    """
    defaults = BuildEnvironment.build_defaults()

    common.BuildEnvironment.add_arguments(parser)

    parser.add_argument('-n', '--' + _NDK_HOME,
                        help='Path to Android NDK', dest=_NDK_HOME,
                        default=defaults[_NDK_HOME])
    parser.add_argument('-s', '--' + _SDK_HOME,
                        help='Path to Android SDK', dest=_SDK_HOME,
                        default=defaults[_SDK_HOME])
    parser.add_argument('-a', '--' + _ANT_PATH,
                        help='Path to ant binary', dest=_ANT_PATH,
                        default=defaults[_ANT_PATH])
    parser.add_argument('-A', '--' + _ANT_FLAGS,
                        help='Flags to use to override ant flags',
                        dest=_ANT_FLAGS, default=defaults[_ANT_FLAGS])
    parser.add_argument('-T', '--' + _ANT_TARGET,
                        help='Target to use for ant build',
                        dest=_ANT_TARGET, default=defaults[_ANT_TARGET])
    parser.add_argument('-k', '--' + _APK_KEYSTORE,
                        help='Path to keystore to use when signing an APK',
                        dest=_APK_KEYSTORE, default=defaults[_APK_KEYSTORE])
    parser.add_argument('-K', '--' + _APK_KEYALIAS,
                        help='Key alias to use when signing an APK',
                        dest=_APK_KEYALIAS, default=defaults[_APK_KEYALIAS])
    parser.add_argument('-P', '--' + _APK_PASSFILE,
                        help='Path to file containing keystore password',
                        dest=_APK_PASSFILE, default=defaults[_APK_PASSFILE])
    parser.add_argument(
        '-S', '--' + _SIGN_APK,
        help='Enable signing of Android APKs',
        dest=_SIGN_APK, action='store_true', default=defaults[_SIGN_APK])

  def build_android_libraries(self, subprojects, output=None):
    """Build list of Android library projects.

    This function iteratively runs ndk-build over a list of paths relative
    to the current project directory.

    Args:
      subprojects: A list pf paths relative to the project directory to build.
      output: An optional directory relative to the project directory to
          receive the build output.

    Raises:
      SubCommandError: ndk-build invocation failed or returned an error.
      ToolPathError: Android NDK location not found in configured build
          environment or $PATH.
    """
    ndk_build = None
    if self.ndk_home:
      ndk_build = os.path.join(self.ndk_home, 'ndk-build')
    common.BuildEnvironment._check_binary('ndk-build', ndk_build)

    for p in subprojects:
      args = [ndk_build, '-B', '-j', self.cpu_count,
              '-C', os.path.abspath(os.path.join(self.project_directory, p))]

      if self.verbose:
        args.append('V=1')

      if output:
        args.append(
            'NDK_OUT=%s' % os.path.abspath(
                os.path.join(self.project_directory, output)))

      if self.make_flags:
        args += shlex.split(self.make_flags, posix=self._posix)

      self.run_subprocess(args)

  def _find_best_android_sdk(self, android, minsdk, target):
    """Finds the best installed Android SDK for a project.

    Based on the passed in min and target SDK levels, find the highest SDK
    level installed that is greater than the specified minsdk, up to the
    target sdk level. Return it as an API level string.

    Otherwise, if the minimum installed SDK is greater than the
    targetSdkVersion, return the maximum installed SDK version, or raise a
    ConfigurationError if no installed SDK meets the min SDK.

    Args:
      android: Path to android tool binary.
      minsdk: Integer minimum SDK level.
      target: Integer target SDK level.

    Returns:
      Highest installed Android SDK API level in the range, as a string.

    Raises:
      SubCommandError: NDK toolchain invocation failed or returned an error.
      ToolPathError: Android NDK or SDK location not found in configured build
          environment or $PATH, or ant not found.
      ConfigurationError: Required build configuration file missing or broken
          in an unrecoverable way.
    """
    acmd = [android, 'list', 'target', '--compact']
    (stdout, unused_stderr) = self.run_subprocess(acmd, capture=True)

    if self.verbose:
      print 'android list target returned: {%s}' % (stdout)
    # Find the highest installed SDK <= targetSdkVersion, if possible.
    #
    # 'android list target --compact' will output lines like:
    #
    # android-1
    # android-2
    #
    # for installed SDK targets, along with other info not starting with
    # android-.
    installed = 0
    for line in stdout.splitlines():
      l = line.strip()
      if l.startswith('android-'):
        nstr = l.split('-')[1]
        n = (int(nstr))
        if n > installed:
          if self.verbose:
            print 'sdk api level %d found' % (n)
          installed = n
        if installed == target:
          break

    if installed < minsdk:
      raise common.ConfigurationError(self.sdk_home,
                                      ('Project requires Android SDK %d, '
                                       'but only found up to %d' %
                                       (minsdk, installed)))

    apitarget = 'android-%d' % (installed)
    return apitarget

  def build_android_apk(self, path='.', output=None):
    """Build an Android APK.

    This function builds an APK by using ndk-build and ant, at an optionally
    specified relative path from the current project directory, and output to
    an optionally specified output directory, also relative to the current
    project directory. Flags are passed to ndk-build and ant as specified in
    the build environment. This function does not install the resulting APK.

    If no build.xml is found, one is generated via the 'android' command, if
    possible.

    Args:
      path: Optional relative path from project directory to project to build.
      output: Optional relative path from project directory to output
        directory.

    Raises:
      SubCommandError: NDK toolchain invocation failed or returned an error.
      ToolPathError: Android NDK or SDK location not found in configured build
          environment or $PATH, or ant not found.
      ConfigurationError: Required build configuration file missing or broken
          in an unrecoverable way.
      IOError: An error occurred writing or copying the APK.
    """
    ant = self.ant_path
    common.BuildEnvironment._check_binary('ant', ant)

    android = os.path.join(self.sdk_home, 'tools', 'android')
    common.BuildEnvironment._check_binary('android', android)

    self.build_android_libraries([path])

    project = os.path.abspath(os.path.join(self.project_directory, path))

    manifest_path = os.path.join(project, _MANIFEST_FILE)

    manifest = AndroidManifest(manifest_path)
    manifest.parse()

    buildxml_path = os.path.join(project, 'build.xml')

    app_name = ''

    # If no build.xml exists, create one for the project in the directory
    # we are currently building.
    if not os.path.exists(buildxml_path):
      app_name = os.path.basename(project) + '_app'
      apitarget = self._find_best_android_sdk(android, manifest.min_sdk,
                                              manifest.target_sdk)
      acmd = [android, 'update', 'project', '--path', project,
              '--target', apitarget, '--name', app_name]
      self.run_subprocess(acmd)

    buildxml = BuildXml(buildxml_path)
    buildxml.parse()

    # Set to value in build.xml, which may have just been updated
    app_name = buildxml.project_name

    acmd = [ant, self.ant_target]

    if self.ant_flags:
      acmd += shlex.split(self.ant_flags, posix=self._posix)

    self.run_subprocess(acmd, cwd=path)

    # ant outputs to $PWD/bin. The APK will have a name as constructed below.
    apkname = '%s-%s-unsigned.apk' % (app_name, self.ant_target)
    apkpath = os.path.join(project, 'bin', apkname)
    source_apkpath = apkpath

    if self.sign_apk:
      signed_apkname = '%s.apk' % app_name
      signed_apkpath = os.path.join(project, 'bin', signed_apkname)
      source_apkpath = signed_apkpath
      self._sign_apk(apkpath, signed_apkpath)

    if output:
      out_abs = os.path.abspath(os.path.join(self.project_directory, output))
      if not os.path.exists(out_abs):
        os.makedirs(out_abs)
      if self.verbose:
        print 'Copying apk %s to: %s' % (source_apkpath, out_abs)
      shutil.copy2(source_apkpath, out_abs)

  def _sign_apk(self, source, target):
    """This function signs an Android APK, optionally generating a key.

    This function signs an APK using a keystore and password as configured
    in the build configuration. If none are configured, it generates an
    ephemeral key good for 60 days.

    Args:
      source: Absolute path to source APK to sign.
      target: Target path to write signed APK to.

    Raises:
      SubCommandError: Jarsigner invocation failed or returned an error.
      ToolPathError: Jarsigner or keygen location not found in $PATH.
      ConfigurationError: User specified some but not all signing parameters.
      IOError: An error occurred copying the APK.
    """
    # Debug targets are automatically signed and aligned by ant.
    if self.ant_target is 'debug':
      return

    # If any of keystore, passwdfile, or alias are None we will create a
    # temporary keystore with a random password and alias and remove it after
    # signing. This facilitates testing release builds when the release
    # keystore is not available (such as in a continuous testing environment).
    keystore = self.apk_keystore
    passfile = self.apk_passfile
    alias = self.apk_keyalias
    ephemeral = False

    try:
      if not keystore or not passfile or not alias:
        # If the user specifies any of these, they need to specify them all,
        # otherwise we may overwrite one of them.
        if keystore:
          raise common.ConfigurationError(keystore,
                                          ('Must specify all of keystore, '
                                           'password file, and alias'))
        if passfile:
          raise common.ConfigurationError(passfile,
                                          ('Must specify all of keystore, '
                                           'password file, and alias'))
        if alias:
          raise common.ConfigurationError(alias,
                                          ('Must specify all of keystore, '
                                           'password file, and alias'))
        ephemeral = True
        keystore = source + '.keystore'
        passfile = source + '.password'
        if self.verbose:
          print ('Creating ephemeral keystore file %s and password file %s' %
                 (keystore, passfile))
        with open(passfile, 'w') as pf:
          os.fchmod(pf.fileno(), stat.S_IRUSR | stat.S_IWUSR)
          pf.write('%08x' % (random.random() * 16 ** 8))

        alias = os.path.basename(source).split('.')[0]
        keytool = distutils.spawn.find_executable('keytool')
        common.BuildEnvironment._check_binary('keytool', keytool)
        acmd = ['keytool', '-genkey', '-v', '-dname',
                'cn=, ou=%s, o=fpl' % (alias), '-storepass:file', passfile,
                '-keypass:file', passfile, '-keystore', keystore, '-alias',
                alias, '-keyalg', 'RSA', '-keysize', '2048', '-validity', '60']
        self.run_subprocess(acmd)

      tmpapk = target + '.tmp'

      if self.verbose:
        print 'Copying APK %s for signing as %s' % (source, tmpapk)

      shutil.copy2(source, tmpapk)

      acmd = ['jarsigner', '-verbose', '-sigalg', 'SHA1withRSA', '-digestalg',
              'SHA1', '-keystore', keystore, '-storepass:file', passfile,
              '-keypass:file', passfile, tmpapk, alias]

      self.run_subprocess(acmd)

      # We want to align the APK for more efficient access on the device.
      # See:
      # http://developer.android.com/tools/help/zipalign.html
      zipalign = os.path.join(self.sdk_home, 'tools', 'zipalign')
      BuildEnvironment._check_binary('zipalign', zipalign)

      acmd = [zipalign, '-f']
      if self.verbose:
        acmd.append('-v')
      acmd += ['4', tmpapk, target]  # alignment == 4
      self.run_subprocess(acmd)

    finally:
      if ephemeral:
        if self.verbose:
          print 'Removing ephemeral keystore and password files'
        if os.path.exists(keystore):
          os.unlink(keystore)
        if os.path.exists(passfile):
          os.unlink(passfile)

  def build_all(self, path='.', apk_output='apks', lib_output='libs',
                exclude_dirs=None):
    """Locate and build all Android sub-projects as appropriate.

    This function will recursively scan a directory tree for Android library
    and application projects and build them with the current build defaults.
    This will not work for projects which only wish for subsets to be built
    or have complicated external manipulation of makefiles and manifests, but
    it should handle the majority of projects as a reasonable default build.

    Args:
      path: Optional path to start the search in, defaults to '.'.
      apk_output: Optional path to apk output directory, default is 'apks'.
      lib_output: Optional path to library output directory, default is 'libs'.
      exclude_dirs: Optional list of directory names to exclude from project
                    detection in addition to:
                    [apk_output, lib_output, 'bin', 'obj', 'res'],
                    which are always excluded.
    Returns:
      (retval, errmsg) tuple of an integer return value suitable for returning
      to the invoking shell, and an error string (if any) or None (on success).
    """

    retval = 0
    errmsg = None
    project = os.path.abspath(os.path.join(self.project_directory, path))

    apk_dir_set = set()
    module_dir_set = set()

    # Exclude paths where buildutil or ndk-build may generate or copy files.
    exclude = [apk_output, lib_output, 'bin', 'obj', 'res']

    if type(exclude_dirs) is list:
      exclude += exclude_dirs

    for root, dirs, files in os.walk(project):
      for ex in exclude:
        if ex in dirs:
          dirs.remove(ex)
      if _MANIFEST_FILE in files:
        apk_dir_set.add(root)
      if _NDK_MAKEFILE in files:
        p = root
        # Handle the use or nonuse of the jni subdir.
        if os.path.basename(p) == 'jni':
          p = os.path.dirname(p)
        module_dir_set.add(p)

    # Set difference, remove anything in apks from libs.
    module_dir_set = module_dir_set.difference(apk_dir_set)

    apk_dirs = list(apk_dir_set)
    lib_dirs = list(module_dir_set)

    if self.verbose:
      print 'Found APK projects in: %s' % str(apk_dirs)
      print 'Found library projects in: %s' % str(lib_dirs)

    try:
      self.build_android_libraries(lib_dirs, output=lib_output)
      for apk in apk_dirs:
        self.build_android_apk(path=apk, output=apk_output)
      retval = 0

    except common.Error as e:
      errmsg = 'Caught buildutil error: %s' % e.error_message
      retval = e.error_code

    except IOError as e:
      errmsg = 'Caught IOError for file %s: %s' % (e.filename, e.strerror)
      retval = -1

    return (retval, errmsg)

  def _check_adb_devices(self):
    """Verifies that only one device is connected.

    Raises:
      AdbError: Incorrect number of connected devices.
    """
    out = self.run_subprocess('adb devices -l', capture=True, shell=True)[0]

    number_of_devices = len(_MATCH_DEVICES.sub(r'', out).splitlines())

    if number_of_devices == 0:
      raise AdbError('No Android devices are connected to this host.');

    if number_of_devices > 1:
      raise AdbError(
        'Multiple Android devices are connected to this host. '
        'Please specify a device using --adb-device <serial>. '
        'The devices connected are: %s' % (os.linesep + out))

  def run_android_apk(self, adb_device=None, wait=True):
    """Run an android apk on the given device.

    Args:
      adb_device: The device to run the apk on. If none it will use the only
        device connected.
      wait: Optional argument to tell the function to wait until the process
        completes and dump the output.
    """
    project = os.path.abspath(self.project_directory)
    manifest_path = os.path.join(project, 'AndroidManifest.xml')

    manifest = AndroidManifest(manifest_path)
    manifest.parse()

    full_name = "%s/%s" % (manifest.package_name, manifest.activity_name)
    if not adb_device:
      self._check_adb_devices()
      adb_device = ''

    self.run_subprocess('adb %s logcat -c' % adb_device, shell=True)

    self.run_subprocess(
      ('adb %s shell am start -S -n %s' % (adb_device, full_name)), shell=True)

    end_match = re.compile((r'.*(Displayed|Activity destroy timeout).*%s.*' %
                            full_name))

    while wait:
      # Use logcat -d so that it can be parsed easily in order to determine
      # when the process ends. An alternative is to read the stream as it gets
      # written but this leads to delays in reading the stream and is difficult
      # to get working propery on windows.
      out, err = self.run_subprocess( ('adb %s logcat -d' % adb_device),
                                     capture=True, shell=True)

      for line in out.splitlines():
        if end_match.match(line):
          print out
          wait = False
