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

detailed usage: android_ndk_perf.py [options] perf_command [perf_arguments]

perf_command can be any valid command for the Linux perf tool or
"visualize" to display a visualization of the performance report.

Caveats:
* "stat" and "top" require root access to the target device.
* "record" is *not* able to annotate traces with symbols from samples taken
  in the kernel without root access to the target device.
"""

import argparse
import os
import platform
import re
import signal
import subprocess
import sys
import threading
import xml.dom.minidom as minidom

## Directory containing this script.
SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))

## Directory containing perf binaries and other tools used by this script.
PERF_TOOLS_DIRECTORY = os.path.abspath(os.path.join(SCRIPT_DIRECTORY,
                                                    os.path.pardir, 'perf'))

## Target directory on the Android device used to push the perf executable and
## associated tools.
REMOTE_TEMP_DIRECTORY = '/data/local/tmp'

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

## Directory containing perf and perfhost binaries.
PERF_TOOLS_BIN_DIRECTORY = os.path.join(PERF_TOOLS_DIRECTORY, 'bin')

## List of paths to search for a host binary.
HOST_BINARY_SEARCH_PATHS = [
    PERF_TOOLS_BIN_DIRECTORY,
    os.path.join(PERF_TOOLS_DIRECTORY, 'tools', 'profile_chrome',
                 'third_party'),
    os.path.join(PERF_TOOLS_DIRECTORY, 'tools', 'telemetry', 'telemetry',
                 'core', 'platform', 'profiler'),
]

## List of paths to search for a target (Android) binary.
TARGET_BINARY_SEARCH_PATHS = [
    PERF_TOOLS_BIN_DIRECTORY,
    PERF_TOOLS_DIRECTORY,
]

## API level perf was introduced into AOSP.
PERF_MIN_API_LEVEL = 16

## Name of the perf binary that runs on the host machine.
PERFHOST_BINARY = 'perfhost'

## Perf binaries not supported warning message.
PERF_BINARIES_NOT_SUPPORTED = """
WARNING: The precompiled perf binaries may not be compatable with android
version %(ver)s. If you enounter issues please try version %(ver)s or higher.
"""

## Performance counters broken warning message.
PERFORMANCE_COUNTERS_BROKEN = """
WARNING: %s is known to have broken performance counters. It is recommended
that you use a different device to record perf data.
"""

## Device not supported warning message.
NOT_SUPPORTED_DEVICE = """
WARNING: %s is not in the list of supported devices. It is likely that the
performance counters don't work so you may need to try a different device.
"""

## Device not rooted error message.
DEVICE_NOT_ROOTED = """
WARNING: perf command "%s" requires a rooted device.  Try running "adb root"
before attempting to use this command.
"""

## Chrome web browser isn't found.
CHROME_NOT_FOUND = """
WARNING: %s is not Google Chrome and may not be able to display the resulting
performance data.
"""


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

  def run_command(self, command, error, **kwargs):
    """Run an ADB command for a specific device.

    Args:
      command: Command to execute.
      error: The message to print if the command fails.
      **kwargs: Keyword arguments passed to execute_local_command().

    Returns:
      (stdout, stderr, kbdint) where stdout is a string containing the
      standard output stream and stderr is a string containing the
      standard error stream and kbdint is whether a keyboard interrupt
      occurred.

    Raises:
      CommandFailedError: If the command fails.
    """
    kwargs = dict(kwargs)
    kwargs['verbose'] = self.verbose
    return execute_local_command(
        'adb %s %s' % ('-s ' + self.serial if self.serial else '',
                       command), '%s (device=%s)' % (error, str(self)),
        **kwargs)

  def shell_command(self, command, error, **kwargs):
    """Run a shell command on the device associated with this instance.

    Args:
      command: Command to execute.
      error: The message to print if the command fails.
      **kwargs: Keyword arguments passed to execute_local_command().

    Returns:
      (stdout, stderr, kbdint) where stdout is a string containing the
      standard output stream and stderr is a string containing the
      standard error stream and kbdint is whether a keyboard interrupt
      occurred.

    Raises:
      CommandFailedError: If the command fails.
    """
    kwargs = dict(kwargs)
    kwargs['verbose'] = self.verbose
    # ADB doesn't return status codes from shell commands to the host shell
    # so get the status code up from the shell using the standard error
    # stream.
    out, err, kbdint = self.run_command(
        r'shell "%s; echo \$? >&2"' % command, error, **kwargs)
    out_lines = out.splitlines()
    # If a keyboard interrupt occurred and the caller wants to ignore the
    # interrupt status, ignore it.
    if kbdint and kwargs.get('keyboard_interrupt_success'):
      returncode = 0
    else:
      returncode = 1
      # Regardless of the destination stream on the Android device ADB
      # redirects everything to the standard error stream so this looks at the
      # last line of the stream to get the command status code.
      if out_lines:
        try:
          returncode = int(out_lines[-1])
          out_lines = out_lines[:-1]
        except ValueError:
          pass
    if returncode:
      print out
      print >> sys.stderr, err
      raise CommandFailedError(error, returncode)
    return (os.linesep.join(out_lines), err, kbdint)

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

  def start_activity(self, package, activity):
    """Start an activity on the device.

    Args:
      package: Package containing the activity that will be started.
      activity: Name of the activity to start.

    Returns:
      The process id of the process for the package containing the activity
      if found.

    Raises:
      CommandFailedError: If the activity fails to start.
      Error: If it's possible to get the PID of the process.
    """
    package_activity = '%s/%s' % (package, activity)
    out, _, _ = self.shell_command(
        ' && '.join(['am start -S -n %s' % package_activity,
                     r'fields=( \$(ps | grep -F %s) )' % package,
                     r'echo \${fields[1]}']),
        'Unable to start Android application %s' % package_activity)
    try:
      return int(out.splitlines()[-1])
    except ValueError:
      raise Error('Unable to get the PID of %s' % package_activity)

  def push(self, local_file, remote_path):
    """Push a local file to the device.

    Args:
      local_file: File to push to the device.
      remote_path: Path on the device.

    Raises:
      CommandFailedError: If the push fails.
    """
    self.run_command('push %s %s' % (local_file, remote_path),
                     'Unable to push %s to %s' %
                     (local_file, remote_path))

  def push_files(self, local_remote_paths):
    """Push a set of local files to remote paths on the device.

    Args:
      local_remote_paths: List of (local, remote) tuples where "local" is the
        local path to push to the device and "remote" is the target location
        on the device.

    Raises:
      CommandFailedError: If the push fails.
    """
    for local, remote in local_remote_paths:
      self.push(local, remote)

  @staticmethod
  def get_package_data_directory(package_name):
    """Get the directory containing data for a package.

    Args:
      package_name: Name of a package installed on the device.

    Returns:
      Directory containing data for a package.
    """
    return '/data/data/%s' % package_name

  @staticmethod
  def get_package_file(package_name, package_file):
    """Get the path of a file in a package's data directory.

    Args:
      package_name: Name of a package installed on the device.
      package_file: Path of the file within the package data directory.

    Returns:
      Absolute path to the file in the package data directory.
    """
    return '/'.join(Adb.get_package_data_directory(package_name), package_file)

  def pull_package_file(self, package_name, package_file, output_file):
    """Pull a file from a package's directory.

    Args:
      package_name: Name of the package to pull the file from.
      package_file: Use Adb.get_package_file() to form the path.
      output_file: Local path to copy the remote file to.
    """
    self.shell_command('run-as %s chmod 666 %s' % (package_name, package_file),
                       'Unable to make %s readable.' % package_file)
    self.run_command('pull %s %s' % (package_file, output_file),
                     'Unable to copy %s from device to %s.' % (package_file,
                                                               output_file))


class SignalHandler(object):
  """Signal handler which allows signals to be sent to the subprocess.

  Attributes:
    called: Whether the signal handler has been called.
    signal_number: Number of the signal being caught.
    signal_handler: Original handler of the signal, restored on restore().
  """

  def __init__(self):
    """Initialize the instance."""
    self.called = False
    self.signal_number = 0
    self.signal_handler = None

  def __call__(self, unused_signal, unused_frame):
    """Logs whether the signal handler has been called."""
    self.called = True

  def acquire(self, signal_number):
    """Override the specified signal handler with this instance.

    Args:
      signal_number: Signal to override with this instance.
    """
    assert not self.signal_handler
    self.signal_number = signal_number
    self.signal_handler = signal.signal(self.signal_number, self)

  def release(self):
    """Restore the signal handler associated with this instance."""
    assert self.signal_handler
    signal.signal(self.signal_number, self.signal_handler)
    self.signal_handler = None


class PerfArgs(object):
  """Class which parses and processes arguments to perf.

  Attributes:
    initial_args: Arguments the instance is initialized with.
    args: Arguments that have been modified by methods of this class.
    command: Primary perf command.

  Class Attributes:
    SUPPORTED_COMMANDS: Set of commands that *should* work with Android, not
      all commands have been tested.
  """

  class Error(Exception):
    """Thrown if a problem is found parsing perf arguments."""
    pass


  SUPPORTED_COMMANDS = set(('annotate',
                            'archive',  # May not be compiled in.
                            'bench', # May not be compiled in.
                            'buildid-cache',
                            'buildid-list',
                            'diff',
                            'evlist',
                            'help',
                            'inject',
                            'list',
                            'lock',
                            'probe',
                            'record',
                            'report',
                            'sched',
                            'script',
                            'stat',
                            'test',
                            'timechart',
                            'top',
                            'visualize'  # Specific to this script.
                            ))

  def __init__(self, args, verbose):
    """Initialize the instance.

    Args:
      args: List of strings stored in initial_args.
      verbose: Whether verbose output is enabled.

    Raises:
      PerfArgs.Error: If a perf command isn't supported.
    """
    self.initial_args = args
    self.args = list(args)
    self.man_to_builtin_help()
    self.command = self.args[0] if self.args else ''
    if self.command in ('annotate', 'buildid-cache', 'buildid-list', 'diff',
                        'inject', 'lock', 'probe', 'record', 'report', 'sched',
                        'script', 'top') and verbose:
      self.args.append('--verbose')
    if self.command and self.command not in PerfArgs.SUPPORTED_COMMANDS:
      raise PerfArgs.Error('Unsupported perf command %s' % self.command)

  def requires_root(self):
    """Determines whether the perf command requires a rooted device.

    Returns:
      True if the command requires root, False otherwise.
    """
    return self.command in ('stat', 'top')

  def run_remote(self):
    """Determine whether the perf command needs to run on a remote device.

    Returns:
      True if perf should be run on an Android device, False otherwise.
    """
    sub_command = self.args[1:2]
    return (self.command in ('archive', 'bench', 'buildid-cache',
                             'buildid-list', 'list', 'probe', 'record',
                             'stat', 'test', 'top') or
            (self.command == 'lock' and ('record' in sub_command)) or
            (self.command == 'kmem' and ('record' in sub_command)) or
            (self.command == 'sched' and ('record' in sub_command or
                                          'replay' in sub_command)) or
            (self.command == 'script' and ('record' in self.args[1:])) or
            (self.command == 'timechart' and ('record' in sub_command)))

  def requires_process(self):
    """Determines whether the command records a process."""
    return (self.command == 'record' or
            (self.command in ('stat', 'top') and '-p' in self.args[1:]))

  def get_help_enabled(self):
    """Determine whether help display is requested in the arguments.

    Returns:
      True if help should be displayed, False otherwise.
    """
    return [arg for arg in self.args if arg in ('-h', '--help', 'help')]

  def man_to_builtin_help(self):
    """Convert perf arguments in the form "HELP COMMAND" to "COMMAND -h".

    Man pages are not provided with the binaries associated with this
    distribution so requests for them will fail.  This function converts
    requests for man pages to arguments that result in retrieving the built-in
    documentation from the perf binaries.
    """
    args = self.args
    out_args = []
    index = 0
    while index < len(args):
      arg = args[index]
      if arg == 'help' and index + 1 < len(args):
        out_args.append(args[index + 1])
        out_args.append('-h')
        index += 1
      else:
        out_args.append(arg)
      index += 1
    # Convert top level help argument into a form perf understands.
    if [arg for arg in out_args[0:1] if arg in ('-h', '--help')]:
      out_args = ['help']
    self.args = out_args

  def insert_symfs_dir(self, symbols_dir):
    """Insert symbols directory into perf arguments if it's not specified.

    Args:
      symbols_dir: Directory that contains symbols for perf data.
    """
    if not symbols_dir or self.command not in ('annotate', 'diff', 'report',
                                               'script', 'timechart'):
      return
    if '--symfs' not in self.args:
      return
    out_args = list(self.args)
    out_args.extend(('--symfs', symbols_dir))
    self.args = out_args

  def get_output_filename(self, remote_output_filename=''):
    """Parse output filename from perf arguments.

    Args:
      remote_output_filename: If this is a non-zero length string it replaces
        the current output filename in the arguments.

    Returns:
      Original output filename string.
    """
    if self.command == 'lock' and ('record' in self.args[1:]):
      return 'perf.data'
    output_filename = {'record': 'perf.data',
                       'stat': 'perf.txt',
                       'timechart': 'output.svg'}.get(self.command)
    if not output_filename:
      return ''

    args = self.args
    out_args = []
    index = 0
    found_filename = False
    while index < len(args):
      out_args.append(args[index])
      index += 1
      if args[index - 1] == '-o' and index < len(args):
        output_filename = args[index]
        found_filename = True
        out_args.append(remote_output_filename if remote_output_filename else
                        output_filename)
        index += 1
    if not found_filename and remote_output_filename:
      out_args.extend(('-o', remote_output_filename))
    self.args = out_args
    return output_filename

  def process_remote_args(self, remote_output_filename):
    """Process arguments specifically for remote commands.

    Args:
      remote_output_filename: Output filename on the remote device.

    Returns:
      The local output filename string or an empty string if this doesn't
      reference the record command.
    """
    if self.command not in ('record', 'top', 'stat'):
      return ''
    # Use -m 4 due to certain devices not having mmap data pages.
    if self.command == 'record':
      self.args.extend(('-m', '4'))
    return self.get_output_filename(remote_output_filename)


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
  arch_paths = []
  if adb_device:
    target_architectures = get_target_architectures(adb_device)
    for api_level in range(adb_device.get_api_level(),
                           PERF_MIN_API_LEVEL - 1, -1):
      arch_paths.extend([os.path.join('android-%d' % api_level,
                                      '-'.join(('arch', arch)))
                         for arch in target_architectures])
  arch_paths.append('')
  for arch_path in arch_paths:
    for search_path in TARGET_BINARY_SEARCH_PATHS:
      binary_path = os.path.join(search_path, arch_path, name)
      if os.path.exists(binary_path):
        return binary_path
  raise BinaryNotFoundError('Unable to find Android %s binary %s' % (
      arch_paths[0], name))


def find_host_binary(name, adb_device=None):
  """Find the path of the specified host binary.

  Args:
    name: The name of the binary to find.
    adb_device: Device connected to the host, if this is None this function
      will search for device specific binaries in the most recent API
      directory.

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

  # Get the set of compatible architectures for the current OS.
  search_paths = []
  os_name, architectures = get_host_os_name_architecture()
  os_dirs = ['-'.join((os_name, arch)) for arch in architectures]

  # Get the list of API levels to search.
  api_level_dir_prefix = 'android-'
  api_levels = []
  if adb_device:
    api_levels = range(adb_device.get_api_level(), PERF_MIN_API_LEVEL - 1, -1)
  else:
    api_levels = [int(filename[api_level_dir_prefix:])
                  for filename in os.listdir(PERF_TOOLS_BIN_DIRECTORY) if
                  filename.startswith(api_level_dir_prefix)]

  # Build the list of OS specific search paths.
  os_paths = []
  for api_level in api_levels:
    for os_dir in os_dirs:
      os_paths.append(os.path.join('%s%d' % (api_level_dir_prefix, api_level),
                                   os_dir))
  search_paths.extend(os_paths)

  # Finally queue a search of the root directory of the host search path.
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
                          verbose=False, keyboard_interrupt_success=False,
                          catch_sigint=True, ignore_error=False):
  """Execute a command and throw an exception on failure.

  Args:
    command_str: The command to be executed.
    error: The message to print when failing.
    display_output_on_error: Display the command output if it fails.
    verbose: Whether to display excecuted commands.
    keyboard_interrupt_success: Whether the keyboard interrupt generates
      a command failure.
    catch_sigint: Whether to catch sigint (keyboard interrupt).
    ignore_error: Ignore errors running this command.

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

  # TODO(smiles): This isn't going to work on Windows, fix it.
  interrupt_signal = signal.SIGINT
  if catch_sigint:
    sigint = SignalHandler()
    sigint.acquire(interrupt_signal)

  # TODO(smiles): Can all of the commands be executed *without* the shell?
  # Stuff will become far easier to deal with.

  # TODO(smiles): Escape command string for local shell (e.g cmd vs. bash)
  process = subprocess.Popen(command_str, shell=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  # TODO(smiles): Add option to send output in real-time here.
  out, err = process.communicate()

  kbdint = False
  if catch_sigint:
    kdbint = sigint.called
    if kdbint and keyboard_interrupt_success:
      process.returncode = 0
    sigint.release()

  if process.returncode and not ignore_error:
    if display_output_on_error:
      print out
      print >> sys.stderr, err
    raise CommandFailedError(error, process.returncode)
  return (out, err, kbdint)


def run_perf_remotely(adb_device, apk_directory, perf_args):
  """Run perf remotely.

  Args:
    adb_device: The device that perf is run on.
    apk_directory: The directory of the apk file to profile.
    perf_args: PerfArgs instance referencing the arguments used to run perf.

  Returns:
    1 for error, 0 for success.

  # TODO(smiles): Change this to raise on error.
  """
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

  # Push perf and wrapper script to the device.
  android_perf = find_target_binary('perf', adb_device)
  android_perf_remote = os.path.join(REMOTE_TEMP_DIRECTORY,
                                     os.path.basename(android_perf))
  adb_device.push_files([(android_perf, android_perf_remote)])

  # Get the output filename and mangle the arguments to run perf remotely.
  output_filename = perf_args.get_output_filename()
  perf_data = '/'.join([Adb.get_package_data_directory(package_name),
                        os.path.basename(output_filename)])
  perf_args.process_remote_args(perf_data)

  try:
    if perf_args.requires_process():
      # TODO(smiles): Parse the main activity name from the package.
      pid = adb_device.start_activity(package_name,
                                      'android.app.NativeActivity')

      # Run perf in a separate thread so that the process can be stopped from
      # the main thread.
      class PerfThread(threading.Thread):
        def __init__(self, adb, command_line):
          super(PerfThread, self).__init__()
          self.adb = adb
          self.command_line = command_line
          self.stdout = ''
          self.stderr = ''
          self.returncode = 0

        def run(self):
          try:
            self.stdout, self.stderr, _ = self.adb.shell_command(
                self.command_line, 'Unable to execute perf record on device.',
                catch_sigint=False)
          except CommandFailedError as e:
            self.returncode = e.returncode

      # Start perf in a seperate thread so that it's possible to relay signals
      # to the remote process from the main thread.
      perf_thread = PerfThread(
          adb_device, ' '.join([
              'run-as', package_name, android_perf_remote,
              ' '.join(perf_args.args), '-p %d' % pid]))
      perf_thread.start()

      keyboard_interrupt = False
      try:
        # Wait for the thread to complete or SIGINT (ctrl-c).
        perf_thread.join()
      except KeyboardInterrupt:
        keyboard_interrupt = True
        adb_device.shell_command(
            r'pkg_user=\$(ps | grep %(pkg)s | while read l; do '
            r'  t=( \${l} ); echo \${t[0]}; break; done); '
            r'pid=( \$(ps | grep \"\${pkg_user}.* %(perf)s\") ); '
            r'echo \"kill -s SIGINT \${pid[1]}\" | run-as %(pkg)s sh' % {
                'pkg': package_name, 'perf': android_perf_remote},
            'Unable to stop %s' % android_perf_remote)

      # If a keyboard interrupt occurred, ignore the status code.
      if keyboard_interrupt:
        perf_thread.join()
        perf_thread.stdout = 0

      if output_filename:
        adb_device.pull_package_file(package_name, perf_data, output_filename)
        # TODO(smiles): Use local perf report to determine which libraries
        # need to be pulled from the device in order to properly annotate
        # samples.
    else:
      out, _, _ = adb_device.shell_command(
          '%s %s' % (android_perf_remote, ' '.join(perf_args)),
          'Unable to execute perf %s on device.' % perf_args.command)
      # TODO(smiles): Move this input execute_local_command()
      print out

  finally:
    # Remove temporary files from the device.
    temporary_files = ' '.join((android_perf_remote, perf_data))
    adb_device.shell_command(
        ''.join(('rm -f %s' % android_perf_remote,
                 '; run-as %s rm -f %s' % (package_name, perf_data)
                 if perf_data else '')),
        'Unable to remove temporary files %s from the device.' % (
            temporary_files))
  return 0


def run_perf_visualizer(browser, perf_args, adb_device, verbose=False):
  """Generate the visualized html.

  Args:
    browser: The browser to use for display
    perf_args: The arguments to run the visualizer with.
    adb_device: Device used to determine which perf binary should be used.
    verbose: Whether to display all shell commands executed by this function.

  Returns:
    1 for error, 0 for success
  """
  perf_host = find_host_binary(PERFHOST_BINARY, adb_device)
  perf_to_tracing = find_host_binary('perf_to_tracing_json.py')
  perf_vis = find_host_binary('perf-vis.py')

  # Output samples and stacks while including specific attributes that are
  # read by the visualizer
  out, _, _ = execute_local_command(
      '%s script -f comm,tid,time,cpu,event,ip,sym,dso,period' % perf_host,
      'Cannot visualize perf data. Please run record using -R',
      verbose=verbose)

  # TODO(smiles): Replace with temporary file
  SCRIPT_OUTPUT = 'perf_script.txt'
  # TODO(smiles): Replace with temporary file
  JSON_OUTPUT = 'perf_json.json'

  with open(SCRIPT_OUTPUT, 'w') as f:
    f.write(out)

  # Generate a common json format from the outputted sample data
  out, _, _ = execute_local_command('%s perf_script.txt' % perf_to_tracing, '',
                                    verbose=verbose)

  with open(JSON_OUTPUT, 'w') as f:
    f.write(out)

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

  See the module doc string for more information.

  Returns:
    0 if successful, 1 otherwise.
  """
  parser = argparse.ArgumentParser(
      description=re.sub(r'^@file [^ ]* ', '', __doc__),
      formatter_class=argparse.RawDescriptionHelpFormatter, add_help=False)
  parser.add_argument('--adb-device',
                      help=('The serial_number of the device to profile if '
                            'multiple Android devices are connected to the '
                            'host.'))
  parser.add_argument('--apk-directory',
                      help='The directory of the package to profile.')
  parser.add_argument('--browser',
                      help='Web browser to use for visualization.')
  parser.add_argument('--verbose', help='Display verbose output.',
                      action='store_true', default=False)

  args, perf_arg_list = parser.parse_known_args()
  verbose = args.verbose

  # Parse perf arguments.
  try:
    perf_args = PerfArgs(perf_arg_list, verbose)
  except PerfArgs.Error as e:
    print >> sys.stderr, str(e)
    return 1

  # Construct a class to communicate with the ADB device.
  try:
    adb_device = Adb(args.adb_device, verbose)
  except Adb.Error, error:
    print >> sys.stderr, os.linesep.join([
        str(error), 'Try specifying a device using --adb-device <serial>.'])
    return 1

  # Preprocess perf arguments.
  perf_args.insert_symfs_dir(os.path.dirname(
      perf_args.get_output_filename()))

  # If requested, display the help text and exit.
  if perf_args.get_help_enabled():
    parser.print_help()
    out, err, _ = execute_local_command(
        '%s %s' % (find_host_binary(PERFHOST_BINARY, adb_device),
                   ' '.join(perf_args.args)),
        'Unable to get %s help' % PERFHOST_BINARY, verbose=verbose,
        ignore_error=True)
    perf_command = 'perf help%s' % (
        ' %s' % perf_args.command if perf_args.command != 'help' else '')
    print os.linesep.join(('', perf_command +
                           ('-' * (80 - len(perf_command))), out + err))
    return 1

  if perf_args.command == 'visualize':
    # TODO(smiles): Move into a function which retrieves the browser.
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
      print CHROME_NOT_FOUND % browser_name

    return run_perf_visualizer(browser, perf_args.args[1:], adb_device)

  try:
    # Run perf remotely
    if perf_args.run_remote():
      android_version = adb_device.get_version()
      if is_version_less_than(android_version, '4.1'):
        print >> sys.stderr, PERF_BINARIES_NOT_SUPPORTED % {
            'ver': android_version}
      (model, name) = adb_device.get_model_and_name()
      if name in BROKEN_DEVICES:
        print >> sys.stderr, PERFORMANCE_COUNTERS_BROKEN % model
      elif name not in SUPPORTED_DEVICES:
        print >> sys.stderr, NOT_SUPPORTED_DEVICE % model
      user, _, _ = adb_device.shell_command(r'echo \${USER}',
                                            'Unable to get Android user name')
      if perf_args.requires_root() and user != 'root':
        print >> sys.stderr, DEVICE_NOT_ROOTED % perf_args.command

      return run_perf_remotely(adb_device, args.apk_directory, perf_args)
    # Run perf locally
    else:
      execute_local_command(
          '%s %s' % (find_host_binary(PERFHOST_BINARY, adb_device),
                     ' '.join(perf_args.args)),
          'Failed to execute %s' % PERFHOST_BINARY, verbose=verbose)

  except CommandFailedError, error:
    print >> sys.stderr, str(error)
    return error.returncode
  return 0

if __name__ == '__main__':
  sys.exit(main())
