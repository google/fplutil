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


class AndroidManifest(object):

  """Class that extracts build information from an AndroidManifest.xml.

  Attributes:
    path: Path to manifest file as set in initializer.
    min_sdk: Minimum SDK version from the uses-sdk element.
    target_sdk: Target SDK version from the uses-sdk element, or min_sdk if it
      is not set.
    app_name: Name taken from the android:label attribute of the application
      element.
  """

  def __init__(self, path):
    """Constructs the AndroidManifest for a specified path.

    Args:
      path: The absolute path to the manifest file.

    Raises:
      ConfigurationError: Manifest file missing.
    """
    if not os.path.exists(path):
      raise ConfigurationError(path, os.strerror(errno.ENOENT))

    self.path = path
    self.min_sdk = 0
    self.target_sdk = 0
    self.app_name = None

  def parse(self):
    """Parse the Android manifest file and extract useful information.

    Raises:
      ConfigurationError: Elements were missing or incorrect in the manifest.
    """
    etree = None
    try:
      etree = xml.etree.ElementTree.parse(self.path)
    except xml.etree.ElementTree.ParseError as pe:
      raise ConfigurationError(self.path, 'XML parse error: ' + str(pe))

    root = etree.getroot()

    sdk_element = root.find('uses-sdk')

    if sdk_element is None:
      raise ConfigurationError(self.path, 'uses-sdk element missing')

    min_sdk_version = sdk_element.get(
        '{http://schemas.android.com/apk/res/android}minSdkVersion')
    target_sdk_version = sdk_element.get(
        '{http://schemas.android.com/apk/res/android}targetSdkVersion')

    if not min_sdk_version:
      raise ConfigurationError(self.path, 'minSdkVersion missing')
    if not target_sdk_version:
      target_sdk_version = min_sdk_version

    self.min_sdk = int(min_sdk_version)
    self.target_sdk = int(target_sdk_version)

    app_element = root.find('application')

    if app_element is None:
      raise ConfigurationError(self.path, 'application element missing')

    self.app_name = app_element.get(
        '{http://schemas.android.com/apk/res/android}label')

    if not self.app_name:
      raise ConfigurationError(self.path, 'application tag label missing')


def build_defaults():
  """Helper function to set build defaults.

  Returns:
    A dict containing appropriate defaults for a build.
  """
  args[_SDK_HOME] = (os.getenv(_SDK_HOME_ENV_VAR) or
                     _find_path_from_binary('android', 2))
  args[_NDK_HOME] = (os.getenv(_NDK_HOME_ENV_VAR) or
                     _find_path_from_binary('ndk-build', 1))
  args[_ANT_PATH] = (os.getenv(_ANT_PATH_ENV_VAR) or
                     distutils.spawn.find_executable('ant'))
  args[_ANT_FLAGS] = '-quiet'
  args[_ANT_TARGET] = 'release'
  args[_APK_KEYSTORE] = None
  args[_APK_KEYALIAS] = None
  args[_APK_PASSFILE] = None
  args[_SIGN_APK] = False

  return args


def add_arguments(parser):
  """Add module-specific command line arguments to an argparse parser.

  This will take an argument parser and add arguments appropriate for this
  module. It will also set appropriate default values.

  Args:
    parser: The argparse.ArgumentParser instance to use.
  """
  defaults = build_defaults()

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
                      help='Path to file containing signing keystore password',
                      dest=_APK_PASSFILE, default=defaults[_APK_PASSFILE])
  parser.add_argument(
      '-S', '--' + _SIGN_APK,
      help='Enable signing of Android APKs',
      dest=_SIGN_APK, action='store_true', default=defaults[_SIGN_APK])


class BuildEnvironment(object):

  def __init__(self, arguments):
    """Constructs the BuildEnvironment with basic information needed to build.

    The build properties as set by argument parsing are also available
    to be modified by code using this object after construction.

    It is required to call this function with a valid arguments object,
    obtained either by calling argparse.ArgumentParser.parse_args() after
    adding this modules arguments via buildutils.add_arguments(), or by passing
    in an object returned from buildutils.build_defaults().

    Args:
      arguments: The argument object returned from ArgumentParser.parse_args().
    """

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
    _check_binary('ndk-build', ndk_build)

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
    (stdout, unused_stderr) = self.run_subprocess(acmd, True)

    if self.verbose:
      print 'android list target returned: {%s}' % (stdout)
    # Find the highest installed SDK <= targetSdkVersion.
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
        if n > installed and n <= target:
          if self.verbose:
            print 'sdk api level %d found' % (n)
          installed = n
        if installed == target:
          break

    if installed < minsdk:
      raise ConfigurationError(self.sdk_home,
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
      output: Optional relative path from project directory to output directory.

    Raises:
      SubCommandError: NDK toolchain invocation failed or returned an error.
      ToolPathError: Android NDK or SDK location not found in configured build
          environment or $PATH, or ant not found.
      ConfigurationError: Required build configuration file missing or broken
          in an unrecoverable way.
      IOError: An error occurred writing or copying the APK.
    """
    ant = self.ant_path
    _check_binary('ant', ant)

    android = os.path.join(self.sdk_home, 'tools', 'android')
    _check_binary('android', android)

    self.build_android_libraries([path])

    project = os.path.abspath(os.path.join(self.project_directory, path))

    manifest_path = os.path.join(project, 'AndroidManifest.xml')

    manifest = AndroidManifest(manifest_path)
    manifest.parse()

    if not os.path.exists(os.path.join(project, 'build.xml')):
      apitarget = self._find_best_android_sdk(android, manifest.min_sdk,
                                              manifest.target_sdk)
      acmd = [android, 'update', 'project', '--path', project,
              '--target', apitarget, '--name', manifest.app_name]
      self.run_subprocess(acmd)

    acmd = [ant, self.ant_target]

    if self.ant_flags:
      acmd += shlex.split(self.ant_flags, posix=self._posix)

    self.run_subprocess(acmd, cwd=path)

    # ant outputs to $PWD/bin. The APK will have a name as constructed below.
    apkname = '%s-%s-unsigned.apk' % (manifest.app_name, self.ant_target)
    apkpath = os.path.join(project, 'bin', apkname)
    source_apkpath = apkpath

    if self.sign_apk:
      signed_apkname = '%s.apk' % manifest.app_name
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
          raise ConfigurationError(keystore,
                                   ('Must specify all of keystore, '
                                    'password file, and alias'))
        if passfile:
          raise ConfigurationError(passfile,
                                   ('Must specify all of keystore, '
                                    'password file, and alias'))
        if alias:
          raise ConfigurationError(alias,
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
          pf.write('%08x' % (random.random() * 16**8))

        alias = os.path.basename(source).split('.')[0]
        keytool = distutils.spawn.find_executable('keytool')
        _check_binary('keytool', keytool)
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
      _check_binary('zipalign', zipalign)

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
