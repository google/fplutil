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
import platform
import random
import re
import shlex
import shutil
import stat
import sys
import xml.etree.ElementTree
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir))
import buildutil.common as common

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
_ALWAYS_MAKE = 'always_make'

_MATCH_DEVICES = re.compile(r'^(List of devices attached\s*\n)|(\n)$')
_MATCH_PACKAGE = re.compile(r'^package:(.*)')

_NATIVE_ACTIVITY = 'android.app.NativeActivity'
_ANDROID_MANIFEST_SCHEMA = 'http://schemas.android.com/apk/res/android'


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
    lib_name: Name of the library loaded by android.app.NativeActivity.
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
    self.lib_name = ''

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

    min_sdk_version = AndroidManifest.__get_schema_attribute_value(
        sdk_element, 'minSdkVersion')
    target_sdk_version = AndroidManifest.__get_schema_attribute_value(
        sdk_element, 'targetSdkVersion')

    app_element = root.find('application')
    if app_element is None:
      raise common.ConfigurationError(self.path, 'application missing')
    activity_element = app_element.find('activity')
    if activity_element is None:
      raise common.ConfigurationError(self.path, 'activity missing')

    self.activity_name = AndroidManifest.__get_schema_attribute_value(
        activity_element, 'name')

    if not min_sdk_version:
      raise common.ConfigurationError(self.path, 'minSdkVersion missing')
    if not target_sdk_version:
      target_sdk_version = min_sdk_version
    if not self.package_name:
      raise common.ConfigurationError(self.path, 'package missing')
    if not self.activity_name:
      raise common.ConfigurationError(self.path,
                                      'activity android:name missing')

    if self.activity_name == _NATIVE_ACTIVITY:
      for metadata_element in activity_element.findall('meta-data'):
        if (AndroidManifest.__get_schema_attribute_value(
            metadata_element, 'name') == 'android.app.lib_name'):
          self.lib_name = AndroidManifest.__get_schema_attribute_value(
              metadata_element, 'value')

      if not self.lib_name:
        raise common.ConfigurationError(
            self.path, 'meta-data android.app.lib_name missing')

    self.min_sdk = int(min_sdk_version)
    self.target_sdk = int(target_sdk_version)

  @staticmethod
  def __get_schema_attribute_value(xml_element, attribute):
    """Get attribute from xml_element using the Android manifest schema.

    Args:
      xml_element: xml.etree.ElementTree to query.
      attribute: Name of Android Manifest attribute to retrieve.

    Returns:
      XML attribute string from the specified element.
    """
    return xml_element.get('{%s}%s' % (_ANDROID_MANIFEST_SCHEMA, attribute))


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

  ADB = 'adb'
  ANDROID = 'android'
  ANT = 'ant'
  JARSIGNER = 'jarsigner'
  KEYTOOL = 'keytool'
  NDK_BUILD = 'ndk-build'
  ZIPALIGN = 'zipalign'

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
    self.always_make = args[_ALWAYS_MAKE]

  @staticmethod
  def build_defaults():
    """Helper function to set build defaults.

    Returns:
      A dict containing appropriate defaults for a build.
    """
    args = common.BuildEnvironment.build_defaults()

    args[_SDK_HOME] = (os.getenv(_SDK_HOME_ENV_VAR) or
                       common.BuildEnvironment._find_path_from_binary(
                           BuildEnvironment.ANDROID, 2))
    args[_NDK_HOME] = (os.getenv(_NDK_HOME_ENV_VAR) or
                       common.BuildEnvironment._find_path_from_binary(
                           BuildEnvironment.NDK_BUILD, 1))
    args[_ANT_PATH] = (os.getenv(_ANT_PATH_ENV_VAR) or
                       distutils.spawn.find_executable(BuildEnvironment.ANT))
    args[_ANT_FLAGS] = '-quiet'
    args[_ANT_TARGET] = 'release'
    args[_APK_KEYSTORE] = None
    args[_APK_KEYALIAS] = None
    args[_APK_PASSFILE] = None
    args[_SIGN_APK] = False
    args[_ALWAYS_MAKE] = False

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
    parser.add_argument('-S', '--' + _SIGN_APK,
                        help='Enable signing of Android APKs',
                        dest=_SIGN_APK, action='store_true',
                        default=defaults[_SIGN_APK])
    parser.add_argument('-B', '--' + _ALWAYS_MAKE,
                        help='Always build all up to date targets.',
                        dest=_ALWAYS_MAKE, action='store_true')
    parser.add_argument('--no-' + _ALWAYS_MAKE,
                        help='Only build out of date targets.',
                        dest=_ALWAYS_MAKE, action='store_false')
    parser.set_defaults(
        **{_ALWAYS_MAKE: defaults[_ALWAYS_MAKE]})  # pylint: disable=star-args

  def _find_binary(self, binary, additional_paths=None):
    """Find a binary from the set of binaries managed by this class.

    This method enables the lookup of a binary path using the name of the
    binary to avoid replication of code which searches for binaries.

    This class allows the lookup of...
    * BuildEnvironment.ADB
    * BuildEnvironment.ANDROID
    * BuildEnvironment.ANT
    * BuildEnvironment.JARSIGNER
    * BuildEnvironment.KEYTOOL
    * BuildEnvironment.NDK_BUILD
    * BuildEnvironment.ZIPALIGN

    The _find_binary() method in derived classes may add more binaries.

    Args:
      binary: Name of the binary.
      additional_paths: Additional dictionary to search for binary paths.

    Returns:
      String containing the path of binary.

    Raises:
      ToolPathError: Binary is not at the specified path.
    """
    ndk_build_paths = []
    if self.ndk_home:
      ndk_build_paths = [os.path.join(self.ndk_home, '')]

    # zipalign is under the sdk/build-tools subdirectory in ADT 20140702
    # or newer.  In older ADT releases zipalign was located in sdk/tools.
    zip_align_paths = []
    if binary == BuildEnvironment.ZIPALIGN:
      zip_align_paths = [os.path.join(self.sdk_home, 'tools', '')]
      for root, dirs, _ in os.walk(os.path.join(self.sdk_home, 'build-tools')):
        zip_align_paths.extend([os.path.join(root, d, '') for d in dirs])
        break

    search_dict = {
        BuildEnvironment.ADB: [os.path.join(
            self.sdk_home, 'platform-tools', '')],
        BuildEnvironment.ANDROID: [
            os.path.join(self.sdk_home, 'tools', '')],
        BuildEnvironment.ANT: [self.ant_path],
        BuildEnvironment.NDK_BUILD: ndk_build_paths,
        BuildEnvironment.JARSIGNER: [],
        BuildEnvironment.KEYTOOL: [],
        BuildEnvironment.ZIPALIGN: zip_align_paths}
    if additional_paths:
      search_dict.append(additional_paths)

    return common.BuildEnvironment._find_binary(self, binary, search_dict)

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
    ndk_build = self._find_binary(BuildEnvironment.NDK_BUILD)

    for p in subprojects:
      # Disable parallel clean on OSX.
      cpu_count = self.cpu_count
      if self.clean and platform.mac_ver()[0]:
        cpu_count = 1

      args = [ndk_build, '-j' + str(cpu_count)]
      if self.always_make:
        args.append('-B')
      args += ['-C', self.get_project_directory(path=p)]
      if self.clean:
        args.append('clean')

      if self.verbose:
        args.append('V=1')

      if output:
        args.append(
            'NDK_OUT=%s' % self.get_project_directory(path=output))

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
        # Ignore preview SDK revisions (e.g "L").
        if not nstr.isdigit():
          continue
        n = int(nstr)
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

  def get_manifest_path(self, path='.'):
    """Get the path of the manifest file.

    Args:
      path: Optional relative path from project directory to project to build.

    Returns:
      Path of the manifest file.
    """
    return os.path.join(self.get_project_directory(path=path), _MANIFEST_FILE)

  def parse_manifest(self, path='.'):
    """Parse the project's manifest.

    Args:
      path: Optional relative path from project directory to project to build.

    Returns:
      AndroidManifest instance parsed from the project manifest.
    """
    manifest = AndroidManifest(self.get_manifest_path(path=path))
    manifest.parse()
    return manifest

  def create_update_build_xml(self, manifest, path='.'):
    """Create or update ant build.xml for an Android project.

    Args:
      manifest: Parsed AndroidManifest instance.
      path: Optional relative path from project directory to project to build.

    Returns:
      BuildXml instance which references the created / updated ant project.
    """
    android = self._find_binary(BuildEnvironment.ANDROID)

    project = self.get_project_directory(path=path)
    buildxml_path = os.path.join(project, 'build.xml')

    # Get the last component of the package name for the application name.
    app_name = manifest.package_name[manifest.package_name.rfind('.') + 1:]

    # If no build.xml exists, create one for the project in the directory
    # we are currently building.
    if (not os.path.exists(buildxml_path) or
        os.path.getmtime(buildxml_path) < os.path.getmtime(manifest.path)):
      apitarget = self._find_best_android_sdk(android, manifest.min_sdk,
                                              manifest.target_sdk)
      self.run_subprocess([android, 'update', 'project', '--path', project,
                           '--target', apitarget, '--name', app_name])

    buildxml = BuildXml(buildxml_path)
    buildxml.parse()
    return buildxml

  def get_apk_filenames(self, app_name, path='.'):
    """Get the set of output APK names for the project.

    Args:
      app_name: Basename of the APK parsed from build.xml.
      path: Relative path from project directory to project to build.

    Returns:
      (signed_apkpath, unsigned_apkpath) where signed_apkpath and
      unsigned_apkpath are paths to the signed and unsigned APKs respectively.
      Signing is optional so the signed APK may not be present when the
      project has been built successfully.
    """
    # ant outputs to $PWD/bin. The APK will have a name as constructed below.
    project_directory = self.get_project_directory(path=path)
    apk_directory = os.path.join(project_directory, 'bin')
    if self.ant_target == 'debug':
      unsigned_apkpath = os.path.join(apk_directory, '%s-%s.apk' % (
          app_name, self.ant_target))
      signed_apkpath = unsigned_apkpath
    else:
      unsigned_apkpath = os.path.join(apk_directory, '%s-%s-unsigned.apk' % (
          app_name, self.ant_target))
      signed_apkpath = os.path.join(apk_directory, '%s.apk' % app_name)
    return (signed_apkpath, unsigned_apkpath)

  def build_android_apk(self, path='.', output=None, manifest=None):
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
      manifest: Parsed AndroidManifest instance.

    Raises:
      SubCommandError: NDK toolchain invocation failed or returned an error.
      ToolPathError: Android NDK or SDK location not found in configured build
          environment or $PATH, or ant not found.
      ConfigurationError: Required build configuration file missing or broken
          in an unrecoverable way.
      IOError: An error occurred writing or copying the APK.
    """
    ant = self._find_binary(BuildEnvironment.ANT)

    # Create or update build.xml for ant.
    buildxml = self.create_update_build_xml(
      manifest if manifest else self.parse_manifest(path=path),
      path=path)

    acmd = [ant, self.ant_target]

    if self.ant_flags:
      acmd += shlex.split(self.ant_flags, posix=self._posix)

    self.run_subprocess(acmd, cwd=path)

    signed_apkpath, unsigned_apkpath = self.get_apk_filenames(
        buildxml.project_name, path=path)
    source_apkpath = unsigned_apkpath

    if self.sign_apk:
      source_apkpath = signed_apkpath
      self._sign_apk(unsigned_apkpath, signed_apkpath)

    if output:
      out_abs = self.get_project_directory(path=output)
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

        password = '%08x' % (random.random() * 16 ** 8)
        with open(passfile, 'w') as pf:
          os.fchmod(pf.fileno(), stat.S_IRUSR | stat.S_IWUSR)
          pf.write(password)

        alias = os.path.basename(source).split('.')[0]

        # NOTE: The password is passed via the command line for compatibility
        # with JDK 6.  Move to use -storepass:file and -keypass:file when
        # JDK 7 is a requirement for Android development.
        acmd = [self._find_binary(BuildEnvironment.KEYTOOL), '-genkeypair',
                '-v', '-dname', 'cn=, ou=%s, o=fpl' % alias, '-storepass',
                password, '-keypass', password, '-keystore', keystore,
                '-alias', alias, '-keyalg', 'RSA', '-keysize', '2048',
                '-validity', '60']
        self.run_subprocess(acmd)

      tmpapk = target + '.tmp'

      if self.verbose:
        print 'Copying APK %s for signing as %s' % (source, tmpapk)

      shutil.copy2(source, tmpapk)

      with open(passfile, 'r') as pf:
        password = pf.read()

      # NOTE: The password is passed via stdin for compatibility with JDK 6
      # which - unlike the use of keytool above - ensures the password is
      # not visible when displaying the command lines of processes of *nix
      # operating systems like Linux and OSX.
      # Move to use -storepass:file and -keypass:file when JDK 7 is a
      # requirement for Android development.
      password_stdin = os.linesep.join(
          [password, password,  # Store password and confirmation.
           password, password])  # Key password and confirmation.
      acmd = [self._find_binary(BuildEnvironment.JARSIGNER),
              '-verbose', '-sigalg', 'SHA1withRSA', '-digestalg',
              'SHA1', '-keystore', keystore, tmpapk, alias]
      self.run_subprocess(acmd, stdin=password_stdin)

      # We want to align the APK for more efficient access on the device.
      # See:
      # http://developer.android.com/tools/help/zipalign.html
      acmd = [self._find_binary(BuildEnvironment.ZIPALIGN), '-f']
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

  def find_projects(self, path='.', exclude_dirs=None):
    """Find all Android projects under the specified path.

    Args:
      path: Path to start the search in, defaults to '.'.
      exclude_dirs: List of directory names to exclude from project
        detection in addition to ['bin', 'obj', 'res'], which are always
        excluded.

    Returns:
      (apk_dirs, lib_dirs) where apk_dirs is the list of directories which
      contain Android projects that build an APK and lib_dirs is alist of
      Android project directories that only build native libraries.
    """
    project = self.get_project_directory(path=path)

    apk_dir_set = set()
    module_dir_set = set()

    # Exclude paths where buildutil or ndk-build may generate or copy files.
    exclude = (exclude_dirs if exclude_dirs else []) + ['bin', 'obj', 'res']

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

    return (list(apk_dir_set), list(module_dir_set))

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
                    detection in addition to
                    [apk_output, lib_output, 'bin', 'obj', 'res'],
                    which are always excluded.
    Returns:
      (retval, errmsg) tuple of an integer return value suitable for returning
      to the invoking shell, and an error string (if any) or None (on success).
    """

    retval = 0
    errmsg = None

    apk_dirs, lib_dirs = self.find_projects(
        path=path, exclude_dirs=([apk_output, lib_output] + (
            exclude_dirs if exclude_dirs else [])))

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

  def check_adb_devices(self, adb_device=None):
    """Verifies that only one device is connected.

    Args:
      adb_device: If specified, check whether this device is connected.

    Raises:
      AdbError: Incorrect number of connected devices.
    """
    out = self.run_subprocess(
        '%s devices -l' % self._find_binary(BuildEnvironment.ADB),
        capture=True, shell=True)[0]

    devices = _MATCH_DEVICES.sub(r'', out).splitlines()
    number_of_devices = len(devices)

    if number_of_devices == 0:
      raise common.AdbError('No Android devices are connected to this host.')

    if adb_device:
      if not [l for l in devices if l.split()[0] == adb_device]:
        raise common.AdbError(
            '%s not found in the list of devices returned by "adb devices -l".'
            'The devices connected are: %s' % (adb_device, os.linesep + out))
    elif number_of_devices > 1:
      raise common.AdbError(
          'Multiple Android devices are connected to this host. '
          'Please specify a device using --adb-device <serial>. '
          'The devices connected are: %s' % (os.linesep + out))

  def get_adb_device_argument(self, adb_device=None, check_devices=True):
    """Construct the argument for ADB to select the specified device.

    Args:
      adb_device: Serial number of the device to use with ADB.
      check_devices: Whether to check the specified device exists.

    Returns:
      String which contains the second argument passed to ADB to select a
      target device.

    Raises:
      AdbError: If adb_device is None and more than one device is connected.
    """
    if check_devices:
      self.check_adb_devices(adb_device)
    return '-s ' + adb_device if adb_device else ''

  def list_installed_packages(self, adb_device=None, check_devices=True):
    """Get the list of packages installed on an Android device.

    Args:
      adb_device: The device to query.
      check_devices: Check whether the specified device exists.

    Raises:
      AdbError: If it's not possible to query the device.
    """
    packages = []
    for line in self.run_subprocess(
        '%s %s shell pm list packages' % (
            self._find_binary(BuildEnvironment.ADB),
            self.get_adb_device_argument(
                adb_device, check_devices=check_devices)),
        shell=True, capture=True)[0].splitlines():
      m = _MATCH_PACKAGE.match(line)
      if m:
        packages.append(m.groups()[0])
    return packages

  def install_android_apk(self, path='.', adb_device=None):
    """Install an android apk on the given device.

    This function will attempt to install an unsigned APK if a signed APK is
    not available which will *only* work on rooted devices.

    Args:
      path: Relative path from project directory to project to run.
      adb_device: The device to run the apk on. If none it will use the only
        device connected.

    Raises:
      ConfigurationError: If no APKs are found.
      AdbError: If it's not possible to install the APK.
    """
    adb_path = self._find_binary(BuildEnvironment.ADB)
    adb_device_arg = self.get_adb_device_argument(adb_device)
    manifest = self.parse_manifest(path=path)
    buildxml = self.create_update_build_xml(manifest, path=path)
    apks = [f for f in self.get_apk_filenames(buildxml.project_name,
                                              path=path) if os.path.exists(f)]
    if not apks:
      raise common.ConfigurationError(
          'Unable to find an APK for the project in %s' % (
              self.get_project_directory(path=path)))
    # If the project is installed, uninstall it.
    if manifest.package_name in self.list_installed_packages(
        adb_device=adb_device, check_devices=False):
      self.run_subprocess('%s %s uninstall %s' % (
          adb_path, adb_device_arg, manifest.package_name), shell=True)
    # Install the APK.
    self.run_subprocess('%s %s install %s' % (
        adb_path, adb_device_arg, apks[0]), shell=True)

  def install_all(self, path='.', adb_device=None, exclude_dirs=None):
    """Locate and install all Android APKs.

    This function recursively scans a directory tree for Android application
    projects and installs them on the specified device.

    Args:
      path: Path to search the search in, defaults to '.'
      adb_device: The device to install the APK to. If none it will use the
        only device connected.
      exclude_dirs: List of directory names to exclude from project
        detection (see find_projects() for more information).

    Returns:
      (retval, errmsg) tuple of an integer return value suitable for
      returning to the invoking shell, and an error string (if any) or None
      (on success).
    """
    retval = 0
    errmsg = None

    apk_dirs, unused_lib_dirs = self.find_projects(path=path,
                                                   exclude_dirs=exclude_dirs)

    for apk_dir in apk_dirs:
      try:
        self.install_android_apk(path=apk_dir, adb_device=adb_device)
      except common.Error as e:
        errmsg  = 'buildutil error: %s' % e.error_message
        retval = e.error_code
        break

    return (retval, errmsg)

  def run_android_apk(self, path='.', adb_device=None, wait=True):
    """Run an android apk on the given device.

    Args:
      path: Relative path from project directory to project to run.
      adb_device: The device to run the apk on. If none it will use the only
        device connected.
      wait: Optional argument to tell the function to wait until the process
        completes and dump the output.
    """
    manifest = self.parse_manifest(path=path)
    full_name = '%s/%s' % (manifest.package_name, manifest.activity_name)
    adb_path = self._find_binary(BuildEnvironment.ADB)
    adb_device_arg = self.get_adb_device_argument(adb_device)

    self.run_subprocess('%s %s logcat -c' % (adb_path, adb_device_arg),
                        shell=True)

    self.run_subprocess(
        ('%s %s shell am start -S -n %s' % (adb_path, adb_device_arg,
                                            full_name)), shell=True)

    end_match = re.compile(
        (r'.*(Displayed|Activity destroy timeout|'
         r'Force finishing activity).*%s.*' % full_name))

    while wait:
      # Use logcat -d so that it can be parsed easily in order to determine
      # when the process ends. An alternative is to read the stream as it gets
      # written but this leads to delays in reading the stream and is difficult
      # to get working propery on windows.
      out, unused_err = self.run_subprocess(
          ('%s %s logcat -d' % (adb_path, adb_device_arg)),
          capture=True, shell=True)

      for line in out.splitlines():
        if end_match.match(line):
          print out
          wait = False

  def run_all(self, path='.', adb_device=None, exclude_dirs=None, wait=True):
    """Locate and run all Android APKs.

    This function recursively scans a directory tree for Android application
    projects and runs them on the specified device.

    Args:
      path: Path to search the search in, defaults to '.'
      adb_device: The device to run the APK on. If none it will use the
        only device connected.
      exclude_dirs: List of directory names to exclude from project
        detection (see find_projects() for more information).
      wait: Whether to wait for the application to start.

    Returns:
      (retval, errmsg) tuple of an integer return value suitable for
      returning to the invoking shell, and an error string (if any) or None
      (on success).
    """
    retval = 0
    errmsg = None

    apk_dirs, unused_lib_dirs = self.find_projects(path=path,
                                                   exclude_dirs=exclude_dirs)

    for apk_dir in apk_dirs:
      try:
        self.run_android_apk(path=apk_dir, adb_device=adb_device, wait=wait)
      except common.Error as e:
        errmsg  = 'buildutil error: %s' % e.error_message
        retval = e.error_code
        break

    return (retval, errmsg)
