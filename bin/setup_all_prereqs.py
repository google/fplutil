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
import sys

import platforms.linux
import platforms.mac

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
    sys.exit()


def create_logger():
  """Create a logger for setup."""
  logging.basicConfig()
  logging.getLogger().setLevel(logging.INFO)


def mac_init():
  """Create an instance of MacSetup and catch version errors."""
  try:
    setup = platforms.mac.MacSetup()
    return setup
  except platforms.mac.VersionUnsupportedError as e:
    logging.warn("Your version of Mac OS (" + e.version + ") is not supported "
                 "by this script.")
  except platforms.mac.VersionTooHighError as e:
    logging.warn("Your version of OS X (" + e.version + ") is higher than this "
                 "setup script supports.\nPlease quit now and update the "
                 "script, or attempt installation for the highest supported "
                 "OS X version (10.11 El Capitan).")
    if raw_input("Continue? (y/n): ").lower().startswith("y"):
      setup = platforms.mac.MacSetup(skip_version_check=True)
      return setup
  except platforms.mac.VersionTooLowError as e:
    logging.warn("Your version of OS X (" + e.version + ") is not reliably "
                 "supported.")
    if raw_input("Attempt installation for the lowest supported OS X version "
                 "(10.4 Tiger)? (y/n): ").lower().startswith("y"):
      setup = platforms.mac.MacSetup(skip_version_check=True)
      return setup
  except platforms.mac.BadDirectoryError as e:
    logging.warn(e.directory + " does not exist.")
  logging.warn("Setup exited before completion.")
  sys.exit(1)


def mac_setup(setup):
  """Perform all necessary setup for Mac OSX and catch installation errors."""
  try:
    setup.setup_all()
    return
  except platforms.mac.InstallInterruptError as e:
    logging.warn("Cancelled wait for " + e.program + ".")
  except platforms.mac.InstallFailedError as e:
    logging.warn(e.program + " failed to install. Please visit " + e.link +
                 " for download link and extraction instructions.\n" +
                 e.instructions)
  except platforms.mac.FileDownloadError as e:
    logging.warn("Please visit " + e.link + "for download link and extraction "
                 "instructions.\n" + e.instructions)
  except platforms.mac.ExtractionError as e:
    logging.warn("Unable to extract " + e.filepath + ".\nPlease extract "
                 "manually.")
  print "Setup exited before completion."
  sys.exit(1)


def main():
  say_hello()
  create_logger()
  if sys.platform.startswith("linux"):
    # linux or linux2
    setup = platforms.linux.LinuxSetup()
    setup.setup_all()
  elif sys.platform == "win32" or sys.platform == "cygwin":
    # Windows or Cygwin
    logging.warn("Windows not supported yet")
  elif sys.platform == "darwin":
    # Mac OS X
    m = mac_init()
    mac_setup(m)
  else:
    # Unsupported OS
    logging.warn(sys.platform + " not supported.")


if __name__ == "__main__":
  sys.exit(main())
