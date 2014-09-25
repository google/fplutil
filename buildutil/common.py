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

"""Common BuildEnvironment sub-module.

This is the base implementation for target-specific build environments. Common
utility functions are collected here as well.

Optional environment variables:

GIT_PATH = Path to git binary.
MAKE_PATH = Path to make binary. Required if make is not in $PATH,
or not passed on command line.
MAKE_FLAGS = String to override the default make flags with.
"""

import datetime
import distutils.spawn
import multiprocessing
import os
import shlex
import shutil
import subprocess
import zipfile

_PROJECT_DIR = 'project_dir'
_MAKE_PATH_ENV_VAR = 'MAKE_PATH'
_GIT_PATH_ENV_VAR = 'GIT_PATH'
_MAKE_FLAGS_ENV_VAR = 'MAKE_FLAGS'
_CPU_COUNT = 'cpu_count'
_MAKE_PATH = 'make_path'
_GIT_PATH = 'git_path'
_MAKE_FLAGS = 'make_flags'
_GIT_CLEAN = 'git_clean'
_VERBOSE = 'verbose'
_OUTPUT_DIR = 'output_dir'
_CLEAN = 'clean'


class Error(Exception):

  """Base class for exceptions in this module.

  Attributes:
    error_message: An error message composited by specific error subclasses.
    error_code: An error scalar unique to each error subclass, suitable for
      return from main()
  """

  CODE = -1

  def __init__(self):
    """Initializes base exception values."""
    super(Error, self).__init__()
    self._error_message = 'Unknown Error'
    self._error_code = Error.CODE

  @property
  def error_message(self):
    """Return a string representation of the error."""
    return self._error_message

  @property
  def error_code(self):
    """Return a scalar representation of the error."""
    return self._error_code

  def __str__(self):
    """Return a string representation of the error.

    Returns:
      An error string composited from internal exception attributes.
    """
    return self.error_message


class ToolPathError(Error):

  """Exception class for missing build tools or other bad paths to them."""

  CODE = 1

  def __init__(self, binary_type, path):
    """Initializes exception with the binary type and configured path.

    Args:
      binary_type: The binary we were trying to find.
      path: The binary path as set in the build environment.
    """
    super(ToolPathError, self).__init__()
    self._error_message = '%s not found at path %s' % (binary_type, path)
    self._error_code = ToolPathError.CODE


class SubCommandError(Error):

  """Exception class related to running commands."""

  CODE = 2

  def __init__(self, arguments, return_code, stderr=None):
    """Initializes exception with subprocess information and error value.

    Args:
      arguments: The argument list passed to subprocess.Popen().
      return_code: The error code returned from the subcommand.
      stderr: Optional string of stderr output from the process, if captured.
    """
    super(SubCommandError, self).__init__()
    if not stderr:
      stderr = '*not captured*'
    self._error_message = 'Error %d running %s as: %s, stderr: {%s}' % (
        return_code, arguments[0],
        str(arguments),
        stderr)

    self._error_code = SubCommandError.CODE


class ConfigurationError(Error):

  """Exception class related to missing or broken build configuration files."""

  CODE = 3

  def __init__(self, path, error):
    """Initializes exception with path to broken file and error message.

    Args:
      path: Path to file that generated the error.
      error: The specific error to report.
    """
    super(ConfigurationError, self).__init__()
    self._error_message = 'Error with build configuration file "%s": %s' % (
        path, error)
    self._error_code = ConfigurationError.CODE


class AdbError(Error):

  """Exception class related to missing or broken adb connections."""

  CODE = 4

  def __init__(self, error):
    """Initializes exception with error message.

    Args:
      error: The specific error to report.
    """
    super(AdbError, self).__init__()
    self._error_message = 'Error with adb connection: %s' % (error)
    self._error_code = ConfigurationError.CODE


class BuildEnvironment(object):

  """Class representing the build environment we will be building in.

  This class resolves and exposes various build parameters as properties,
  which can be customized by users before building. It also provides methods
  to accomplish common build tasks such as executing build tools and archiving
  the resulting build artifacts. It is subclassed to provide platform-specific
  build tasks.

  Attributes:
    project_directory: The top-level project directory to build.
    output_directory: The top level directory to copy the build archive to.
    enable_git_clean: Boolean value to enable cleaning for git-based projects.
    make_path: Path to the make binary, for make-based projects.
    make_flags: Flags to pass to make, for make-based projects.
    clean: Boolean value which specifies whether to clean the project.
    git_path: Path to the git binary, for projects based on git.
    cpu_count: Number of CPU cores to use while building.
    verbose: Boolean to enable verbose message output.
    host_os_name: Lowercased name of host operating system.
    host_architecture: Lowercased name of host machine architecture.
  """

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

    self.project_directory = args[_PROJECT_DIR]
    self.output_directory = args[_OUTPUT_DIR]
    if not self.output_directory:
      self.output_directory = args[_PROJECT_DIR]
    self.enable_git_clean = args[_GIT_CLEAN]
    self.make_path = args[_MAKE_PATH]
    self.git_path = args[_GIT_PATH]
    self.make_flags = args[_MAKE_FLAGS]
    self.cpu_count = args[_CPU_COUNT]
    self.verbose = args[_VERBOSE]
    self.clean = args[_CLEAN]

    (sysname, unused_node, unused_release, unused_version,
     machine) = os.uname()
    self.host_os_name = sysname.lower()
    self.host_architecture = machine.lower()

    self._posix = self.host_os_name is not 'windows'

    if self.verbose:
      print 'Build environment set up from: %s' % str(args)

  @staticmethod
  def _find_path_from_binary(name, levels):
    """Search $PATH for name and find parent directory n levels above it.

    Return the directory at 'levels' levels above the named binary if it is
    found in $PATH.

    Example, if 'android' is in joebob's $PATH at

      /home/joebob/android-sdk-linux/tools/android

    then calling this function with ('android', 2) would return

      /home/joebob/android-sdk-linux

    Args:
      name: Binary name to search for in $PATH.
      levels: The number of parent directory levels above it to return.

    Returns:
      Path to binary nth parent directory, or None if not found or invalid.
    """
    path = distutils.spawn.find_executable(name)
    if path and (levels > 0):
      directories = path.split(os.path.sep)

      if levels < len(directories):
        if levels == len(directories) - 1:
          path = os.path.sep
        else:
          directories = directories[0:-levels]
          path = os.path.sep.join(directories)
      else:
        path = None

    return path

  @staticmethod
  def build_defaults():
    """Helper function to set build defaults.

    Returns:
      A dict containing appropriate defaults for a build.
    """
    args = {}
    args[_PROJECT_DIR] = os.getcwd()
    args[_GIT_CLEAN] = False
    args[_MAKE_PATH] = (os.getenv(_MAKE_PATH_ENV_VAR) or
                        distutils.spawn.find_executable('make'))
    args[_GIT_PATH] = (os.getenv(_GIT_PATH_ENV_VAR) or
                       distutils.spawn.find_executable('git'))
    args[_MAKE_FLAGS] = os.getenv(_MAKE_FLAGS_ENV_VAR)
    args[_CPU_COUNT] = str(multiprocessing.cpu_count())
    args[_VERBOSE] = False
    args[_OUTPUT_DIR] = args[_PROJECT_DIR]
    args[_CLEAN] = False

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

    parser.add_argument('-C', '--' + _PROJECT_DIR,
                        help='Set project top level directory',
                        dest=_PROJECT_DIR, default=defaults[_PROJECT_DIR])
    parser.add_argument(
        '-j', '--' + _CPU_COUNT, help='Processor cores to use when building',
        dest=_CPU_COUNT, default=defaults[_CPU_COUNT])
    parser.add_argument('-m', '--' + _MAKE_PATH,
                        help='Path to make binary', dest=_MAKE_PATH,
                        default=defaults[_MAKE_PATH])
    parser.add_argument('-g', '--' + _GIT_PATH,
                        help='Path to git binary', dest=_GIT_PATH,
                        default=defaults[_GIT_PATH])
    parser.add_argument(
        '-f', '--' + _MAKE_FLAGS, help='Flags to use to override makeflags',
        dest=_MAKE_FLAGS, default=defaults[_MAKE_FLAGS])
    parser.add_argument(
        '-w', '--' + _GIT_CLEAN,
        help='Enable git_clean to reset project directory to last git commit',
        dest=_GIT_CLEAN, action='store_true', default=defaults[_GIT_CLEAN])
    parser.add_argument(
        '-v', '--' + _VERBOSE,
        help='Enable verbose output', dest=_VERBOSE, action='store_true',
        default=defaults[_VERBOSE])
    parser.add_argument('-o', '--' + _OUTPUT_DIR,
                        help='Set build artifact output top-level directory',
                        dest=_OUTPUT_DIR, default=None)
    parser.add_argument('-c', '--' + _CLEAN, action='store_true',
                        help='Clean all build artifacts.',
                        default=False)

  @staticmethod
  def _check_binary(name, path):
    """Helper function to verify a binary resides at a path.

    Args:
      name: The binary name we are checking.
      path: The path to check.

    Raises:
      ToolPathError: Binary is not at the specified path.
    """
    if not path or not os.path.exists(path):
      raise ToolPathError(name, path)

  def run_subprocess(self, argv, capture=False, cwd=None, shell=False):
    """Run a subprocess as specified by the given argument list.

    Runs a process via popen().

    Args:
      argv: A list of process arguments starting with the binary name, in the
        form returned by shlex.
      capture: Boolean to control if output is captured or not.
      cwd: Optional path relative to the project directory to run process in
        for commands that do not allow specifying this, such as ant.
      shell: Optional argument to tell subprocess to allow for shell features.
    Returns:
      A tuple of (stdout, stderr), or (None, None) if capture=False.

    Raises:
      SubCommandError: Process return code was nonzero.
    """

    if self.verbose:
      print 'Running subcommand as: %s' % str(argv)

    if cwd:
      cwd = os.path.abspath(os.path.join(self.project_directory, cwd))

    stdout = None
    stderr = None
    if capture:
      process = subprocess.Popen(args=argv, bufsize=-1, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, shell=shell, cwd=cwd)
      (stdout, stderr) = process.communicate()
    else:
      process = subprocess.Popen(argv, shell=shell, cwd=cwd)
      process.wait()

    if process.returncode or self.verbose:
      print 'Subprocess returned %d' % process.returncode

    if process.returncode:
      raise SubCommandError(argv, process.returncode, stderr)

    return (stdout, stderr)

  def run_make(self):
    """Run make based on the specified build environment.

    This will execute make using the configured environment, passing it the
    flags specified in the cmake_flags property.

    Raises:
      SubCommandError: Make invocation failed or returned an error.
      ToolPathError: Make not found in configured build environment or $PATH.
    """

    BuildEnvironment._check_binary('make', self.make_path)

    args = [self.make_path, '-j', self.cpu_count, '-C', self.project_directory]
    if self.clean:
      args += ['clean']
    if self.make_flags:
      args += shlex.split(self.make_flags, posix=self._posix)

    self.run_subprocess(args)

  def make_archive(self, dirlist, archive_path, copyto=None, exclude=None):
    """Archive build artifacts at the specified directory paths.

    Creates a zip archive containing the contents of all the directories
    specified in dirlist. All dirlist paths are relative from the project
    top directory.

    Args:
      dirlist: A list of directories to archive, relative to the value of the
        project_directory property.
      archive_path: A path to the zipfile to create, relative to the value of
        the output_directory property.
      copyto: Optional argument specifying an absolute directory path to copy
        the archive to on success.
      exclude: Optional list of directory names to filter from dir trees in
        dirlist.  Subdirectories with these names will be skipped when writing
        the archive.

    Raises:
      IOError: An error occurred writing or copying the archive.
    """
    arcabs = os.path.join(self.output_directory, archive_path)
    if os.path.exists(arcabs):
      os.remove(arcabs)

    if self.verbose:
      print 'Creating archive at: %s' % arcabs

    now = datetime.datetime.now()
    now_string = now.strftime('%Y_%m_%d_%H%M.%S.%f')
    tmp = arcabs + str(os.getpid()) + now_string

    self._write_archive(tmp, dirlist, exclude)

    os.rename(tmp, arcabs)
    if self.verbose:
      print 'Archive complete at: %s' % arcabs

    if copyto:
      if self.verbose:
        print 'Copying archive to: %s' % copyto
      shutil.copy2(arcabs, copyto)

  def _write_archive(self, path, directory_list, exclude):
    """Write a zip archive of a list of directories.

    Args:
      path: A path to the zipfile to create.
      directory_list: A list of directories to archive.
      exclude: Subtree directory names to exclude from the archive.

    Raises:
      IOError: An error occurred writing the archive.
    """
    # Algorithm is to walk the directory tree for each directory
    # passed in by the user, and add its files to the archive. Since we
    # may be run from any directory, the path calculations all need to be
    # relative to the project base directory absolute path; however, inside the
    # zipfile, we want to name the files relative to the name of the project
    # directory so that the archive is all contained under a root named for
    # the project base dir. In this code, absolute paths are prefaced with
    # 'abs' to make that clear. The final filename in the archive is resolved
    # in the call to os.path.relpath.
    with zipfile.ZipFile(path, 'w') as arczip:
      for d in directory_list:
        absd = os.path.join(self.project_directory, d)
        if self.verbose:
          print 'Archiving directory %s' % d
        for root, dirs, files in os.walk(absd):
          if exclude:
            for ex in exclude:
              if ex in dirs:
                dirs.remove(ex)
          for f in files:
            absf = os.path.join(root, f)
            absr = os.path.relpath(absf,
                                   os.path.dirname(self.project_directory))
            if self.verbose:
              print '--> Archiving "%s" as "%s"' % (absf, absr)
            arczip.write(absf, absr)

  def git_clean(self):
    """Cleans build directory back to last git commit.

    Some build systems like CMake have no way to clean up their build
    cruft they create. This function checks it is being run at the top of a git
    repository; then, if enabled in the environment, resets the git repository
    back to its last git commit.

    This will erase ALL CHANGES in the current directory after the last git
    commit, including any build output or edited files. Use with caution.
    Primarily intended for automated builds, and only does anything if the
    '-w' or '--git_clean' flags are passed to the argument parser (or env is
    otherwise modified to enable this.)

    Raises:
      SubCommandError: An error was returned from running git.
      ToolPathError: Git not found in configured build environment or $PATH.
    """
    if not self.enable_git_clean:
      return

    gitdir = os.path.join(self.project_directory, '.git')
    if not os.path.exists(gitdir):
      if self.verbose:
        print 'Not cleaning, %s is not a git repo base' % gitdir
      return

    BuildEnvironment._check_binary('git', self.git_path)

    # Need to use git clean to take care of build output files.
    self.run_subprocess([self.git_path, '-C', self.project_directory, 'clean',
                         '-d', '-f'])
    # Need to use git reset to take care of things like generated config that
    # may also be checked in.
    self.run_subprocess([self.git_path, '-C', self.project_directory, 'reset',
                         '--hard'])
