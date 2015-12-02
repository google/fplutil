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
from optparse import OptionParser
import os
import re
import subprocess
import sys

import setup_util


"""Contains all necessary methods for setting up the Linux and Android.

All update and install methods will check if a download is necessary first.
All download methods will not.
"""

# The user's home directory, and the default place for storing both the
#   Android SDK and Android NDK.
BASE_DIR = os.path.expanduser("~")

# The default names of the folders the Android SDK and Android NDK will be
#   downloaded/installed to.
ANDROID_SDK_LINUX = "android-sdk-linux"
ANDROID_NDK = "android-ndk-r10e"

# Hashes of the expected files for downloading.
ANDROID_SDK_HASH = "978ee9da3dda10fb786709b7c2e924c0"
ANDROID_NDK_HASH = "c3edd3273029da1cbd2f62c48249e978"
ANDROID_NDK_HASH_64 = "19af543b068bdb7f27787c2bc69aba7f"

# Packages required for Android SDK updates.
# Does not include platform-tools, as this must be
#   checked for and installed first.
# Package title: install_code
ANDROID_SDK_UPDATES = {
    "Android SDK Tools": "tools",
    "Android SDK Build-tools": "build-tools-23.0.2",
    "SDK Platform Android 5.0": "android-21",
    "Android TV ARM EABI v7a System Image, Android API 21":
      "sys-img-armeabi-v7a-android-tv-21",
    # Support Packages
    "Android Support Repository, revision 25": "extra-android-m2repository",
    "Android Support Library, revision 23.1.1": "extra-android-support",
    # Google APIs
    "Google Play services, revision 28": "extra-google-google_play_services",
    "Google Repository, revision 23": "extra-google-m2repository"}

# Programs required for Linux installation.
# Program name : package_name
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

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)

parser = OptionParser()
parser.add_option("-s", "--android_sdk", action="store", type="string",
                  dest="sdk_location", help="Specify path to Android SDK")
parser.add_option("-n", "--android_ndk", action="store", type="string",
                  dest="ndk_location", help="Specify path to Android NDK")
(options, args) = parser.parse_args()

class LinuxSetup(object):
  """Contains all necessary methods for setting up the Linux and Android.

   Attributes:
     bashrc_changed: A boolean indicating whether or not the bashrc has been
         edited by the script, indicating the user should call source ~/.bashrc
     home: A string of the user's home directory, as ~ is not always guaranteed
         to work.
     bashrc: A string of the path of the user's bashrc.
     sdk_path: A string of the location of the Android SDK package.
     ndk_path: A string of the location of the Android NDK package.
  """

  def __init__(self):
    self.bashrc_changed = False
    self.bashrc = os.path.join(BASE_DIR, ".bashrc")
    if options.sdk_location:
      self.sdk_path = os.path.join(BASE_DIR, options.sdk_location)
    else:
      self.sdk_path = os.path.join(BASE_DIR, ANDROID_SDK_LINUX)
    if options.ndk_location:
      self.ndk_path = os.path.join(BASE_DIR, options.ndk_location)
    else:
      self.ndk_path = os.path.join(BASE_DIR, ANDROID_NDK)

  def linux_requirements(self):
    """Installs all necessary linux programs.

    If the program has already been intalled, it will be skipped.
    """
    if not os.path.isfile("/etc/debian_version"):
      logger.critical("This setup script only works for Debian-based Linux.\n")
      sys.exit()

    logger.info("Installing:\n    + " + "\n    + ".join(LINUX_PROGRAMS.keys())
                + "\nSudo may prompt you for your password")
    try:
      output = subprocess.check_output("sudo apt-get install " +
                                       " ".join(LINUX_PROGRAMS.values()),
                                       shell=True)
    except subprocess.CalledProcessError:
      logger.warning("Please enter your password to install the necessary "
                     "linux programs\n")
      sys.exit()
    logger.info(output)

  def android_check_dir(self, dev_kit, location):
    """Checks to see if the dev_kit can be found in the given location.

    Args:
      dev_kit: String of either SDK or NDK to determine which should be
          installed. Everything else will be ignored.
      location: String of the location to be searching in
    Return:
      Boolean: Whether or the the dev kit could be found in the location
    """
    sdk = False
    ndk = False
    if dev_kit == "SDK":
      sdk = True
    elif dev_kit == "NDK":
      ndk = True
    else:
      return False
    if os.path.isdir(location):
      if (sdk and os.path.isfile(os.path.join(location, "tools/android")) or
          ndk and os.path.isfile(os.path.join(location, "ndk-build"))):
        if sdk:
          self.sdk_path = location
        else:  # ndk
          self.ndk_path = location
        print "Android " + dev_kit + " found at " + location
        return True
      else:
        # Try again, but add sdk or ndk folder name to path.
        if (sdk and
            os.path.isfile(
                os.path.join(location,
                             os.path.join(ANDROID_SDK_LINUX,
                                          "tools/android")))):
          self.sdk_path = os.path.join(location, ANDROID_SDK_LINUX)
          print "Android SDK found at " + self.sdk_path
          return True
        elif (ndk and
              os.path.isfile(
                  os.path.join(location,
                               os.path.join(ANDROID_NDK, "ndk-build")))):
          self.ndk_path = os.path.join(location, ANDROID_NDK)
          print "Android NDK found at " + self.ndk_path
          return True
        else:
          print "No Android NDK found at " + location
    else:
      print location + " is not a directory"
    return False


  def android_install(self, dev_kit):
    """Check for specified Android dev kit, download and install.

    Args:
      dev_kit: String of either SDK or NDK to determine which should be
          installed. Anything else will be ignored.
    """
    # TODO(ngibson) Test this more.
    sdk = False
    ndk = False
    if dev_kit == "SDK":
      sdk = True
    elif dev_kit == "NDK":
      ndk = True
    else:
      return

    logger.info("Checking for Android " + dev_kit + "...")
    # Check if the dev kit is already in the home directory.
    if (sdk and self.android_check_dir(dev_kit, self.sdk_path) or
        ndk and self.android_check_dir(dev_kit, self.ndk_path)):
      return

    # Give options for searching or downloading SDK or NDK into in other places.
    print("Android " + dev_kit + " not found in home directory.\n"
          "Please select action to be taken:\n"
          "\t(1) Download into home directory\n"
          "\t(2) Download into another directory\n"
          "\t(3) Search in another directory\n"
          "\t(4) Exit setup")
    while True:
      response = raw_input("").strip()

      if response == "1":
        # Install in home directory (BASE_DIR).
        if sdk:
          self.android_download_sdk(BASE_DIR)
        else:  # ndk
          self.android_download_ndk(BASE_DIR)
        logger.info("Android " + dev_kit + " installed in home directory\n")
        break

      elif response == "2":
        while True:
          # Give another base directory to install in.
          print "Please specify full path of base directory to install:"
          dk_dir = raw_input("")
          if os.path.isdir(dk_dir):
            if sdk:
              self.android_download_sdk(dk_dir)
              self.sdk_path = os.path.join(dk_dir, ANDROID_SDK_LINUX)
            else:  # ndk
              self.android_download_ndk(dk_dir)
              self.ndk_path = os.path.join(dk_dir, ANDROID_NDK)
            logger.info("Android " + dev_kit + " iinstalled in " + dk_dir)
            break
          else:
            print dk_dir + " is not a directory"

      elif response == "3":
        # Search in another directory.
        print "Please specify path to search:"
        dk_dir = os.path.join(BASE_DIR, raw_input("").strip())
        if self.android_check_dir(dev_kit, dk_dir):
          break

      elif response == "4":
        logger.warning("Setup exited before completion\n")
        sys.exit()

      print "Please enter a number from 1-4:"

  def android_download_sdk(self, directory):
    """Download Android SDK and unpack into specified directory.

    Args:
      directory: String indication of location to unpack SDK to
    """
    sdk_location = os.path.join(directory, "sdk.tgz")
    url = "http://dl.google.com/android/android-sdk_r24.4.1-linux.tgz"
    sdk_location = setup_util.download_file(url, sdk_location, "Android SDK",
                                            ANDROID_SDK_HASH)
    if not sdk_location:
      print("Please visit http://developer.android.com/sdk/index.html#Other "
            "for download link and extraction instructions.\n"
            "Please rerun this script afterwards with the flag\n"
            "\t--android_sdk=/path/to/android_sdk")
      sys.exit()

    setup_util.extract_tarfile(sdk_location, "r", directory, "Android SDK")
    os.remove(sdk_location)

  def android_update_sdk_path(self):
    """Checks bashrc and edits it to include Android SDK path."""
    # Check file paths are set up correctly and edit bashrc accordingly.
    if not os.path.exists(self.bashrc):
      # Create empty bashrc.
      open(self.bashrc, "a").close()
    with open(self.bashrc, "r") as f:
      lines = f.readlines()
    append = True
    for line in lines:
      if "ANDROID_HOME=" in line:
        if line.split("=")[1].strip() != self.sdk_path.strip():
          # Current ANDROID_HOME is wrong.
          setup_util.remove_line(self.bashrc, line, lines)
          self.bashrc_changed = True
        else:
          append = False  # Line is correct.
        break

    if append:
      with open(self.bashrc, "a") as f:
        f.write("export ANDROID_HOME=" + self.sdk_path + "\n")
      self.bashrc_changed = True

    path_update_tools = True
    path_update_platform = True
    with open(self.bashrc, "r") as f:
      for line in f:
        if re.search("export PATH.*/tools", line):
          path_update_tools = False
        if re.search("export PATH.*/platform-tools", line):
          path_update_platform = False

    if path_update_tools or path_update_platform:
      with open(self.bashrc, "a") as f:
        if path_update_tools:
          f.write("export PATH=$ANDROID_HOME/tools:$PATH\n")
        if path_update_platform:
          f.write("export PATH=$ANDROID_HOME/platform-tools:$PATH\n")
      self.bashrc_changed = True

  def android_update_platform_tools(self):
    """Update the Android SDK Platform Tools."""
    # This is very verbose, and requires a y/n response.
    # Android SDK Platform-tools must be installed before Tools.
    subprocess.call(self.sdk_path + "/tools/android update sdk -u -a -t " +
                    "platform-tools", shell=True)

  def android_get_relevant_sdk_updates(self, all_available_updates):
    """Check to see if any of the updates listed as available are relevant.

    Args:
      all_available_updates: A string of all the updates currently listed as
      available to download
    Returns:
      A list of all the package names which can be downloaded
    """
    packages = []
    for key in ANDROID_SDK_UPDATES:
      if key in all_available_updates:
        packages.append(ANDROID_SDK_UPDATES[key])
    return packages

  def android_update_sdk(self):
    """Checks for and performs any necessary Android SDK updates found."""
    updated = False
    logger.info("Checking for updates...")
    available_updates = subprocess.check_output(self.sdk_path +
                                                "/tools/android list sdk",
                                                shell=True)
    if "Android SDK Platform-tools" in available_updates:
      # Refresh available updates, as tools and build-tools won't show
      # without platform-tools.
      self.android_update_platform_tools()
      available_updates = subprocess.check_output(self.sdk_path +
                                                  "/tools/android list sdk",
                                                  shell=True)
      updated = True

    packages = self.android_get_relevant_sdk_updates(available_updates)
    if packages:
      subprocess.call(self.sdk_path + "/tools/android update sdk -u -a -t " +
                      ",".join(packages), shell=True)
      updated = True

    if not updated:
      logger.info("\tNo Android SDK updates required.")

  def android_download_ndk(self, directory):
    """Checks Linux version and downloads the appropriate Android NDK.

    Args:
      directory: String indication of location to unpack NDK
    """
    ndk_location = os.path.join(directory, "ndk.bin")
    os_version = subprocess.check_output("uname -m", shell=True)
    if os_version.strip() == "x86_64":
      # 64-bit
      url = "http://dl.google.com/android/ndk/android-ndk-r10e-linux-x86_64.bin"
      setup_util.download_file(url, ndk_location, "Android NDK",
                               ANDROID_NDK_HASH_64)
    else:
      # 32-bit
      url = "http://dl.google.com/android/ndk/android-ndk-r10e-linux-x86_64.bin"
      setup_util.download_file(url, ndk_location, "Android NDK",
                               ANDROID_NDK_HASH)
    if not ndk_location:
      print("Please visit http://developer.android.com/ndk/downloads/index.html"
            " for download link and extraction instructions.\n"
            "Please rerun this script afterwards with the flag\n"
            "\t--android_ndk=/path/to/android_ndk")
      sys.exit()

    # Allow execution by all parties.
    os.chmod(ndk_location, 0755)
    current_dir = os.getcwd()
    os.chdir(BASE_DIR)
    os.system(ndk_location)
    os.chdir(current_dir)
    os.remove(ndk_location)

  def android_update_ndk_path(self):
    """Checks bashrc and edits it to include Android NDK path."""
    path_update_ndk = True
    with open(self.bashrc, "r") as f:
      for line in f:
        if re.search("export PATH.*/android-ndk-r10e", line):
          path_update_ndk = False
    if path_update_ndk:
      with open(self.bashrc, "a") as f:
        f.write("export PATH=" + self.ndk_path + ":$PATH\n")
      self.bashrc_changed = True

    if self.bashrc_changed:
      # Sourcing bashrc cannot be done within a script.
      logger.warn("~/.bashrc has been changed. Please refresh your bashrc "
                  "running:\n   source ~/.bashrc")

  def setup_all(self):
    """Perform all necessary setup."""
    self.linux_requirements()
    self.android_install("SDK")
    self.android_update_sdk_path()
    self.android_update_sdk()
    self.android_install("NDK")
    self.android_update_ndk_path()
    logger.info("Setup complete")
