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

import logging
from optparse import OptionParser
import os
import sys

try:
  sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir))
except NameError:
  sys.path.append(os.path.join(os.path.dirname(
      locals().get("__file__", "bin")), os.pardir))

import setuputil.android
import setuputil.linux
import setuputil.mac
import setuputil.windows

"""Installs all necessary requirements for building.

   Determines user's OS and downloads and installs prerequisites accoringly.
"""


def say_hello():
  """Prints welcome message to the user."""
  print("\nWelcome to the fplutil setup script!\n"
        "This script will install any necessary prerequisites so you can build "
        "Android and Desktop applications using FPL's suite of tools.\n"
        "This script will, by default, install some dependencies in your "
        "home directory.\nIf you would rather install depedencies in a "
        "different location, quit now and check additional path setting "
        "options with the flag --help.\n"
        "For more information, including instructions for manual setup, "
        "visit:\nhttp://google.github.io/fplutil/fplutil_prerequisites.html")
  answer = raw_input("Press ENTER to continue, or q to quit: ")
  if answer.lower().startswith("q"):
    return False
  else:
    return True


def create_option_parser():
  """Creates option parser and adds command line arguments to parser."""
  parser = OptionParser()
  parser.add_option("--android_sdk", action="store", type="string",
                    dest="sdk_location", default=setuputil.common.BASE_DIR,
                    help="ANDROID: Specify path to Android SDK directory. Can "
                         "either be a reference to existing SDK tools, or an "
                         "indication of where to install them. Path can either "
                         "be the full file path, or relative to the home "
                         "directory.")
  parser.add_option("--android_ndk", action="store", type="string",
                    dest="ndk_location", default=setuputil.common.BASE_DIR,
                    help="ANDROID: Specify path to Android NDK directory. Can "
                         "either be a reference to existing NDK tools, or an "
                         "indication of where to install them. Path can either "
                         "be the full file path, or relative to the home "
                         "directory.")
  parser.add_option("--ant", action="store", type="string",
                    dest="ant_location", default=setuputil.common.BASE_DIR,
                    help="OSX: Specify path to Apache Ant directory. Can "
                         "either be a reference to existing ant tools, or an "
                         "indication of where to install them. Path can either "
                         "be the full file path, or relative to the home "
                         "directory.")
  parser.add_option("--cwebp", action="store", type="string",
                    dest="cwebp_location", default=setuputil.common.BASE_DIR,
                    help="OSX, WINDOWS: Specify path to cwebp directory. Can "
                         "either be a reference to existing cwebp tools, or an "
                         "indication of where to install them. Path can either "
                         "be the full file path, or relative to the home "
                         "directory.")
  parser.add_option("--cmake", action="store", type="string",
                    dest="cmake_location", default=setuputil.common.BASE_DIR,
                    help="OSX, WINDOWS: Specify path to CMake directory. Can "
                         "either be a reference to existing CMake tools, or an "
                         "indication of where to install them. Path can either "
                         "be the full file path, or relative to the home "
                         "directory.")
  parser.add_option("--java", action="store", type="string",
                    dest="java_location", default=setuputil.common.BASE_DIR,
                    help="WINDOWS: Specify where Java has been installed. Used "
                         "if Java has been installed but cannot be located. "
                         "Path can either be the full file path, or relative "
                         "to the home directory.")
  parser.add_option("--python", action="store", type="string",
                    dest="python_location", default=setuputil.common.BASE_DIR,
                    help="WINDOWS: Specify where Python has been installed. "
                         "Used if Python has been installed but cannot be "
                         "located. Path can either be the full file path, or "
                         "relative to the home directory.")
  parser.add_option("--no_android", action="store_true",
                    dest="no_android", default=False,
                    help="ANDROID: Don't install Android. If this flag is set, "
                         "android_sdk and android_ndk flags will be ignored.")
  parser.add_option("--no_macports", action="store_true",
                    dest="no_macports", default=False,
                    help="OSX: Don't attempt to install Mac Ports. If Mac "
                         "Ports is already installed, then installation will "
                         "be skipped irrespectively. Intended to people that "
                         "wish to install ImageMagick using Homebrew.")
  parser.add_option("--no_visual_studio", action="store_true",
                    dest="no_visual_studio", default=False,
                    help="WINDOWS: Don't attempt to install Visual Studio. "
                         "Indended for users that wish to build without Visual "
                         "Studio, or have a version of Visual Studio that is "
                         "not currently recognised as supported.")
  parser.add_option("--fix_directx", action="store_true",
                    dest="fix_directx", default=False,
                    help="WINDOWS: Attempt to solve problems DirectX has with "
                         "Visual Studio installation.")
  parser.add_option("--fix_path", action="store_true",
                    dest="fix_path", default=False,
                    help="WINDOWS: Check Windows' PATH variable to see if it "
                         "contains the necessary file paths. Attempt to fix "
                         "any missing paths.")
  options, _ = parser.parse_args()
  return options


def create_logger():
  """Create a logger for setup."""
  logging.basicConfig()
  logging.getLogger().setLevel(logging.INFO)


def linux_setup():
  """Creates an instance of LinuxSetup and runs all setup.

  Raises:
    VersionUnsupportedError: If Linux version is not Debian based.
    PermissiondDeniedError: If sudo permissions are not granted.
    BadDirectoryError: If a path given in the cwebp, cmake or ant flag does not
        exist.
  """
  try:
    setup = setuputil.linux.LinuxSetup()
    setup.setup_all()
    return
  except setuputil.common.VersionUnsupportedError as e:
    logging.error("This setup script only works for Debian-based Linux.")
    raise e
  except setuputil.common.PermissionDeniedError as e:
    logging.error("Installation of " + e.program + " failed. " + e.instructions)
    raise e
  except setuputil.common.BadDirectoryError as e:
    logging.error("Directory given for flag " + e.flag + " does not exist.\n"
                  "Please check " + e.directory + " and try again.")
    raise e


def windows_init(options):
  """Create an instance of WindowsSetup and catch version errors.

  Args:
    options: All command line flags.
  Returns:
    WindowsSetup: The object needed for setting up Windows if successful, or
      nothing if setup fails.
  Raises:
    VersionUnsupportedError: If the system version is neither 32bit or 64bit
    VersionTooLowError: If the OS is older than Windows 7
    BadDirectoryError: If the given cwebp or cmake path does not exist.
  """
  try:
    setup = setuputil.windows.WindowsSetup(options)
    return setup
  except setuputil.common.VersionUnsupportedError as e:
    logging.error("Your version of Windows is neither 32 nor 64 bit, and is "
                  "not supported by this script.")
    raise e
  except setuputil.common.VersionUnsupportedError as e:
    logging.error("Your version of Windows (" + e.version + ") is lower than "
                  "the lowest supported version of this script (Windows 7).")
    raise e
  except setuputil.common.BadDirectoryError as e:
    logging.error("Directory given for flag " + e.flag + " does not exist.\n"
                  "Please check " + e.directory + " and try again.")
    raise e
  return None


def windows_setup(setup):
  try:
    setup.setup_all()
  except setuputil.common.PermissionDeniedError as e:
    logging.error("Could not obtain permissions to run " + e.program + ".\n"
                  + e.instructions)
    raise e
  except setuputil.common.FileDownloadError as e:
    logging.error("Please visit " + e.link + "for download link and extraction "
                  "instructions.\n" + e.instructions)
    raise e
  except setuputil.common.InstallFailedError as e:
    logging.error(e.program + " failed to install. Please visit " + e.link +
                  " for download link and extraction instructions.\n" +
                  e.instructions)
    raise e
  except setuputil.common.WebbrowserFailedError as e:
    logging.error("Unable to open link for " + e.pagename + ". Please open " +
                  e.link + " manually to complete installation, and rerun this "
                  "script again afterwards.")
    raise e
  except setuputil.common.InstallInterruptError as e:
    logging.error("Cancelled wait for " + e.program + ". " + e.instructions)
    raise e


def mac_init(options, skip_version_check=False):
  """Create an instance of MacSetup and catch version errors.

      FileDownloadError: If the Visual Studio installer fails to download, or
          is downloaded incorrectly.
  Args:
    options: All command line flags
    skip_version_check: A boolean determining whether or not to check the minor
        version of Mac OS X
  Returns:
    MacSetup: The object needed for setting up Mac if successful, or nothing if
        setup fails
  Raises:
    VersionUnsupportedError: If Mac OS is a version other than OS X.
    VersionTooHighError: If Mac OSX version is higher than 10.11 (El Capitan)
    VersionTooLowError: If Mac OSX version is lower than 10.4 (Tiger)
    BadDirectoryError: If a path given in the cwebp, cmake or ant flag does not
        exist.
  """
  try:
    setup = setuputil.mac.MacSetup(options, skip_version_check)
    return setup
  except setuputil.common.VersionUnsupportedError as e:
    logging.error("Your version of Mac OS (" + e.version + ") is not supported "
                  "by this script.")
    raise e
  except setuputil.common.VersionTooHighError as e:
    logging.error("Your version of OS X (" + e.version + ") is higher than "
                  "this setup script supports.\nPlease quit now and update the "
                  "script, or attempt installation for the highest supported "
                  "OS X version (10.11 El Capitan).")
    if raw_input("Continue? (y/n): ").lower().startswith("y"):
      return mac_init(options, skip_version_check=True)
    else:
      raise e
  except setuputil.mac.VersionTooLowError as e:
    logging.error("Your version of OS X (" + e.version + ") is not reliably "
                  "supported.")
    if raw_input("Attempt installation for the lowest supported OS X version "
                 "(10.4 Tiger)? (y/n): ").lower().startswith("y"):
      return mac_init(options, skip_version_check=True)
    else:
      raise e
  except setuputil.common.BadDirectoryError as e:
    logging.error("Directory given for flag " + e.flag + " does not exist.\n"
                  "Please check " + e.directory + " and try again.")
    raise e
  return None


def mac_setup(setup):
  """Perform all necessary setup for Mac OSX and catch installation errors.

  Args:
    setup: The MacSetup object needed for installing all prereqs
  Raises:
    InstallInterruptError: If the user cancels the wait for installation of
        Xcode, Xcode Command Line Tools, or Java
    InstallFailedError: If, for any reason, ImageMagick cannot be installed.
    FileDownloadError: If the cmake tar, cwebp tar, MacPorts package or Ant tar
        fails to download, or is incorrectly downloaded.
    ExtractionError: If the cmake tar, cwebp tar, or ant tar cannot be properly
        extracted.
    PermissionsDeniedError: If sudo permissions are not granted for accepting
        the Xcode terms and conditions, or for MacPorts installation.
    CommandFailedError: Xcode is unable to install using its command line
        installer
    UnknownFileTypeError: If the type of the downloaded package does not match
        any of the supported types.
    BadDirectoryError: If a path given in the cwebp, cmake or ant flag does not
        exist.
  """
  try:
    setup.setup_all()
    return
  except setuputil.common.InstallInterruptError as e:
    logging.error("Cancelled wait for " + e.program + ".")
    raise e
  except setuputil.common.InstallFailedError as e:
    logging.error(e.program + " failed to install. Please visit " + e.link +
                  " for download link and extraction instructions.\n" +
                  e.instructions)
    raise e
  except setuputil.common.FileDownloadError as e:
    logging.error("Please visit " + e.link + "for download link and extraction "
                  "instructions.\n" + e.instructions)
    raise e
  except setuputil.common.ExtractionError as e:
    logging.error("Unable to extract " + e.filepath + ".\nPlease extract "
                  "manually.")
    raise e
  except setuputil.common.PermissionDeniedError as e:
    logging.error(e.program + " failed to obtain permissions. " +
                  e.instructions)
    raise e
  except setuputil.common.CommandFailedError as e:
    logging.error("Unable to perform bash command:\n\t" + e.command + "\n"
                  "Please check error message and go to " + e.link + " for "
                  "help.")
    raise e
  except setuputil.common.UnknownFileTypeError as e:
    logging.error("Unknown file type \"" + e.filetype + "\" downloaded.\n" +
                  e.instructions)
    raise e
  except setuputil.common.BadDirectoryError as e:
    logging.error("Directory given for flag " + e.flag + " does not exist.\n"
                  "Please check " + e.directory + " and try again.")
    raise e


def android_init(system, options):
  """Create an instance of AndroidSetup and catch version errors.

  Args:
    system: Whether the OS is Linux, Mac or Windows
    options: All command line flags
  Returns:
    AndroidSetup: The object needed for setting up Android if successful, or
        nothing if setup fails
  Raises:
    SystemUnsupportedError: If the system not recognised as Linux or Mac OS X.
    BadDirectoryError: If the specified SDK or NDK directory does not exist.
  """
  try:
    setup = setuputil.android.AndroidSetup(system, options)
    return setup
  except setuputil.common.SystemUnsupportedError as e:
    logging.error("Android setup unsupported for " + e.system + ".")
    raise e
  except setuputil.common.BadDirectoryError as e:
    logging.error("Directory given for flag " + e.flag + " does not exist.\n"
                  "Please check " + e.directory + " and try again.")
    raise e
  return None


def android_setup(setup):
  """Perform all necessary setup for Android and catch installation errors.

  Args:
    setup: The AndroidSetup object needed for installing all prereqs
  Raises:
    FileDownloadError: SDK tar or zip, or NDK bin fails to download
    UnknownFileTypeError: If the type of the downloaded package does not match
        any of the supported types.
    CommandFailedError: If tools/android was unable to run correctly for any
        reason.
  """
  try:
    setup.setup_all()
  except setuputil.common.FileDownloadError as e:
    logging.error("Please visit " + e.link + "for download link and extraction "
                  "instructions.\n" + e.instructions)
    raise e
  except setuputil.common.UnknownFileTypeError as e:
    logging.error("Unknown file type \"" + e.filetype + "\" downloaded.\n" +
                  e.instructions)
    raise e
  except setuputil.common.CommandFailedError as e:
    logging.error("Unable to perform bash command:\n\t" + e.command + "\n"
                  "Please check error message and go to " + e.link + " for "
                  "help.")
    raise e


def main():
  if not say_hello():
    return 0
  create_logger()
  options = create_option_parser()
  system = sys.platform
  path_update = False
  path = ""
  if system.startswith("linux"):
    # linux or linux2
    linux_setup()
    system = setuputil.common.LINUX
    # Linux setup doesn't change bashrc
  elif system == "win32" or system == "cygwin":
    # Windows or Cygwin
    w = windows_init(options)
    windows_setup(w)
    system = setuputil.common.WINDOWS
    path_update = w.has_bash_changed()
    path = w.get_windows_path_update()
  elif sys.platform == "darwin":
    # Mac OS X
    m = mac_init(options)
    mac_setup(m)
    system = setuputil.common.MAC
    path_update = m.has_bash_changed()
  else:
    # Unsupported OS
    logging.error(system + " not supported.")
    return 1

  if not options.no_android:
    a = android_init(system, options)
    android_setup(a)
    path_update = path_update or a.has_bash_changed()
    if system == setuputil.common.WINDOWS:
      path = a.get_windows_path_update() + os.pathsep + path

  if path_update:
    if system == setuputil.common.LINUX:
      print("\n~/.bashrc has been changed. Please refresh your bashrc by "
            "running\n\tsource ~/.bashrc")
    elif system == setuputil.common.MAC:
      print("\n~/.bash_profile has been changed. Please refresh your bash "
            "profile by running\n\tsource ~/.bash_profile")
    else:  # system == setuputil.common.Windows:
      setuputil.windows.update_windows_path(path)
      print("\nWindows PATH has been changed. Please restart the command "
            "prompt before continuing.")
  return 0

if __name__ == "__main__":
  sys.exit(main())
