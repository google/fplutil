#!/usr/bin/python

# Copyright 2016 Google Inc. All Rights Reserved.
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


import os

BASE_DIR = os.path.expanduser("~")

LINUX = "LINUX"
LINUX_32 = LINUX + "32"
LINUX_64 = LINUX + "64"
MAC = "MAC"
WINDOWS = "WINDOWS"
WINDOWS_32 = WINDOWS + "32"
WINDOWS_64 = WINDOWS + "64"


class Setup(object):
  """Base class for installing prerequisites for Linux, Mac OS X and Windows.

  Attributes:
    bash_profile_changed: A boolean indicating whether or not the bash profile
        has been edited by the script, and the user should call source.
    cwebp_path: A string of the path to the location of the cwebp directory.
    cmake_path: A string of the path to the location of the cmake directory.

  Raises:
    BadDirectoryError: If a path given in the cwebp, cmake or ant flag does not
        exist.
  """

  def __init__(self, options):
    self.bash_profile_changed = False
    self.bash_profile = os.path.join(BASE_DIR, ".bash_profile") # Unused in
                                                                # Windows
    self.cwebp_path = os.path.join(BASE_DIR, options.cwebp_location)
    if not os.path.isdir(self.cwebp_path):
      raise BadDirectoryError("--cwebp", self.cwebp_path)
    self.cmake_path = os.path.join(BASE_DIR, options.cmake_location)
    if not os.path.isdir(self.cmake_path):
      raise BadDirectoryError("--cmake", self.cmake_path)
    self.ant_path = os.path.join(BASE_DIR, options.ant_location)
    if not os.path.isdir(self.ant_path):
      raise BadDirectoryError("--ant", self.ant_path)

  def has_bash_changed(self):
    """Returns wheter or not the bash profile has been changed."""
    return self.bash_profile_changed


class SystemUnsupportedError(Exception):
  """Raised when an OS is unrecognised or unsupported."""

  def __init__(self, system):
    Exception.__init__(self)
    self.system = system


class VersionUnsupportedError(Exception):
  """Raised when the version of an OS is unrecognised or unsupported."""

  def __init__(self, version):
    Exception.__init__(self)
    self.version = version


class VersionTooHighError(Exception):
  """Raised when the OS version is greater than the highest supported."""

  def __init__(self, version):
    Exception.__init__(self)
    self.version = version


class VersionTooLowError(Exception):
  """Raised when the OS version is less than the lowest supported."""

  def __init__(self, version):
    Exception.__init__(self)
    self.version = version


class BadDirectoryError(Exception):
  """Raised when a directory given through a command line flag doesn't exist."""

  def __init__(self, flag, directory):
    Exception.__init__(self)
    self.flag = flag
    self.directory = directory


class InstallInterruptError(Exception):
  """Raised when installation of a program was interrupted by the user."""

  def __init__(self, program, instructions=""):
    Exception.__init__(self)
    self.program = program
    self.instructions = instructions


class InstallFailedError(Exception):
  """Raised when installation fails for reasons other than user interrupt."""

  def __init__(self, program, link="", instructions=""):
    Exception.__init__(self)
    self.program = program
    self.link = link
    self.instructions = instructions


class FileDownloadError(Exception):
  """Raised when a file was unable to download."""

  def __init__(self, link, instructions=""):
    Exception.__init__(self)
    self.link = link
    self.instructions = instructions


class UnknownFileTypeError(Exception):
  """Raised when the extension of a file is unrecognised."""

  def __init__(self, filetype, instructions):
    Exception.__init__(self)
    self.filetype = filetype
    self.instructions = instructions


class ExtractionError(Exception):
  """Raised when a compressed file was unable to be extracted."""

  def __init__(self, filepath):
    Exception.__init__(self)
    self.filepath = filepath


class CommandFailedError(Exception):
  """Raised when a subprocess fails for unforseeable reasons."""

  def __init__(self, command, link):
    Exception.__init__(self)
    self.command = command
    self.link = link


class PermissionDeniedError(Exception):
  """Raised when the script was not able to gain the correct permissions."""

  def __init__(self, program, instructions):
    Exception.__init__(self)
    self.program = program
    self.instructions = instructions


class WebbrowserFailedError(Exception):
  """Raised when a url was unable to be opened in the webbrowser."""

  def __init__(self, pagename, link):
    Exception.__init__(self)
    self.pagename = pagename
    self.link = link
