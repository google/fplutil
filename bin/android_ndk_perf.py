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

Detailed usage: android_ndk_perf.py [options] perf_command [perf_arguments]

perf_command can be any valid command for the Linux perf tool or
"visualize" to display a visualization of the performance report.

Caveats:
* "stat" and "top" require root access to the target device.
* "record" is *not* able to annotate traces with symbols from samples taken
  in the kernel without root access to the target device.
"""

import argparse
import distutils.spawn
import os
import platform
import re
import signal
import subprocess
import sys
import tempfile
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
    os.path.join(PERF_TOOLS_DIRECTORY, 'tools', 'telemetry', 'telemetry',
                 'core', 'platform', 'profiler', 'perf_vis'),
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

## Binary which converts from a perf trace to JSON.
PERF_TO_TRACING = 'perf_to_tracing_json.py'

## Binary visualizes JSON output of PERF_TO_TRACING using HTML.
PERF_VIS = 'perf-vis.py'

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
WARNING: %s is not Google Chrome and therefore may not be able
to display the performance data.
"""

## Regular expression which matches the libraries referenced by
## "perf buildid-list --with-hits -i ${input_file}".
PERF_BUILDID_LIST_MATCH_OBJ_RE = re.compile(r'^[^ ]* ([^\[][^ ]*[^\]])')

## Regular expression which extracts the supported fields from
## "perf script -h".
PERF_SCRIPT_HELP_FIELDS = re.compile(r'.*-f.*--fields.*Fields: (.*)')

## Regular expression which extracts fields from an event in
## run_perf_visualizer().
PERF_REPORT_EVENT_RE = re.compile(r'^(.*)\s+(\d+)\s+(\d+\.\d+):\s([^:]+):.*')

## Regular expression which extracts fields from a stack track in
## run_perf_visualizer().
PERF_REPORT_STACK_RE = re.compile(r'^\s+([0-9a-zA-Z]+)\s+(.*)\s+(\(.*\))$')

## Regular expression which extracts the output html filename from PERF_VIS.
PERF_VIS_OUTPUT_FILE_RE = re.compile(r'.*output:\s+(.*\.html).*')


class Error(Exception):
  """General error thrown by this module."""
  pass


class CommandFailedError(Error):
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
    adb_path: Path to the ADB executable.
    command_handler: Callable which executes subprocesses.  See
      execute_command().

  Class Attributes:
    _MATCH_DEVICES: Regular expression which matches connected devices.
    _MATCH_PROPERTY: Regular expression which matches properties returned by
      the getprop shell command.
  """

  class Error(Exception):
    """Thrown when the Adb object detects an error."""
    pass

  class ShellCommand(object):
    """Callable object which can be used to run shell commands.

    Attributes:
      adb: Adb instance to relay shell commands to.
    """

    def __init__(self, adb):
      """Initialize this instance.

      Args:
        adb: Adb instance to relay shell commands to.
      """
      self.adb = adb

    def __call__(self, executable, executable_args, error, **kwargs):
      """Run a shell command on the device associated with this instance.

      Args:
        executable: String added to the start of the command line.
        executable_args: List of strings that are joined with whitespace to
          form the shell command.
        error: The message to print if the command fails.
        **kwargs: Keyword arguments passed to the command_handler attribute.

      Returns:
        (stdout, stderr, kbdint) where stdout is a string containing the
        standard output stream and stderr is a string containing the
        standard error stream and kbdint is whether a keyboard interrupt
        occurred.
      """
      args = [executable]
      args.extend(executable_args)
      return self.adb.shell_command(' '.join(args), error, **kwargs)

  _MATCH_DEVICES = re.compile(r'^(List of devices attached\s*\n)|(\n)$')
  _MATCH_PROPERTY = re.compile(r'^\[([^\]]*)\]: *\[([^\]]*)\]$')

  def __init__(self, serial, command_handler, adb_path=None, verbose=False):
    """Initialize this instance.

    Args:
      serial: Device serial number to connect to.  If this is an empty
        string this class will use the first device connected if only one
        device is connected.
      command_handler: Callable which executes subprocesses.  See
        execute_local_command().
      adb_path: Path to the adb executable.  If this is None the PATH is
        searched.
      verbose: Whether to display all shell commands run by this class.

    Raises:
      Adb.Error: If multiple devices are connected and no device is selected,
        no devices are connected or ADB can't be found.
    """
    self.cached_properties = {}
    self.verbose = verbose
    self.command_handler = command_handler
    self.adb_path = (adb_path if adb_path else
                     distutils.spawn.find_executable('adb'))
    if not self.adb_path:
      raise Adb.Error('Unable to find adb executable, '
                      'is the ADT platforms-tools directory in the PATH?')
    self.serial = serial

  def _run_command(self, command, command_args, error, add_serial, **kwargs):
    """Run an ADB command for a specific device.

    Args:
      command: Command to execute.
      command_args: Arguments to pass to the command.
      error: The message to print if the command fails.
      add_serial: Add the device serial number to ADB's arguments.  This should
        only be used with command that operate on a single device.
      **kwargs: Keyword arguments passed to "command_handler".

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
    args = []
    if add_serial and self.serial:
      args.extend(('-s', self.serial))
    args.append(command)
    args.extend(command_args)
    return self.command_handler(self.adb_path, args, error, **kwargs)

  def run_command(self, command, command_args, error, **kwargs):
    """Run an ADB command for a specific device.

    Args:
      command: Command to execute.
      command_args: Arguments to pass to the command.
      error: The message to print if the command fails.
      **kwargs: Keyword arguments passed to "command_handler".

    Returns:
      (stdout, stderr, kbdint) where stdout is a string containing the
      standard output stream and stderr is a string containing the
      standard error stream and kbdint is whether a keyboard interrupt
      occurred.

    Raises:
      CommandFailedError: If the command fails.
    """
    return self._run_command(command, command_args,
                             '%s (device=%s)' % (error, str(self)), True,
                             **kwargs)

  def run_global_command(self, command, command_args, error, **kwargs):
    """Run an ADB command that does not operate on an individual device.

    Args:
      command: Command to execute.
      command_args: Arguments to pass to the command.
      error: The message to print if the command fails.
      **kwargs: Keyword arguments passed to "command_handler".

    Returns:
      (stdout, stderr, kbdint) where stdout is a string containing the
      standard output stream and stderr is a string containing the
      standard error stream and kbdint is whether a keyboard interrupt
      occurred.

    Raises:
      CommandFailedError: If the command fails.
    """
    return self._run_command(command, command_args, error, False, **kwargs)

  def shell_command(self, command, error, **kwargs):
    """Run a shell command on the device associated with this instance.

    Args:
      command: Command to execute in the remote shell.
      error: The message to print if the command fails.
      **kwargs: Keyword arguments passed to "command_handler".

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
        'shell', [command + r'; echo $? >&2'], error, **kwargs)
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
    if returncode and not kwargs.get('display_output'):
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
    out, _, _ = self.run_global_command(
        'devices', ['-l'], 'Unable to get the list of connected devices.')
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
                     r'fields=( $(ps | grep -F %s) )' % package,
                     r'echo ${fields[1]}']),
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
    self.run_command('push', [local_file, remote_path],
                     'Unable to push %s to %s' % (local_file, remote_path))

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

  def pull(self, remote_path, local_file):
    """Pull a remote file to the host.

    Args:
      remote_path: Path on the device.
      local_file: Path to the file on the host.  If the directories to the
        local file don't exist, they're created.

    Raises:
      CommandFailedError: If the pull fails.
    """
    local_dir = os.path.dirname(local_file)
    if not os.path.exists(local_dir):
      os.makedirs(local_dir)
    self.run_command('pull', [remote_path, local_file],
                     'Unable to pull %s to %s' % (remote_path, local_file))

  def pull_files(self, remote_local_paths):
    """Pull a set of remote files to the host.

    Args:
      remote_local_paths: List of (remote, local) tuples where "remote" is the
        source location on the device and "local" is the host path to copy to.

    Raises:
      CommandFailedError: If the pull fails.
    """
    for remote, local in remote_local_paths:
      self.pull(remote, local)

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
    self.run_command('pull', [package_file, output_file],
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


class PerfArgsCommand(object):
  """Properties of a perf command.

  Attributes:
    name: Name of the command.
    sub_commands: Dictionary of sub-commands in the form of
      PerfArgsCommand instances indexed by sub-command name.
    value_options: List of value options that need to be skipped when
      determining the sub-command.
    verbose: Whether the command supports the verbose option.
    remote: Whether the command needs to be executed on a remote device.
    real_command: Whether this is a real perf command.
    output_filename: Default output filename for this command or '' if
      the command doesn't write to a file.
    input_filename: Default input filename for this command or '' if
      the command doesn't read from a file.
  """

  def __init__(self, name, sub_commands=None, value_options=None,
               verbose=False, remote=False, real_command=True,
               output_filename='', input_filename=''):
    """Initialize this instance.

    Args:
      name: Name of the command.
      sub_commands: List of sub-commands in the form of
        PerfArgsCommand instances.
      value_options: List of value options that need to be skipped when
        determining the sub-command.
      verbose: Whether the command supports the verbose option.
      remote: Whether the command needs to be executed on a remote device.
      real_command: Whether this is a real perf command.
      output_filename: Default output filename for this command or '' if
        the command doesn't write to a file.
      input_filename: Default input filename for this command or '' if
        the command doesn't read from a file.
    """
    self.name = name
    self.sub_commands = (dict([(cmd.name, cmd) for cmd in sub_commands]) if
                         sub_commands else {})
    self.value_options = value_options if value_options else []
    self.verbose = verbose
    self.remote = remote
    self.real_command = real_command
    self.input_filename = input_filename
    self.output_filename = output_filename

  def __str__(self):
    """Get the name of the command.

    Returns:
      Name of the command.
    """
    return self.name


class PerfArgs(object):
  """Class which parses and processes arguments to perf.

  Attributes:
    initial_args: Arguments the instance is initialized with.
    args: Arguments that have been modified by methods of this class.
    command: Primary perf command as a PerfArgsCommand instance.
    sub_command: PerfArgsCommand instance of the secondary command
      if provided, None otherwise.

  Class Attributes:
    SUPPORTED_COMMANDS: List of PerfArgsCommand instances, one for each
      command that *should* work with perf on Android.  Not all commands have
      been tested
    SUPPORTED_COMMANDS_DICT: Dictionary populated from SUPPORTED_COMMANDS.
  """

  class Error(Exception):
    """Thrown if a problem is found parsing perf arguments."""
    pass

  SUPPORTED_COMMANDS = [
      PerfArgsCommand('annotate', verbose=True, input_filename='perf.data'),
      # May not be compiled in.
      PerfArgsCommand('archive', remote=True),
      # May not be compiled in.
      PerfArgsCommand('bench', remote=True),
      PerfArgsCommand('buildid-cache', verbose=True),
      PerfArgsCommand('buildid-list', verbose=True,
                      input_filename='perf.data'),
      PerfArgsCommand('diff', verbose=True),
      PerfArgsCommand('evlist', input_filename='perf.data'),
      PerfArgsCommand('help'),
      PerfArgsCommand('inject', verbose=True),
      PerfArgsCommand('kmem',
                      sub_commands=(PerfArgsCommand('record'),
                                    PerfArgsCommand('stat', remote=True)),
                      value_options=('-i', '--input', '-s', '--sort',
                                     '-l', '--line'),
                      input_filename='perf.data'),
      PerfArgsCommand('list', remote=True),
      PerfArgsCommand(
          'lock',
          sub_commands=(PerfArgsCommand('record', remote=True,
                                        output_filename='perf.data'),
                        PerfArgsCommand('trace', input_filename='perf.data'),
                        PerfArgsCommand('report', input_filename='perf.data')),
          value_options=('-i', '--input'), verbose=True),
      PerfArgsCommand('probe', verbose=True, remote=True),
      PerfArgsCommand('record', verbose=True, remote=True,
                      output_filename='perf.data'),
      PerfArgsCommand('report', verbose=True, input_filename='perf.data'),
      PerfArgsCommand('sched',
                      sub_commands=(PerfArgsCommand('record', remote=True),
                                    PerfArgsCommand('latency'),
                                    PerfArgsCommand('map'),
                                    PerfArgsCommand('replay'),
                                    PerfArgsCommand('trace')),
                      value_options=('-i', '--input'), verbose=True,
                      input_filename='perf.data'),
      PerfArgsCommand('script',
                      sub_commands=(PerfArgsCommand('record', remote=True),
                                    PerfArgsCommand('report')),
                      value_options=('-s', '--script', '-g', '--gen-script',
                                     '-i', '--input', '-k', '--vmlinux',
                                     '--kallsyms', '--symfs'), verbose=True,
                      input_filename='perf.data'),
      PerfArgsCommand('stat', output_filename='perf.data'),
      # May not be compiled in.
      PerfArgsCommand('test'),
      PerfArgsCommand('timechart',
                      sub_commands=(PerfArgsCommand('record'),),
                      value_options=('-i', '--input', '-o', '--output',
                                     '-w', '--width', '-p', '--process',
                                     '--symfs'),
                      output_filename='output.svg',
                      input_filename='perf.data'),
      PerfArgsCommand('top', verbose=True),
      # Specific to this script.
      PerfArgsCommand('visualize', real_command=False,
                      input_filename='perf.data')]

  SUPPORTED_COMMANDS_DICT = dict([(cmd.name, cmd)
                                  for cmd in SUPPORTED_COMMANDS])

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
    command_arg = self.args[0] if self.args else 'help'
    self.command = PerfArgs.SUPPORTED_COMMANDS_DICT.get(command_arg)
    if not self.command:
      raise PerfArgs.Error('Unsupported perf command %s' % command_arg)
    if self.command.verbose and verbose:
      self.args.append('--verbose')
    self.sub_command = self.get_sub_command()

  def get_sub_command(self):
    """Get the sub-command for the current command if applicable.

    Returns:
      PerfArgsCommand instance for the sub-command of the current command.  If
      a sub-command isn't found None is returned.
    """
    if len(self.args) > 2:
      index = 1
      arg = self.args[1]
      while index < len(self.args):
        arg = self.args[index]
        if not arg.startswith('-'):
          break
        if arg in self.command.value_options:
          index += 1
        index += 1
      return self.command.sub_commands.get(arg)
    return None

  def requires_root(self):
    """Determines whether the perf command requires a rooted device.

    Returns:
      True if the command requires root, False otherwise.
    """
    if self.command.name == 'top' and not [
        arg for arg in self.args[1:] if arg in ('-p', '-t', '-u')]:
      return True
    return False

  def requires_remote(self):
    """Determine whether the perf command needs to run on a remote device.

    Returns:
      True if perf should be run on an Android device, False otherwise.
    """
    return self.command.remote or (self.sub_command and
                                   self.sub_command.remote)

  def insert_process_option(self, pid):
    """Inserts a process option into the argument list.

    Inserts a process option into the argument list if the command accepts
    a process ID.

    Args:
      pid: Process ID to add to the argument list.
    """
    if (self.command.name in ('record', 'stat', 'top') or
        (self.command.name == 'script' and
         self.sub_command and self.sub_command.name == 'record')):
      self.args.extend(('-p', str(pid)))

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
      elif arg == '--help' and index + 1 == len(args):
        out_args.append('-h')
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
    if not symbols_dir or self.command.name not in (
        'annotate', 'diff', 'report', 'script', 'timechart', 'visualize'):
      return
    if '--symfs' in self.args:
      return
    out_args = list(self.args)
    out_args.extend(('--symfs', symbols_dir))
    self.args = out_args

  def parse_value_option(self, options):
    """Parse an argument with a value from the current argument list.

    Args:
      options: List of equivalent option strings (e.g '-o' and '--output') that
        are followed by the value to be retrieved.

    Returns:
      The index of the value argument in the 'args' attribute or -1 if it's
      not found.
    """
    index = -1
    for i, arg in enumerate(self.args):
      if arg in options and i < len(self.args) - 1:
        index = i + 1
        break
    return index

  def get_default_output_filename(self):
    """Get the default output filename for the current command.

    Returns:
      String containing the default output filename for the current command
      if the command results in an output file, empty string otherwise.
    """
    for command in (self.command, self.sub_command):
      if command and command.output_filename:
        return command.output_filename
    return ''

  def get_output_filename(self, remote_output_filename=''):
    """Parse output filename from perf arguments.

    Args:
      remote_output_filename: If this is a non-zero length string it replaces
        the current output filename in the arguments.

    Returns:
      Original output filename string.
    """
    output_filename = self.get_default_output_filename()
    if not output_filename:
      return ''

    index = self.parse_value_option(['-o'])
    if index >= 0:
      output_filename = self.args[index]
      if remote_output_filename:
        self.args[index] = remote_output_filename
    elif remote_output_filename:
      self.args.extend(('-o', remote_output_filename))
    return output_filename

  def get_default_input_filename(self):
    """Get the default input filename for the current command.

    Returns:
      String containing the default input filename for the current command
      if the command results in an input file, empty string otherwise.
    """
    for command in (self.command, self.sub_command):
      if command and command.input_filename:
        return command.input_filename
    return ''

  def get_input_filename(self):
    """Parse input filename from perf arguments.

    Returns:
      Input filename string if found in the arguments or the default input
      filename for the command.
    """
    index = self.parse_value_option(['-i'])
    return (self.args[index] if index >= 0 else
            self.get_default_input_filename())

  def process_remote_args(self, remote_output_filename,
                          call_graph_recording, timestamp_recording):
    """Process arguments specifically for remote commands.

    Args:
      remote_output_filename: Output filename on the remote device.
      call_graph_recording: Enable recording of call graphs.
      timestamp_recording: Enable recording of time stamps.

    Returns:
      The local output filename string or an empty string if this doesn't
      reference the record command.
    """
    if self.command.name not in ('record', 'top', 'stat'):
      return ''
    # Use -m 4 due to certain devices not having mmap data pages.
    if self.command.name == 'record':
      self.args.extend(('-m', '4'))
    if call_graph_recording:
      self.args.append('-g')
    if timestamp_recording:
      self.args.append('-T')
    return self.get_output_filename(remote_output_filename)


class ThreadedReader(threading.Thread):
  """Reads a file like object into a string from a thread.

  This also optionally writes data read to an output file.

  Attributes:
    read_file: File to read.
    output_file: If this isn't None, data read from read_file will be written
      to this file.
    read_lines: List of line strings read from the file.
  """

  def __init__(self, read_file, output_file):
    """Initialize this instance.

    Args:
      read_file: File to read.
      output_file: If this isn't None, data read from read_file will be written
        to this file.
    """
    super(ThreadedReader, self).__init__()
    self.read_file = read_file
    self.output_file = output_file
    self.read_lines = []

  def run(self):
    """Capture output from read_file into read_string."""
    while True:
      line = self.read_file.readline()
      if not line:
        break
      self.read_lines.append(line)
      if self.output_file:
        self.output_file.write(line)

  def __str__(self):
    """Get the string read from the file.

    Returns:
      String read from the file.
    """
    return ''.join(self.read_lines)


class CommandThread(threading.Thread):
  """Runs a command in a separate thread.

  Attributes:
    command_handler: Callable which implements the same interface as
      execute_command() used to run the command from this thread.
    executable: String path to the executable to run.
    executable_args: List of string arguments to pass to the executable.
    error: Error string to pass to the command_handler.
    kwargs: Keyword arguments to pass to the command handler.
    stdout: String containing the standard output of the executed command.
    stderr: String containing the standard error output of the executed
      command.
    returncode: Return code of the command.
  """

  def __init__(self, command_handler, executable, executable_args, error,
               **kwargs):
    """Initialize the instance.

    Args:
      command_handler: Callable which implements the same interface as
        execute_command() used to run the command from this thread.
      executable: String path to the executable to run.
      executable_args: List of string arguments to pass to the executable.
      error: Error string to pass to the command_handler.
      **kwargs: Keyword arguments to pass to the command handler.
    """
    super(CommandThread, self).__init__()
    self.command_handler = command_handler
    self.executable = executable
    self.executable_args = executable_args
    self.error = error
    self.stdout = ''
    self.stderr = ''
    self.returncode = 0
    self.kwargs = kwargs

  def run(self):
    """Execute the command."""
    # Signals can only be caught from the main thread so disable capture.
    kwargs = dict(self.kwargs)
    kwargs['catch_sigint'] = False
    try:
      self.stdout, self.stderr, _ = self.command_handler(
          self.executable, self.executable_args, self.error, **kwargs)
    except CommandFailedError as e:
      self.returncode = e.returncode


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
    api_levels = [int(filename[len(api_level_dir_prefix):])
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

  searched_paths = []
  for arch_path in search_paths:
    for search_path in HOST_BINARY_SEARCH_PATHS:
      for exe_extension in exe_extensions:
        binary_path = (os.path.join(search_path, arch_path, name) +
                       exe_extension)
        searched_paths.append(binary_path)
        if os.path.exists(binary_path):
          return binary_path
  raise BinaryNotFoundError('Unable to find host binary %s in %s' % (
      name, os.linesep.join(searched_paths)))


def execute_command(executable, executable_args, error,
                    display_output_on_error=True,
                    verbose=False, keyboard_interrupt_success=False,
                    catch_sigint=True, ignore_error=False,
                    display_output=False):
  """Execute a command and throw an exception on failure.

  Args:
    executable: String path to the executable to run.
    executable_args: List of string arguments to pass to the executable.
    error: The message to print when failing.
    display_output_on_error: Display the command output if it fails.
    verbose: Whether to display excecuted commands.
    keyboard_interrupt_success: Whether the keyboard interrupt generates
      a command failure.
    catch_sigint: Whether to catch sigint (keyboard interrupt).
    ignore_error: Ignore errors running this command.
    display_output: Display the output stream.

  Returns:
    (stdout, stderr, kbdint) where stdout is a string containing the
    standard output stream and stderr is a string containing the
    standard error stream and kbdint is whether a keyboard interrupt
    occurred.

  Raises:
    CommandFailedError: An error occured running the command.
  """
  if verbose:
    print >> sys.stderr, ' '.join((
        executable, ' '.join(['"%s"' % a for a in executable_args])))

  # TODO(smiles): This isn't going to work on Windows, fix it.
  interrupt_signal = signal.SIGINT
  if catch_sigint:
    sigint = SignalHandler()
    sigint.acquire(interrupt_signal)

  try:
    process = subprocess.Popen([executable] + executable_args,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  except OSError, e:
    raise CommandFailedError(' '.join((str(e), error)), 1)

  # Read output of the command and optionally mirror the captured stdout and
  # stderr streams to stderr and stdout respectively.
  stdout, stderr = ((sys.stdout, sys.stderr) if display_output else
                    (None, None))
  stdout_reader = ThreadedReader(process.stdout, stdout)
  stdout_reader.start()
  stderr_reader = ThreadedReader(process.stderr, stderr)
  stderr_reader.start()
  stdout_reader.join()
  stderr_reader.join()
  process.wait()

  kbdint = False
  if catch_sigint:
    kdbint = sigint.called
    if kdbint and keyboard_interrupt_success:
      process.returncode = 0
    sigint.release()

  if process.returncode and not ignore_error:
    if display_output_on_error and not display_output:
      print str(stdout_reader)
      print >> sys.stderr, str(stderr_reader)
    raise CommandFailedError(error, process.returncode)
  return (str(stdout_reader), str(stderr_reader), kbdint)


def run_perf_remotely(adb_device, apk_directory, perf_args,
                      call_graph_recording, timestamp_recording):
  """Run perf remotely.

  Args:
    adb_device: The device that perf is run on.
    apk_directory: The directory of the apk file to profile.
    perf_args: PerfArgs instance referencing the arguments used to run perf.
    call_graph_recording: Whether to enable recording of call graphs.
    timestamp_recording: Whether to enable recording of timestamps.

  Returns:
    1 for error, 0 for success.

  # TODO(smiles): Change this to raise on error.
  """
  # TODO(smiles): Optionally install the apk on the device.
  # TODO(smiles): Optionally profile a package by name on the device.
  # TODO(smiles): Read main activity and package name from APK using aapt.
  package_name = ''
  if apk_directory:
    manifest_filename = os.path.join(apk_directory, MANIFEST_NAME)
    if not os.path.isfile(manifest_filename):
      print >> sys.stderr, (
          'Cannot find Manifest %s, please specify the directory where the '
          'manifest is located with --apk-directory.') % manifest_filename
      return 1
    package_name = get_package_name_from_manifest(manifest_filename)

  # Push perf and wrapper script to the device.
  android_perf = find_target_binary('perf', adb_device)
  android_perf_remote = os.path.join(REMOTE_TEMP_DIRECTORY,
                                     os.path.basename(android_perf))
  adb_device.push_files([(android_perf, android_perf_remote)])

  # Get the output filename and mangle the arguments to run perf remotely.
  output_filename = perf_args.get_output_filename()
  if package_name:
    perf_data = '/'.join([Adb.get_package_data_directory(package_name),
                          os.path.basename(output_filename)])
  else:
    perf_data = output_filename
  perf_args.process_remote_args(perf_data, call_graph_recording,
                                timestamp_recording)

  try:
    if package_name:
      # TODO(smiles): Parse the main activity name from the package.
      perf_args.insert_process_option(
          adb_device.start_activity(package_name,
                                    'android.app.NativeActivity'))

      # Start perf in a seperate thread so that it's possible to relay signals
      # to the remote process from the main thread.
      perf_thread = CommandThread(
          Adb.ShellCommand(adb_device), 'run-as',
          [package_name, android_perf_remote, ' '.join(perf_args.args)], '',
          display_output=True)
      perf_thread.start()

      keyboard_interrupt = False
      try:
        # Wait for the thread to complete or SIGINT (ctrl-c).
        perf_thread.join()
      except KeyboardInterrupt:
        print >> sys.stderr, 'Finishing, please wait..'
        keyboard_interrupt = True
        adb_device.shell_command(
            r'pkg_user=$(ps | grep %(pkg)s | while read l; do '
            r'  t=( ${l} ); echo ${t[0]}; break; done); '
            r'pid=( $(ps | grep "${pkg_user}.* %(perf)s") ); '
            r'echo "kill -s SIGINT ${pid[1]}" | run-as %(pkg)s sh' % {
                'pkg': package_name, 'perf': android_perf_remote},
            'Unable to stop %s' % android_perf_remote)

      # If a keyboard interrupt occurred, ignore the status code.
      if keyboard_interrupt:
        perf_thread.join()
        perf_thread.stdout = 0

      if output_filename:
        # Create the output directory if it doesn't exist.
        output_directory = os.path.dirname(output_filename)
        if output_directory and not os.path.exists(output_directory):
          os.makedirs(output_directory)

        adb_device.pull_package_file(package_name, perf_data, output_filename)

        if (os.path.splitext(perf_args.get_default_output_filename())[1] ==
            '.data'):
          # Parse dependencies from the trace.
          out, _, _ = execute_command(
              find_host_binary(PERFHOST_BINARY, adb_device),
              ['buildid-list', '-i', output_filename, '--with-hits'],
              'Unable to retrieve the set of dependencies for perf '
              'trace %s' % output_filename, verbose=adb_device.verbose)
          # Pull all dependencies from the device.
          for dep in [s.groups()[0] for s in [
              PERF_BUILDID_LIST_MATCH_OBJ_RE.match(l)
              for l in out.splitlines()] if s]:
            try:
              adb_device.pull(dep, os.path.join(output_directory, dep[1:]))
            except CommandFailedError as e:
              print >> sys.stderr, 'WARNING: ' + str(e)

    else:
      adb_device.shell_command(
          ' '.join((android_perf_remote, ' '.join(perf_args.args))),
          'Unable to execute perf %s on device.' % perf_args.command.name,
          display_output=True)

  finally:
    # Remove temporary files from the device.
    temporary_files = ' '.join((android_perf_remote, perf_data))
    adb_device.shell_command(
        ''.join(('rm -f %s' % android_perf_remote,
                 '; run-as %s rm -f %s' % (package_name, perf_data)
                 if package_name and perf_data else '')),
        'Unable to remove temporary files %s from the device.' % (
            temporary_files), display_output=True)
  return 0


def run_perf_visualizer(browser, perf_args, adb_device, output_filename,
                        verbose):
  """Generate the visualized html.

  Args:
    browser: The browser to use for display
    perf_args: PerfArgs instance which contains arguments used to run the
      visualizer.
    adb_device: Device used to determine which perf binary should be used.
    output_filename: Name of the report file to write to.
    verbose: Whether to display all shell commands executed by this function.

  Returns:
    1 for error, 0 for success

  Raises:
    Error: If an error occurs.
    CommandFailedError: If a command fails to execute.
  """
  perf_host = find_host_binary(PERFHOST_BINARY, adb_device)
  perf_to_tracing = find_host_binary(PERF_TO_TRACING)
  perf_vis = find_host_binary(PERF_VIS)

  # Get the list of support fields from perf.
  out, err, _ = execute_command(perf_host, ['script', '-h'], '',
                                verbose=verbose, ignore_error=True)
  supported_script_fields = None
  for l in (out + err).splitlines():
    m = PERF_SCRIPT_HELP_FIELDS.match(l)
    if m:
      supported_script_fields = set(m.groups()[0].split(','))
  if not supported_script_fields:
    raise Error('Unable to retrieve supported fields from perf script.')

  # Output samples and stacks while including specific attributes that are
  # read by the visualizer.
  symfs_index = perf_args.parse_value_option(['--symfs'])
  perf_script_args_list = [
      'script', '-f', ','.join(('comm',
                                'tid',
                                # 'cpu',  # Need root on Android.
                                'time',
                                'event',
                                'sym')),
      '-i', perf_args.get_input_filename(),
      '--symfs', (perf_args.args[symfs_index] if symfs_index >= 0 else
                  os.dirname(perf_args.get_input_filename()))]

  # If the version of perf supports the ip and dso fields, they'll need to be
  # specified to print stack traces.
  if 'ip' in supported_script_fields and 'dso' in supported_script_fields:
    perf_script_args_list[-1] += ',ip,dso'

  perf_script_args = PerfArgs(perf_script_args_list, verbose)
  out, _, _ = execute_command(perf_host, perf_script_args.args,
                              'Cannot visualize perf data.  '
                              'Try specifying input data using -i.',
                              verbose=verbose)

  # Add fields required by PERF_TO_TRACING that are not supported by the
  # Android version of perf (API level 16-19).
  processed_script_output = []
  event_line = ''
  stack_lines = []
  for line in out.splitlines():
    # Parse event lines.
    if line and not line.startswith('\t'):
      m = PERF_REPORT_EVENT_RE.match(line)
      if not m:
        raise Error('Unexpected format of event line reported by perf script.'
                    ' (%s)' % line)
      comm, tid, time, event = m.groups()
      event_line = '\t'.join([
          comm,
          tid,
          '[000]',
          time + ':',
          event + ':',
          # Sample period, since this isn't stored in perf.data just leave
          # samples normalized.
          # TODO(smiles): Store this is metadata pulled along with the
          # trace from the device.
          '1'])
    elif line.startswith('\t'):
      # This is a stack trace.
      m = PERF_REPORT_STACK_RE.match(line)
      if not m:
        raise Error('Unexpected fields reported in perf script '
                    'stack trace. (%s)' % line)
      ip, symbol, dso = m.groups()
      symbol = symbol if symbol.strip() else '[unknown]'
      dso = '([unknown])' if dso == '()' else dso
      stack_lines.append(''.join((line[:line.find(ip)],
                                  ' '.join((ip, symbol, dso)))))
    else:
      # PERF_TO_TRACING requires a stack trace for each event so filter events
      # without stack traces.
      if event_line and stack_lines:
        processed_script_output.append(event_line)
        processed_script_output.extend(stack_lines)
        # End of a stack track.
        processed_script_output.append(line.rstrip())
      event_line = ''
      stack_lines = []
  out = os.linesep.join(processed_script_output)
  script_output = tempfile.NamedTemporaryFile()
  script_output.write(out)
  script_output.flush()

  # Generate a common json format from the outputted sample data.
  out, _, _ = execute_command(perf_to_tracing, [script_output.name],
                              'Unable to convert perf script output to JSON.',
                              verbose=verbose)
  json_output = tempfile.NamedTemporaryFile()
  json_output.write(out)
  json_output.flush()

  # Generate the html file from the json data.
  out, _, _ = execute_command(perf_vis, [json_output.name],
                              'Unable to generate HTML report from JSON '
                              'data', verbose=verbose)
  m = PERF_VIS_OUTPUT_FILE_RE.search(out)
  generated_filename = m.groups()[0]
  if os.path.exists(output_filename):
    os.remove(output_filename)
  os.rename(generated_filename, output_filename)
  execute_command(browser, [output_filename],
                  'Cannot start browser %s' % browser, verbose=verbose)


def get_browser(verbose):
  """Try to get the browser executable / command to open a URL.

  Args:
    verbose: Whether verbose output is enabled.

  Returns:
    (executable, name) tuple where executable is the executable or command
    required to open a URL and name is the name of the browser.
  """
  browser = None
  browser_name = None
  if platform.system() == 'Linux':
    try:
      browser_name, _, _ = execute_command(
          'xdg-settings', ['get', 'default-web-browser'],
          'Unable to retrieve browser name.', verbose=verbose)
      browser_name = browser_name.strip()
      browser = 'xdg-open'
    except CommandFailedError as e:
      print >> sys.stderr, str(e)
  elif platform.system() == 'Darwin':
    browser = 'open'
    browser_name = '<unknown browser>'
  elif platform.system() == 'Windows':
    browser = 'start'
    browser_name = '<unknown browser>'
  return (browser, browser_name)


def display_help(parser, sub_command_parsers, perf_args, adb_device, verbose):
  """Display help for command referenced by perf_args.

  Args:
    parser: argparse.ArgumentParser instance which is used to print the
      global help string.
    sub_command_parsers: Dictionary of argparse.ArgumentParser instances
      indexed by subcommand, for each subcommand this script provides.
    perf_args: PerfArgs instance which is used to determine which perf command
      help to display.
    adb_device: Device used to determine which perf binary should be used.
    verbose: Whether verbose output is enabled.
  """
  parser.print_help()
  command = perf_args.command
  if command:
    command_name = command.name
    command_header = '%s help%s' % (
        'perf' if command.real_command else os.path.basename(sys.argv[0]),
        ' %s' % command_name if command_name != 'help' else '')
    print os.linesep.join(
        ('', command_header + ('-' * (80 - len(command_header)))))
    sub_command_parser = sub_command_parsers.get(command_name)
    if sub_command_parser:
      sub_command_parser.print_help()
    elif perf_args.command.real_command:
      out, err, _ = execute_command(
          find_host_binary(PERFHOST_BINARY, adb_device), perf_args.args,
          'Unable to get %s help' % PERFHOST_BINARY, verbose=verbose,
          ignore_error=True)
      print out + err


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
  parser.add_argument('--verbose', help='Display verbose output.',
                      action='store_true', default=False)
  parser.add_argument('--no-record-call-graph',
                      help=('By default the call graph will be captured on'
                            'record so the trace can be visualized with '
                            'stacks.  Use this option to disable call graph '
                            'recording (effectively removing -g from the '
                            '"perf record" command line.'))
  parser.add_argument('--no-record-timestamp',
                      help=('By default the timestamp will be captured on'
                            'for each recorded event so the trace can be '
                            'visualized with timing information.  Use this '
                            'option to disable timestamp recording '
                            '(effectively removing -T from the "perf record"'
                            ' command line.'))

  visualizer_parser = argparse.ArgumentParser(
      description=('visualize converts a perf trace to a HTML visualization '
                   'and opens the page in a web browser.'), add_help=False)
  visualizer_parser.add_argument(
      '--browser', help='Web browser to use for visualization.')
  visualizer_parser.add_argument(
      '-i', '--input-file',
      help=('perf.data file to visualize.  If this isn\'t specified, '
            'the command will attempt to read perf.data from the current '
            'directory.'))
  visualizer_parser.add_argument(
      '--symfs', help=('Look for symbols relative to this directory.  '
                       'If this is not specified, the input file directory '
                       'is searched for symbols.'))
  visualizer_parser.add_argument(
      '-o', '--output-file', help=('Name of the HTML report file to '
                                   'generate.'),
      required=True)

  args, perf_arg_list = parser.parse_known_args()
  verbose = args.verbose

  # Parse perf arguments.
  try:
    perf_args = PerfArgs(perf_arg_list, verbose)
  except PerfArgs.Error as e:
    print >> sys.stderr, str(e)
    return 1

  # Preprocess perf arguments.
  perf_args.insert_symfs_dir(os.path.dirname(
      perf_args.get_input_filename()))

  if perf_args.command and perf_args.command.name == 'visualize':
    visualizer_args, _ = visualizer_parser.parse_known_args(
        args=perf_args.args[1:])
  else:
    visualizer_args = []

  try:
    # Construct a class to communicate with the ADB device.
    adb_device = Adb(args.adb_device, execute_command, verbose=verbose)
  except Adb.Error, error:
    # If the perf command needs to be run on the device, report the error and
    # exit.
    if not perf_args.get_help_enabled() and perf_args.requires_remote():
      print >> sys.stderr, os.linesep.join([
          str(error), 'Try specifying a device using --adb-device <serial>.'])
      return 1
    else:
      adb_device = None

  # If requested, display the help text and exit.
  if perf_args.get_help_enabled():
    display_help(parser, {'visualize': visualizer_parser}, perf_args,
                 adb_device, verbose)
    return 1

  # Run visualization command.
  if perf_args.command.name == 'visualize':
    browser, browser_name = (
        (visualizer_args.browser, visualizer_args.browser)
        if visualizer_args.browser else get_browser(verbose))
    if not browser:
      print >> sys.stderr, ('Cannot find default browser. '
                            'Please specify using --browser.')
      return 1
    if not re.match(r'.*chrom.*', browser_name, re.IGNORECASE):
      print >> sys.stderr, CHROME_NOT_FOUND % browser_name
    try:
      return run_perf_visualizer(browser, perf_args, adb_device,
                                 visualizer_args.output_file, verbose)
    except CommandFailedError as error:
      print >> sys.stderr, str(error)
      return error.returncode
    except Error as error:
      print >> sys.stderr, str(error)
      return 1

  try:
    # Run perf remotely
    if perf_args.requires_remote():
      android_version = adb_device.get_version()
      if is_version_less_than(android_version, '4.1'):
        print >> sys.stderr, PERF_BINARIES_NOT_SUPPORTED % {
            'ver': android_version}
      (model, name) = adb_device.get_model_and_name()
      if name in BROKEN_DEVICES:
        print >> sys.stderr, PERFORMANCE_COUNTERS_BROKEN % model
      elif name not in SUPPORTED_DEVICES:
        print >> sys.stderr, NOT_SUPPORTED_DEVICE % model
      user, _, _ = adb_device.shell_command(r'echo ${USER}',
                                            'Unable to get Android user name')
      if perf_args.requires_root() and user != 'root':
        print >> sys.stderr, DEVICE_NOT_ROOTED % perf_args.command.name

      return run_perf_remotely(adb_device, args.apk_directory, perf_args,
                               not args.no_record_call_graph,
                               not args.no_record_timestamp)
    # Run perf locally
    else:
      execute_command(
          find_host_binary(PERFHOST_BINARY, adb_device), perf_args.args,
          'Failed to execute %s %s' % (PERFHOST_BINARY,
                                       ' '.join(perf_args.args)),
          verbose=verbose, display_output=True)

  except CommandFailedError as error:
    print >> sys.stderr, str(error)
    return error.returncode
  return 0

if __name__ == '__main__':
  sys.exit(main())
