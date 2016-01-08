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

from distutils.spawn import find_executable
import logging
import os
import stat
import subprocess

import common
import util


"""Contains all necessary methods for setting up Android on Linux and Mac OSX.

All update and install methods will check if a download is necessary first.
All download methods will not.
"""

# The default names of the folders the Android SDK and Android NDK will be
#   downloaded/installed to.
SDK_NAMES = {
    common.LINUX: "android-sdk-linux",
    common.MAC: "android-sdk-macosx"
}

SDK_VERSIONS = {
    common.LINUX: ("http://dl.google.com/android/android-sdk_r24.4.1-linux.tgz",
                   "725bb360f0f7d04eaccff5a2d57abdd49061326d"),
    common.MAC: ("http://dl.google.com/android/android-sdk_r24.4.1-macosx.zip",
                 "85a9cccb0b1f9e6f1f616335c5f07107553840cd")
}

ANDROID_NDK = "android-ndk-r10e"
NDK_DOWNLOAD_PREFIX = "http://dl.google.com/android/ndk/"
NDK_VERSIONS = {
    common.LINUX_32: ("android-ndk-r10e-linux-x86.bin",
                      "b970d086d5c91c320c006ea14e58bd1a50e1fe52"),
    common.LINUX_64: ("android-ndk-r10e-linux-x86_64.bin",
                      "c685e5f106f8daa9b5449d0a4f21ee8c0afcb2f6"),
    common.MAC: ("android-ndk-r10e-darwin-x86_64.bin",
                 "b57c2b9213251180dcab794352bfc9a241bf2557")
}

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
    "Google Play services, revision 29": "extra-google-google_play_services",
    "Google Repository, revision 23": "extra-google-m2repository"
}


class AndroidSetup(object):
  """Contains all necessary methods for setting up the Android.

   Attributes:
     bash_changed: A boolean indicating whether or not the bashrc or bash
         profile has been edited by the script, indicating the user should call
         source ~/.bashrc or bash_profile
     bash: A string of the path of the user's bashrc/profile.
     sdk_path: A string of the location of the Android SDK package.
     ndk_path: A string of the location of the Android NDK package.
  Raises:
    SystemUnsupportedError: If the system not recognised as Linux or Mac OS X.
    BadDirectoryError: If the specified SDK or NDK directory does not exist.

  """

  def __init__(self, system, options):
    self.system = system
    if self.system == common.LINUX:
      self.bash = os.path.join(common.BASE_DIR, ".bashrc")
    elif self.system == common.MAC:
      self.bash = os.path.join(common.BASE_DIR, ".bash_profile")
    elif self.system == common.WINDOWS:
      raise common.SystemUnsupportedError(system)
    else:
      raise common.SystemUnsupportedError(system)
    self.bash_changed = False
    self.sdk_path = os.path.join(common.BASE_DIR, options.sdk_location)
    if not os.path.isdir(self.sdk_path):
      raise common.BadDirectoryError("--android_sdk", self.sdk_path)
    self.ndk_path = os.path.join(common.BASE_DIR, options.ndk_location)
    if not os.path.isdir(self.ndk_path):
      raise common.BadDirectoryError("--android_ndk", self.ndk_path)

  def android_install_sdk(self):
    """Checks the directory for installing Android SDK."""
    logging.info("Checking for Android SDK...")
    # Check if android path is already set up
    location = find_executable("android")
    if location:
      # Strip tools/android out of path
      self.sdk_path = os.path.dirname(os.path.dirname(location))
      logging.info("Android SDK found at " + self.sdk_path)
      return
    # Path is not set, but sdk may still exist
    location = util.check_dir(self.sdk_path, SDK_NAMES.get(self.system),
                              "tools/android")
    if location:
      self.sdk_path = location
      logging.info("Android SDK found at " + self.sdk_path)
      return
    logging.info("Android SDK not found. Downloading now.")
    self.android_download_sdk(self.sdk_path)

  def android_download_sdk(self, directory):
    """Download Android SDK and unpack into specified directory.

    Args:
      directory: String indication of location to unpack SDK to
    Raises:
      FileDownloadError: SDK tar or zip fails to download
      UnknownFileTypeError: If the file downloaded is neither a tar or a zip,
          and cannot be extracted.
    """
    url, file_hash = SDK_VERSIONS.get(self.system)
    suffix = util.get_file_type(url)
    sdk_location = os.path.join(directory, "sdk." + suffix)
    sdk_location = util.download_file(url, sdk_location, "Android SDK",
                                      file_hash)
    if not sdk_location:
      raise common.FileDownloadError("http://developer.android.com/sdk/index."
                                     "html#", "Please rerun this script "
                                     "afterwards with the flag\n"
                                     "\t--android_sdk=/path/to/android_sdk")
    if suffix == "tgz":
      util.extract_tarfile(sdk_location, "r", directory, "Android SDK")
    elif suffix == "zip":
      util.extract_zipfile(sdk_location, "r", directory, "Android SDK")
    else:
      raise common.UnknownFileTypeError(suffix, "Please manually extract "
                                        "Android SDK and rerun this script "
                                        "afterwards with the flag\n"
                                        "\t--android_sdk=/path/to/android_sdk")
    if self.system == common.MAC:
      # Sometimes, permissions aren't set correctly on tools/android on OSX.
      # Change permissions to allow execution by user
      android = os.path.join(directory,
                             SDK_NAMES.get(self.system) + "/tools/android")
      curr_permissions = os.stat(android)
      os.chmod(android, curr_permissions.st_mode | stat.S_IXUSR)
    # Update self.sdk_path to now include the SDK name
    self.sdk_path = os.path.join(self.sdk_path, SDK_NAMES.get(self.system))

  def android_update_sdk_path(self):
    """Checks PATH variable and edits bashrc/profile for Android SDK."""
    tools_update_path = True
    platform_update_path = True
    if find_executable("android"):
      tools_update_path = False
    if find_executable("adb"):
      platform_update_path = False

    if tools_update_path or platform_update_path:
      with open(self.bash, "a") as f:
        if tools_update_path:
          f.write("export PATH=" + os.path.join(self.sdk_path, "tools")
                  + ":$PATH\n")
        if platform_update_path:
          f.write("export PATH=" + os.path.join(self.sdk_path, "platform-tools")
                  + ":$PATH\n")
        self.bash_changed = True

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
    Raises:
      CommandFailedError: If tools/android was unable to run correctly for any
          reason.
    """
    packages = []
    for key in ANDROID_SDK_UPDATES:
      if key in all_available_updates:
        packages.append(ANDROID_SDK_UPDATES[key])
    return packages

  def android_get_all_sdk_updates(self):
    """Get a list of all possible android SDK updates as a string."""
    logging.info("Checking for updates...")
    try:
      updates = subprocess.check_output(self.sdk_path +
                                        "/tools/android list sdk", shell=True)
      return updates
    except subprocess.CalledProcessError:
      raise common.CommandFailedError(self.sdk_path + "/tools/android list sdk",
                                      "http://developer.android.com/tools/help/"
                                      "android.html")

  def android_update_sdk(self):
    """Checks for and performs any necessary Android SDK updates found."""
    updated = False
    available_updates = self.android_get_all_sdk_updates()
    if "Android SDK Platform-tools" in available_updates:
      # Refresh available updates, as tools and build-tools won't show
      # without platform-tools.
      self.android_update_platform_tools()
      available_updates = self.android_get_all_sdk_updates()
      updated = True

    packages = self.android_get_relevant_sdk_updates(available_updates)
    if packages:
      subprocess.call(self.sdk_path + "/tools/android update sdk -u -a -t " +
                      ",".join(packages), shell=True)
      updated = True
    if not updated:
      logging.info("\tNo Android SDK updates required.")

  def android_install_ndk(self):
    """Checks the directory for installing Android NDK."""
    logging.info("Checking for Android NDK...")
    # Check if android path is already set up
    location = find_executable("ndk-build")
    if location:
      # Strip ndk-build out of path name
      self.sdk_path = os.path.dirname(location)
      logging.info("Android NDK found at " + self.ndk_path)
      return
    # Path is not set, but ndk may still exist
    location = util.check_dir(self.ndk_path, ANDROID_NDK, "ndk-build")
    if location:
      self.ndk_path = location
      logging.info("Android NDK found at " + self.ndk_path)
      return
    logging.info("Android NDK not found. Downloading now.")
    self.android_download_ndk(self.ndk_path)

  def android_download_ndk(self, directory):
    """Checks OS version and downloads the appropriate Android NDK.

    Args:
      directory: String indication of location to unpack NDK
    Raises:
      FileDownloadError: NDK bin failes to download
    """
    ndk_location = os.path.join(directory, "ndk.bin")
    if self.system == common.LINUX:
      os_version = subprocess.check_output("uname -m", shell=True)
      if os_version.strip() == "x86_64":
        url, file_hash = NDK_VERSIONS.get(common.LINUX_64)
      else:
        url, file_hash = NDK_VERSIONS.get(common.LINUX_32)
    else:
      url, file_hash = NDK_VERSIONS.get(self.system)
    url = NDK_DOWNLOAD_PREFIX + url
    ndk_location = util.download_file(url, ndk_location, "Android NDK",
                                      file_hash)
    if not ndk_location:
      raise common.FileDownloadError("http://developer.android.com/ndk/"
                                     "downloads/index.html", "Please rerun "
                                     "this script afterwards with the flag\n"
                                     "\t--android_ndk=/path/to/android_ndk")

    # Allow execution by all parties.
    os.chmod(ndk_location, 0755)
    current_dir = os.getcwd()
    os.chdir(common.BASE_DIR)
    os.system(ndk_location)
    os.chdir(current_dir)
    os.remove(ndk_location)

  def android_update_ndk_path(self):
    """Checks bashrc/profile and edits it to include Android NDK path."""
    if not find_executable("ndk-build"):
      with open(self.bash, "a") as f:
        f.write("export PATH=" + self.ndk_path + ":$PATH\n")
      self.bash_changed = True

  def has_bash_changed(self):
    # Sourcing bashrc/profile cannot be done within a script.
    return self.bash_changed

  def setup_all(self):
    """Perform all necessary setup."""
    self.android_install_sdk()
    self.android_update_sdk_path()
    self.android_update_sdk()
    self.android_install_ndk()
    self.android_update_ndk_path()
    logging.info("Android setup complete")
