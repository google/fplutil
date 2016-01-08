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

import logging
import os
import subprocess

import common


"""Contains all necessary methods for setting up Linux."""

# Programs required for Linux installation.
# Program name: package_name
LINUX_PROGRAMS = {
    "autoconf": "autoconf",
    "automake": "automake",
    "cmake": "cmake",
    "ImageMagick": "imagemagick",
    "OpenGL": "libglapi-mesa",
    "GLU": "libglu1-mesa-dev",
    "libtool": "libtool",
    "OSS Proxy Daemon": "osspd",
    "Python": "python",
    "Ragel": "ragel",
    "crwebp": "webp",
    "Java 1.7": "openjdk-7-jdk",
    "ant": "ant"}


class LinuxSetup(object):
  """Contains all necessary methods for setting up Linux."""

  def linux_requirements(self):
    """Installs all necessary linux programs.

    If the program has already been intalled, it will be skipped.

    Raises:
      VersionUnsupportedError: If Linux version is not Debian based.
      PermissiondDeniedError: If sudo permissions are not granted.
      BadDirectoryError: If a path given in the cwebp, cmake or ant flag does
          not exist.
    """
    if not os.path.isfile("/etc/debian_version"):
      raise common.VersionUnsupportedError("Non Debian based")

    logging.info("Installing:\n    + " + "\n    + ".join(LINUX_PROGRAMS.keys())
                 + "\nSudo may prompt you for your password")
    try:
      subprocess.call("sudo apt-get update", shell=True)
      subprocess.call("sudo apt-get install " +
                      " ".join(LINUX_PROGRAMS.values()), shell=True)
    except subprocess.CalledProcessError:
      raise common.PermissionDeniedError("Linux programs", "Please enter your "
                                         "password to install the necessary "
                                         "Linux programs\n")

  def setup_all(self):
    """Perform all necessary setup."""
    self.linux_requirements()
    logging.info("Linux setup complete")
