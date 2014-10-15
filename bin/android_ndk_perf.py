#!/usr/bin/python
# Copyright 2014 Google Inc. All Rights Reserved.
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

"""@file bin/android_ndk_perf.py Linux perf automation for Android.

This script simplifies CPU profiling of Android NDK apps.
"""

import argparse
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import xml.dom.minidom as minidom

## Directory containing this script.
SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))

## Directory containing perf binaries and other tools used by this script.
PERF_TOOLS_DIRECTORY = os.path.abspath(os.path.join(SCRIPT_DIRECTORY,
                                                    os.path.pardir, 'perf'))

## Android manifest filename.
MANIFEST_NAME = 'AndroidManifest.xml'

## Set of tested devices that are known to support perf.
SUPPORTED_DEVICES = set([
    'mantaray',  # Nexus 10
    'nakasi',  # Nexus 7 (2012)
])

## Set of tested devices that are known to have broken support for perf.
BROKEN_DEVICES = set([
    'razor',  # Nexus 7 (2013)
    'hammerhead',  # Nexus 5
])

## Maps a python platform.machine() string to a list of compatible Android
## (AOSP) build system architecture.
HOST_MACHINE_TYPE_TO_ARCHITECTURE = {
    'x86_64': ['x86_64', 'x86'],  # Linux / OSX.
    'AMD64': ['x86_64', 'x86'],  # Windows.
}

## Set of regular expressions that map a platform.system() to an Android
## (AOSP) build system OS name.
HOST_SYSTEM_TO_OS_NAME = (
    (re.compile(r'Darwin'), 'darwin'),
    (re.compile(r'Linux'), 'linux'),
    (re.compile(r'Windows'), 'windows'),
    (re.compile(r'CYGWIN.*'), 'windows')
)

## Maps an ABI to a set of compatible Android (AOSP) architectures.
ANDROID_ABI_TO_ARCHITECTURE = {
    'armeabi': ['arm'],
    'armeabi-v7a': ['arm'],
    'arm64-v8a': ['arm64', 'arm'],
    'x86': ['x86'],
    'x86-64': ['x86-64', 'x86'],
    'mips': ['mips'],
}

## List of paths to search for a host binary.
HOST_BINARY_SEARCH_PATHS = [
    os.path.join(PERF_TOOLS_DIRECTORY, 'bin'),
    os.path.join(PERF_TOOLS_DIRECTORY, 'tools', 'profile_chrome',
                 'third_party'),
    os.path.join(PERF_TOOLS_DIRECTORY, 'tools', 'telemetry', 'telemetry',
                 'core', 'platform', 'profiler'),
]

## List of paths to search for a target (Android) binary.
TARGET_BINARY_SEARCH_PATHS = [
    os.path.join(PERF_TOOLS_DIRECTORY, 'bin'),
]

# TODO(smiles): Replace with temporary file
SCRIPT_OUTPUT = 'perf_script.txt'
# TODO(smiles): Replace with temporary file
JSON_OUTPUT = 'perf_json.json'


class CommandFailedError(Exception):
  """Thrown when a shell command fails.

  Attributes:
    returncode: Status of the failed command.
  """

  def __init__(self, error_string, returncode):
    """Initialize this instance.

    Args:
      error_string: String associated with the exception.
      returncode: Assigned to return_status of this instance.
    """
    super(CommandFailedError, self).__init__(error_string)
    self.returncode = returncode


class Error(Exception):
  """General error thrown by this module."""
  pass


class BinaryNotFoundError(Error):
  """Thrown when a binary isn't found."""
  pass


class Adb(object):
  """Executes ADB commands on a device.

  Attributes:
    _serial: Device serial number to connect to.  If this is an empty string
      this class will use the first device connected if only one device is
      connected.
    cached_properties: Dictionary of cached properties of the device.
    verbose: Whether to display all shell commands run by this class.

  Class Attributes:
    _MATCH_DEVICES: Regular expression which matches connected devices.
    _MATCH_PROPERTY: Regular expression which matches properties returned by
      the getprop shell command.
  """

  class Error(Exception):
    """Thrown when the Adb object detects an error."""
    pass

  _MATCH_DEVICES = re.compile(r'^(List of devices attached\s*\n)|(\n)$')
  _MATCH_PROPERTY = re.compile(r'^\[([^\]]*)\]: *\[([^\]]*)\]$')

  def __init__(self, serial, verbose=False):
    """Initialize this instance.

    Args:
      serial: Device serial number to connect to.  If this is an empty
        string this class will use the first device connected if only one
        device is connected.
      verbose: Whether to display all shell commands run by this class.
    """
    self.cached_properties = {}
    self.verbose = verbose
    self._serial = serial

  def run_command(self, command, error, keyboard_interrupt_success=False):
    """Run an ADB command for a specific device.

    Args:
      command: Command to execute.
      error: The message to print if the command fails.
      keyboard_interrupt_success: Whether the a keyboard interrupt generates
        a command failure.

    Returns:
      (stdout, stderr, kbdint) where stdout is a string containing the
      standard output stream and stderr is a string containing the
      standard error stream and kbdint is whether a keyboard interrupt
      occurred.

    Raises:
      CommandFailedError: If the command fails.
    """
    return execute_local_command(
        'adb %s %s' % ('-s ' + self.serial if self.serial else '',
                       command), '%s (device=%s)' % (error, str(self)),
        verbose=self.verbose,
        keyboard_interrupt_success=keyboard_interrupt_success)

  def shell_command(self, command, error, keyboard_interrupt_success=False):
    """Run a shell command on the device associated with this instance.

    Args:
      command: Command to execute.
      error: The message to print if the command fails.
      keyboard_interrupt_success: Whether the a keyboard interrupt generates
        a command failure.

    Returns:
      (stdout, stderr, kbdint) where stdout is a string containing the
      standard output stream and stderr is a string containing the
      standard error stream and kbdint is whether a keyboard interrupt
      occurred.

    Raises:
      CommandFailedError: If the command fails.
    """
    # ADB doesn't return status codes from shell commands to the host shell
    # so get the status code up from the shell using the standard error
    # stream.
    out, err, kbdint = self.run_command(
        r'shell "%s; echo \$? >&2"' % command, error,
        keyboard_interrupt_success=keyboard_interrupt_success)
    out_lines = out.splitlines()
    # If a keyboard interrupt occurred and the caller wants to ignore the
    # interrupt status, ignore it.
    if kbdint and keyboard_interrupt_success:
      returncode = 0
    else:
      returncode = 1
      # Regardless of the destination stream on the Android device ADB
      # redirects everything to the standard error stream so this looks at the
      # last line of the stream to get the command status code.
      if out_lines:
        try:
          returncode = int(out_lines[-1])
        except ValueError:
          pass
    if returncode:
      print out
      print >> sys.stderr, err
      raise CommandFailedError(error, returncode)
    return (os.linesep.join(out_lines[:-1]), err, kbdint)

  @property
  def serial(self):
    """Serial number of the device associated with this class."""
    return self._serial

  @serial.setter
  def serial(self, serial):
    """Set the serial number of the device associated with this class.

    Args:
      serial: Serial number string.

    Raises:
      Adb.Error: If no devices are connected, the serial number isn't in the
        set of connected devices or no serial number is specified and more
        than one device is connected.
    """
    # Verify the serial number is valid for the set of connected devices.
    devices = self.get_devices()
    number_of_devices = len(devices)
    error_message = []
    if not number_of_devices:
      error_message.append('No Android devices are connected to this host.')
    elif serial and serial not in [d.split()[0] for d in devices]:
      error_message = ['%s is not connected to the host.' % serial,
                       'The connected devices are:']
      error_message.extend(devices)
    elif not serial and number_of_devices > 1:
      error_message = ['Multiple Android devices are connected to this host.',
                       'The connected devices are:']
      error_message.extend(devices)
    if error_message:
      raise Adb.Error(os.linesep.join(error_message))

    # Set the serial number and clear the cached properties.
    self._serial = serial
    self.cached_properties = {}

  def get_prop(self, android_property_name, use_cached=True):
    """Gets a property (getprop) from the device.

    Args:
      android_property_name: The property to get.
      use_cached: Whether to use a cached value of the property.

    Returns:
      The value of the retrieved property.

    Raises:
      CommandFailedError: If the command fails.
    """
    if not use_cached:
      self.cached_properties = {}

    if not self.cached_properties:
      out, _, _ = self.shell_command('getprop', 'Unable to get properties')
      for l in out.splitlines():
        m = Adb._MATCH_PROPERTY.match(l)
        if m:
          key, value = m.groups()
          self.cached_properties[key] = value
    return self.cached_properties.get(android_property_name)

  def get_supported_abis(self):
    """Gets the set of ABIs supported by the Android device.

    Returns:
      List of ABI strings.
    """
    return [v for v in [self.get_prop('ro.product.cpu.%s' % p)
                        for p in ('abi', 'abi2')] if v]

  def get_version(self):
    """Gets the version of Android on the device.

    Returns:
      The android version number
    """
    return self.get_prop('ro.build.version.release')

  def get_model_and_name(self):
    """Gets the version of Android on the device.

    Returns:
      Tuple of android model and name.

    Raises:
      CommandFailedError: If the command fails.
    """
    return [self.get_prop('ro.product.%s' % p) for p in ['model', 'name']]

  def get_api_level(self):
    """Gets the API level of Android on the device.

    Returns:
      Integer API level.

    Raises:
      CommandFailedError: If the command fails.
    """
    return int(self.get_prop('ro.build.version.sdk'))

  def __str__(self):
    """Get a string representation of this device.

    Returns:
      Serial number of this device.
    """
    return self.serial if self.serial else '<default>'

  def get_devices(self):
    """Gets the numer of connected android devices.

    Returns:
      The number of connected android devices.

    Raises:
      CommandFailedError: An error occured running the command.
    """
    out, _, _ = execute_local_command(
        'adb devices -l', 'Unable to get the list of connected devices',
        verbose=self.verbose)
    return Adb._MATCH_DEVICES.sub(r'', out).splitlines()


def version_to_tuple(version):
  """Convert a version to a tuple of ints.

  Args:
    version: Version to convert

  Returns:
    Tuple of ints
  """
  return tuple([int(elem) for elem in version.split('.')])


def is_version_less_than(version1, version2):
  """Comare to version strings.

  Args:
    version1: The first version to compare
    version2: The second version to compare

  Returns:
    True if version1 < version2 and false otherwise.
  """
  return version_to_tuple(version1) < version_to_tuple(version2)


def get_package_name_from_manifest(name):
  """Gets the name of the apk package to profile from the Manifest.

  Args:
    name: The name of the AndroidManifest file to search through.

  Returns:
    The name of the apk package.
  """
  xml = minidom.parse(name)
  return xml.getElementsByTagName('manifest')[0].getAttribute('package')


def get_host_os_name_architecture():
  """Get the OS name for the host and the architecture.

  Returns:
    (os_name, architectures) tuple where os_name is a string that contains the
    name of the OS and architectures is a list of supported processor
    architectures, in the form used by the AOSP build system.

  Raises:
    Error: If the operating system isn't recognized.
  """
  system_name = platform.system()
  for regexp, os_name in HOST_SYSTEM_TO_OS_NAME:
    if regexp.match(system_name):
      return (os_name, HOST_MACHINE_TYPE_TO_ARCHITECTURE[platform.machine()])
  raise Error('Unknown OS %s' % system_name)


def get_target_architectures(adb_device):
  """Get the architecture of the target device.

  Args:
    adb_device: The device to query.

  Returns:
    List of compatible architecture strings in the form used by the AOSP build
    system.
  """
  architectures = []
  for abi in adb_device.get_supported_abis():
    architectures.extend(ANDROID_ABI_TO_ARCHITECTURE[abi])
  # Remove duplicates from the returned list.
  unsorted_architectures = set(architectures)
  sorted_architectures = []
  for arch in architectures:
    if arch in unsorted_architectures:
      unsorted_architectures.remove(arch)
      sorted_architectures.append(arch)
  return sorted_architectures


def find_target_binary(name, adb_device):
  """Find the path of the specified target (Android) binary.

  Args:
    name: The name of the binary to find.
    adb_device: Device connected to the host.

  Returns:
    The path of the binary.

  Raises:
    BinaryNotFoundError: If the specified binary isn't found.
  """

  for arch in get_target_architectures(adb_device):
    arch_path = os.path.join('android-%d' % adb_device.get_api_level(),
                             '-'.join(('arch', arch)))
    for search_path in TARGET_BINARY_SEARCH_PATHS:
      binary_path = os.path.join(search_path, arch_path, name)
      if os.path.exists(binary_path):
        return binary_path
  raise BinaryNotFoundError('Unable to find Android %s binary %s' % (
      arch_path, name))


def find_host_binary(name, adb_device=None):
  """Find the path of the specified host binary.

  Args:
    name: The name of the binary to find.
    adb_device: Device connected to the host, if this is None this function
      does not search for device specific binaries.

  Returns:
    The path of the binary.

  Raises:
    BinaryNotFoundError: If the specified binary isn't found.
  """
  # On Windows search for filenames that have executable extensions.
  exe_extensions = ['']
  if platform.system() == 'Windows':
    extensions = os.environ('PATHEXT')
    if extensions:
      exe_extensions.extend(extensions.split(';'))

  search_paths = []
  if adb_device:
    os_name, architectures = get_host_os_name_architecture()
    os_paths = []
    for arch in architectures:
      for target_arch in get_target_architectures(adb_device):
        os_paths.append(os.path.join('android-%d' % adb_device.get_api_level(),
                                     '-'.join((os_name, arch, 'arch-',
                                               target_arch))))
    search_paths.extend(os_paths)
  search_paths.append('')
  for arch_path in search_paths:
    for search_path in HOST_BINARY_SEARCH_PATHS:
      for exe_extension in exe_extensions:
        binary_path = (os.path.join(search_path, arch_path, name) +
                       exe_extension)
        if os.path.exists(binary_path):
          return binary_path
  raise BinaryNotFoundError('Unable to find host %s binary %s' % (
      str(search_paths[:-1]), name))


def execute_local_command(command_str, error, display_output_on_error=True,
                          verbose=False, keyboard_interrupt_success=False):
  """Execute a command and throw an exception on failure.

  Args:
    command_str: The command to be executed.
    error: The message to print when failing.
    display_output_on_error: Display the command output if it fails.
    verbose: Whether to display excecuted commands.
    keyboard_interrupt_success: Whether the keyboard interrupt generates
      a command failure.

  Returns:
    (stdout, stderr, kbdint) where stdout is a string containing the
    standard output stream and stderr is a string containing the
    standard error stream and kbdint is whether a keyboard interrupt
    occurred.

  Raises:
    CommandFailedError: An error occured running the command.
  """
  if verbose:
    print >> sys.stderr, command_str

  class SignalHandler(object):
    """Signal handler which allows signals to be sent to the subprocess.

    Attributes:
      called: Whether the signal handler has been called.
    """

    def __init__(self):
      """Initialize the instance."""
      self.called = False

    def __call__(self, unused_signal, unused_frame):
      """Logs whether the signal handler has been called."""
      self.called = True

  sigint = SignalHandler()
  previous_sigint = signal.signal(signal.SIGINT, sigint)

  process = subprocess.Popen(command_str, shell=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  # Read from the pipe for the case that anything is left.
  out, err = process.communicate()

  if sigint.called and keyboard_interrupt_success:
    process.returncode = 0

  signal.signal(signal.SIGINT, previous_sigint)

  if process.returncode:
    if display_output_on_error:
      print out
      print >> sys.stderr, err
    raise CommandFailedError(error, process.returncode)
  return (out, err, sigint.called)


def get_pid(process_name, adb_device):
  """Gets the process id of the given process on the Android device.

  Args:
    process_name: The name of the process to get the pid of.
    adb_device: The device to look for the process on.

  Returns:
    The process id of the given process if found or None if not.
  """
  out, _, _ = adb_device.shell_command(
      r'fields=( \$(ps | grep -F %s) ); echo \${fields[1]}' % process_name,
      r'Unable to get PID of %s' % process_name)
  return int(out)


def get_perf_data_file(package_name, adb_device, output_file):
  """Get the perf data file from the remote host.

  Args:
    package_name: The name of the running package.
    adb_device: The device that the package is running on.
    output_file: The directory to store the output in.
  """
  adb_device.shell_command(
      'run-as %s chmod 666 /data/data/%s/perf.data' % (
          package_name, package_name), 'Unable to make perf.data readable.')
  adb_device.run_command(
      'pull /data/data/%s/perf.data' % package_name,
      'Unable to get perf data from device.')
  adb_device.shell_command(
      'run-as %s rm /data/data/%s/perf.data' % (package_name, package_name),
      'Unable to delete perf.data from device.')

  if output_file:
    shutil.move('perf.data', output_file)


def run_perf_remotely(adb_device, apk_directory, perf_args, output_file):
  """Run perf remotely.

  Args:
    adb_device: The device that perf is run on
    apk_directory: The directory of the apk file to profile
    perf_args: The arguments to run perf with
    output_file: The destination perf file to save the data to

  Returns:
    1 for error, 0 for success.
  """
  android_perf = find_target_binary('perf', adb_device)
  android_perf_remote = '/data/local/tmp/perf'
  perf_command = ''
  if perf_args:
    perf_command = perf_args[0]

  adb_device.run_command('push %s %s' % (android_perf, android_perf_remote),
                         'Unable to push perf executable to device')

  # TODO(smiles): Optionally install the apk on the device.
  # TODO(smiles): Read main activity and package name from APK using aapt.
  name = MANIFEST_NAME
  if apk_directory:
    name = apk_directory + '/' + MANIFEST_NAME
  if not os.path.isfile(name):
    print >> sys.stderr, (
        'Cannot find Manifest %s, please specify the directory where the '
        'manifest is located with --apk-directory.') % name
    return 1

  package_name = get_package_name_from_manifest(name)

  # Deal with starting the package and retrieving the data
  if perf_command == 'record' or perf_command == 'stat':
    adb_device.shell_command(
        'am start -n %s/android.app.NativeActivity' % package_name,
        'Unable to start Android application %s' % package_name)
    pid = get_pid(package_name, adb_device)
    if pid is None:
      print  >> sys.stderr, 'Cannot start %s' % package_name
      return 1

    # Use -m 4 due to certain devices not having mmap data pages.
    record_args = ''
    if perf_command == 'record':
      record_args = '-m 4'
    out, _, _ = adb_device.shell_command(
        'run-as %(name)s %(perf)s %(cmd)s -p %(pid)d -o %(output)s '
        '%(record_args)s %(perf_args)s' %
        {'name': package_name, 'perf': android_perf_remote,
         'cmd': perf_command, 'pid': pid,
         'output': '/data/data/%s/perf.data' % package_name,
         'record_args': record_args, 'perf_args': ' '.join(perf_args[1:])},
        'Unable to execute perf record on device.',
        keyboard_interrupt_success=True)
    print out
    if perf_command == 'record':
      get_perf_data_file(package_name, adb_device, output_file)
  else:
    out, _, _ = adb_device.shell_command(
        '%s %s' % (android_perf_remote, ' '.join(perf_args)),
        'Unable to execute perf %s on device.' % perf_command)
  return 0


def run_perf_visualizer(browser, perf_args, verbose=False):
  """Generate the visualized html.

  Args:
    browser: The browser to use for display
    perf_args: The arguments to run the visualizer with.
    verbose: Whether to display all shell commands executed by this function.

  Returns:
    1 for error, 0 for success
  """
  perf_host = find_host_binary('perfhost')
  perf_to_tracing = find_host_binary('perf_to_tracing_json.py')
  perf_vis = find_host_binary('perf-vis.py')

  # Output samples and stacks while including specific attributes that are
  # read by the visualizer
  out, _, _ = execute_local_command(
      '%s script -f comm,tid,time,cpu,event,ip,sym,dso,period' % perf_host,
      'Cannot visualize perf data. Please run record using -R',
      verbose=verbose)

  output_file = open(SCRIPT_OUTPUT, 'w')
  output_file.write(out)
  output_file.close()

  # Generate a common json format from the outputted sample data
  out, _, _ = execute_local_command('%s perf_script.txt' % perf_to_tracing, '',
                                    verbose=verbose)

  output_file = open(JSON_OUTPUT, 'w')
  output_file.write(out)
  output_file.close()

  # Generate the html file from the json data
  out, _, _ = execute_local_command('%s %s perf_json.json' % (
      perf_vis, ' '.join(perf_args)), '', verbose=verbose)

  os.remove(SCRIPT_OUTPUT)
  os.remove(JSON_OUTPUT)

  url = re.sub(r'.*output: ', r'', out.replace('\n', ' ')).strip()
  execute_local_command(
      '%s %s' % (browser, url), 'Cannot start browser %s' % browser,
      verbose=verbose)

  return 0


def main():
  """Automate Linux perf to simplfy CPU profiling of NDK applications.

  Usage: android_ndk_perf.py [options] perf_command

  Run with -h to view options.

  perf_command can be any valid command for the Linux perf tool or
  "visualize" to display a visualization of the performance report.

  Returns:
    0 if successful, 1 otherwise.
  """
  parser = argparse.ArgumentParser(
      description=('Run Perf for the Android package in the current '
                   'directory on a connected device.'))
  parser.add_argument(
      '-s', '--adb-device',
      help=('adb-device specifies the serial_number of the device to deploy '
            'the built apk to if multiple Android devices are connected to '
            'the host'))
  parser.add_argument(
      '--apk-directory',
      help='apk-directory specifies the directory of the package to profile')
  parser.add_argument(
      '--browser',
      help='browser specifies which browser to use for visualization')
  parser.add_argument(
      '-v', '--verbose', help='Display verbose output.', action='store_true',
      default=False)
  # This should hijack the -o option of perf record.
  parser.add_argument('-o', '--output-file')

  args, perf_args = parser.parse_known_args()
  perf_command = ''
  if perf_args:
    perf_command = perf_args[0]

  verbose = args.verbose

  if perf_command == 'visualize':
    if args.browser:
      browser = args.browser
      browser_name = args.browser
    else:
      # TODO(smiles): This does *not* work on OSX or Windows
      browser = 'xdg-open'
      browser_name, _ = execute_local_command(
          'xdg-settings get default-web-browser',
          'Cannot find default browser. Please specify using --browser.',
          verbose=verbose)
      browser_name = browser_name.strip()

    if not re.match(r'.*chrom.*', browser_name):
      print (
          'WARNING: %s is not a version of chrome and may not be able to '
          'display the resulting performance data.' % browser_name)

    return run_perf_visualizer(browser, perf_args[1:])

  # Construct a class to communicate with the ADB device.
  try:
    adb_device = Adb(args.adb_device, verbose)
  except Adb.Error, error:
    print >> sys.stderr, os.linesep.join([
        str(error), 'Try specifying a device using --adb-device <serial>.'])
    return 1

  try:
    # Run perf remotely
    if (perf_command == 'record' or perf_command == 'stat'
        or perf_command == 'top'):

      android_version = adb_device.get_version()
      if is_version_less_than(android_version, '4.4'):
        print (
            'WARNING: The precompiled perf binaries may not be compatable '
            'with android version %s. If you enounter issues please try '
            'version 4.4 or higher.' % android_version)
      (model, name) = adb_device.get_model_and_name()
      if name in BROKEN_DEVICES:
        print (
            'WARNING: %s is known to have broken performance counters. It is '
            'recommended that you use a different device to record perf data.'
            % model)
      elif name not in SUPPORTED_DEVICES:
        print (
            'WARNING: %s is not in the list of supported devices. It is '
            'likely that the performance counters don\'t work and you may '
            'need to try a different device.' % model)

      return run_perf_remotely(adb_device, args.apk_directory, perf_args,
                               args.output_file)
    # Run perf locally
    else:
        execute_local_command(
            '%s %s' % (find_host_binary('perfhost', adb_device),
                       ' '.join(perf_args)), 'Failed to execute perfhost',
            verbose=verbose)

  except CommandFailedError, error:
    return error.returncode
  return 0

if __name__ == '__main__':
  sys.exit(main())
