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


"""Installs all necessary requirements for building.

Determines user's OS and downloads and installs prerequisitexs accoringly.
"""

import re
import sys
import subprocess
import urllib
import tarfile
import os
import stat

def remove_line(filename, to_remove, all_lines=""):
  """Removes a any instances of a line from a file.

  Args:
    filename: A string name (including path) of the text file
    to_remove: The string that is to be removed from the text file
    all_lines: An option string representing the whole of the original file.
        If no string is provided, read the file first
  """
  if not all_lines:
    with open(filename, "r") as f:
      all_lines = f.readlines()
  with open(filename, "w") as f:
    for line in all_lines:
      if line != to_remove:
        f.write(line)

def download_file(url, location, name_of_file):
    """ Attempts to download a file from the internet to the specified location.

    If the file is not found, or the retrieval of the file failed, the
    exception will be caught and the system will exit.

    Args:
      url: A string of the URL to be retrieved.
      location: A string of the path the file will be downloaded to.
      name_of_file: A string with the name of the file, for printing purposes.

    Returns:
      The location of the file, if the download is successful.
    """
    try:
      location, headers = urllib.urlretrieve(url, location)
      print "\t" + name_of_file + " successfully downloaded."
      return location
    except IOError, e:
      sys.stderr.write("\t" + name_of_file + " failed to download.\n")
      sys.exit()

def extract_tarfile(tar_location, extract_location, name_of_file):
    """ Attempts to extract a tar file (tgz).

    If the file is not found, or the extraction of the contents failed, the
    exception will be caught and the system will exit.

    Args:
      tar_location: A string of the current location of the tgz file
      extract_location: A string of the path the file will be extracted to.
      name_of_file: A string with the name of the file, for printing purposes.
    """
    try:
      tar = tarfile.open(tar_location, 'r')
      tar.extractall(path=extract_location, members=tar)
      os.remove(tar_location)
      print "\t" + name_of_file + " sucessfully extracted"
    except Exception as e:
      sys.stderr.write("\t" + name_of_file + " failed to extract.\n")
      sys.exit()


class Linux_setup:
  """ Contains all necessary methods for setting up the Linux environment,
      including Android.

  Attributes:
    bashrc_changed: A boolean indicating whether or not the bashrc has been
        edited by the script, indicating the user should call source ~/.bashrc
    home: A string of the user's home directory, as ~ is not always guaranteed
        to work.
    home_contents: A string of the folders in the home directory. Used for
        determing what android packages have already been installed.
    bashrc: A string of the path of the user's bashrc.
    sdk_path: A string of the location of the Android SDK package.
    ndk_path: A string of the location of the Android NDK package.
  """

  def __init__(self):
    """ Inits Linux_setup by preparing all file paths """
    self.bashrc_changed = False
    self.home = os.path.expanduser('~')
    self.home_contents = subprocess.check_output("ls " + self.home, shell=True)
    self.bashrc = os.path.join(self.home, ".bashrc")
    self.sdk_path = os.path.join(self.home, "android-sdk-linux")
    self.ndk_path = os.path.join(self.home, "android-ndk-r10e")

  def linux_requirements(self):
    """ Installs all necessary linux programs. If the program has already been
        intalled, it will be skipped. """
    print "Installing:\n  + autoconf, automake and libtool\n  + cmake\n",\
          "  + cwebp\n  + GLU\n  + ImageMagick\n  + OpenGL\n",\
          "  + OSS Proxy Daemon\n  + Python\n  + Ragel\n",\
          "  + Java 1.7\n  + ant\n", \
          "Sudo may prompt you for your password."
    subprocess.call("sudo apt-get install autoconf automake cmake imagemagick "
                    "libglapi-mesa libglu1-mesa-dev libtool osspd python ragel "
                    "webp openjdk-7-jdk ant", shell=True)

  def android_install_sdk(self):
    """ Check if Android SDK has already been installed, and if not, download
        and install it. """
    print "Checking for Android SDK..."
    # Check if android-sdk is in the home directory
    if "android-sdk-linux/" not in self.home_contents:
      print "\tAndroid SDK not found. Downloading now."
      sdk_location = os.path.join(self.home, "sdk.tgz")
      url = "http://dl.google.com/android/android-sdk_r24.4.1-linux.tgz"
      sdk_location = download_file(url, sdk_location, "Android SDK")
      extract_tarfile(sdk_location, self.home, "Android SDK")
    else:
      print "\tAndroid SDK found at " + self.sdk_path

  def android_update_sdk_path(self):
    """ Checks the bashrc has been set up correctly for the Android SDK paths,
        and if not, edit the bashrc accordingly """
    # Check file paths are set up correctly and edit bashrc accordingly
    if not os.path.exists(self.bashrc):
      # create empty bashrc
      open(self.bashrc, 'a').close()
    with open(self.bashrc, "r") as f:
      lines = f.readlines()
    append = True
    for line in lines:
      if "ANDROID_HOME=" in line:
        if line.split('=')[1].strip() != self.sdk_path.strip():
          # Current ANDROID_HOME is wrong
          remove_line(self.bashrc, line, lines)
          self.bashrc_changed = True
        else:
          append = False # line is correct
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
      with open(self.bashrc, "w") as f:
        if path_update_tools:
          f.write("export PATH=$ANDROID_HOME/tools:$PATH\n")
        if path_update_platform:
          f.write("export PATH=$ANDROID_HOME/platform-tools:$PATH\n")
      self.bashrc_changed = True

  def android_update_platform_tools(self):
      """ Update the Android SDK Platform Tools """
      # This is very verbose, and requires a y/n response
      # Android SDK Platform-tools must be installed before Tools
      subprocess.call(self.sdk_path + "/tools/android update sdk -u -a -t platform-tools",
                      shell=True)

  def android_get_relevant_sdk_updates(self, all_available_updates):
    """ Check to see if any of the updates listed as available are relevant

    Args:
      all_available_udpates: A string of all the updates currently listed as
          available to download
    Returns:
      A list of all the package names which can be downloaded
    """
    packages = []
    if "Android SDK Tools" in all_available_updates:
      packages.append("tools")
    if "Android SDK Build-tools" in all_available_updates:
      packages.append("build-tools-23.0.2")
    if "SDK Platform Android 5.0" in all_available_updates:
      packages.append("android-21")
    if "Android TV ARM EABI v7a System Image, Android API 21" in all_available_updates:
      packages.append("sys-img-armeabi-v7a-android-tv-21")
    # Support libraries
    if "Android Support Repository, revision 25" in all_available_updates:
      packages.append("extra-android-m2repository")
    if "Android Support Library, revision 23.1.1" in all_available_updates:
      packages.append("extra-android-support")
    # Google APIs
    if "Google Play services, revision 28" in all_available_updates:
      packages.append("extra-google-google_play_services")
    if "Google Repository, revision 23" in all_available_updates:
      packages.append("extra-google-m2repository")
    return packages

  def android_update_sdk(self):
    """ Check to see if the Android SDK needs any updates, and performs any
        necessary updates found """
    updated = False
    print "Checking for updates..."
    available_updates = subprocess.check_output(self.sdk_path + "/tools/android list sdk",
                                                shell=True)
    if "Android SDK Platform-tools" in available_updates:
      # Refresh available updates, as tools and build-tools won't show without
      # platform-tools
      self.android_update_platform_tools()
      available_updates = subprocess.check_output(self.sdk_path + "/tools/android list sdk",
                                                  shell=True)
      updated = True

    packages = self.android_get_relevant_sdk_updates(available_updates)
    if packages:
      subprocess.call(self.sdk_path + "/tools/android update sdk -u -a -t " +
                      ','.join(packages), shell=True)
      updated = True

    if not updated:
      print "\tNo Android SDK updates required."

  def android_download_ndk(self):
    """ Check what version of Linux is being used, and download the appropriate
        Android NDK.

        Returns:
          The string location of the NDK binary
    """
    os_version = subprocess.check_output("uname -m", shell=True)
    ndk_version = ""
    if os_version.strip() == "x86_64":
      # 64-bit
      ndk_version = "android-ndk-r10e-linux-x86_64.bin"
    else:
      # 32-bit
      ndk_version = "android-ndk-r10e-linux-x86.bin"
    url = "http://dl.google.com/android/ndk/" + ndk_version
    ndk_location = os.path.join(self.home, ndk_version)
    download_file(url, ndk_location, "Android NDK")
    return ndk_location

  def android_install_ndk(self):
    """ Check if Android NDK has already been installed, and if not, download
        and install it. """
    print "Checking for Android NDK..."
    # Check if android-ndk is already in the home directory
    if "android-ndk-r10e/" not in self.home_contents:
      print "\tAndroid NDK not found. Downloading now."
      ndk_location = self.android_download_ndk()
      # Allow execution by all parties
      os.chmod(ndk_location, 0755)
      current_dir = os.getcwd()
      os.chdir(self.home)
      os.system(ndk_location)
      os.chdir(current_dir)
      os.remove(ndk_location)
    else:
      print "\tAndroid NDK found at " + self.ndk_path

  def android_update_ndk_path(self):
    """ Checks the bashrc has been set up correctly for the Android NDK paths,
        and if not, edit the bashrc accordingly """
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
      sys.stderr.write("~/.bashrc has been changed. Please refresh your bashrc " +
                       "running: \n   exec bash")

  def setup_all(self):
    """ Perform all necessary setup """
    self.linux_requirements()
    self.android_install_sdk()
    self.android_update_sdk_path()
    self.android_update_sdk()
    self.android_install_ndk()
    self.android_update_ndk_path()
    print "Setup complete"


def main():
  if sys.platform.startswith("linux"):
    # linux or linux2
    setup = Linux_setup()
    setup.setup_all()
  elif sys.platform == "win32" or sys.platform == "cygwin":
    # Windows or Cygwin
    print "Windows not supported yet"
  elif sys.platform == "darwin":
    # Mac OS X
    print "Mac not supported yet"
  else:
    # Unsupported OS
    print sys.platform + " not supported."


if __name__ == "__main__":
  sys.exit(main())
