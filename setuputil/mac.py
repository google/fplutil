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

from datetime import date
from distutils.spawn import find_executable
import logging
import os
import platform
import subprocess
import urlparse

import common
import util

"""Contains all necessary methods for setting up Mac OS."""

# Mac OS X versions and names
OSX_10_4_TIGER = 4
OSX_10_5_LEOPARD = 5
OSX_10_6_SNOW_LEOPARD = 6
OSX_10_7_LION = 7
OSX_10_8_MOUNTAIN_LION = 8
OSX_10_9_MAVERICKS = 9
OSX_10_10_YOSEMITE = 10
OSX_10_11_EL_CAPITAN = 11

# The path from the base CMake directory to where the executables are
CMAKE_BIN = "CMake.app/Contents/bin"

# SHA-1 hash for the cwebp and ant tarfile
CWEBP_HASH = "18c9a9bbfdd988b44d393895bad7de422b40228c"
ANT_HASH = "2442eff9ff2aa2b3df4aac75c9d9681232fc747a"

# Version of cwebp and ant that will be downloaded
CWEBP_VERSION = "libwebp-0.4.4-mac-10.9"
ANT_VERSION = "apache-ant-1.9.6"

# Download link for cwebp and ant tarfile
CWEBP_URL = ("http://downloads.webmproject.org/releases/webp/"
             + CWEBP_VERSION + ".tar.gz")
ANT_URL = ("https://www.apache.org/dist/ant/binaries/" +
           ANT_VERSION + "-bin.tar.gz")

# Download prefixes for cmake and MacPorts. All download links for cmake and
#   MacPorts must have the prefix in front.
CMAKE_DOWNLOAD_PREFIX = "https://cmake.org/files/"
MACPORTS_DOWNLOAD_PREFIX = "https://distfiles.macports.org/MacPorts/MacPorts-"

# A list of supported OSX Versions, with their MacPorts download link and
#   corresponding SHA-1 hash.
# version: (download link, hash)
MACPORTS_VERSIONS = {
    OSX_10_4_TIGER: ("2.3.3-10.4-Tiger.dmg",
                     "52fe9d7f413d7cf81ed3e59b93a14cbb892d77bf"),
    OSX_10_5_LEOPARD: ("2.3.4-10.5-Leopard.dmg",
                       "bbdf05f1c198a5b962afaa00e44785c0c61e4699"),
    OSX_10_6_SNOW_LEOPARD: ("2.3.4-10.6-SnowLeopard.pkg",
                            "d3dab3e181f5febab521b1dbe3d56f988107b504"),
    OSX_10_7_LION: ("2.3.4-10.7-Lion.pkg",
                    "1847f4b50b11430eddbfed4e67b53452c2ab2a4f"),
    OSX_10_8_MOUNTAIN_LION: ("2.3.4-10.8-MountainLion.pkg",
                             "69653efc649505db3d4e0315f75be07271bebc71"),
    OSX_10_9_MAVERICKS: ("2.3.4-10.9-Mavericks.pkg",
                         "7a8d988869eb608e6b0ba49ccebb0dd0b670d140"),
    OSX_10_10_YOSEMITE: ("2.3.4-10.10-Yosemite.pkg",
                         "79d9591a34fa76774a1b4208af530f49e181bb8b"),
    OSX_10_11_EL_CAPITAN: ("2.3.4-10.11-ElCapitan.pkg",
                           "cd4aee25054d5d0b487a7a6f5200fd586c62c26c")
}

# A list of supported OSX Versions, with their method of installing Xcode and
#   the corresponding information required.
# version: (method, info)
XCODE_VERSIONS = {
    OSX_10_4_TIGER: ("INSTRUCTION",
                     "Xcode 2.4.1 and Xcode 2.6 Developer Tools"),
    OSX_10_5_LEOPARD: ("INSTRUCTION",
                       "Xcode 3.0 and Xcode 3.1 Developer Tools"),
    OSX_10_6_SNOW_LEOPARD: ("INSTRUCTION", "Xcode 3.2.6"),
    OSX_10_7_LION: ("LINK", "http://itunes.apple.com/us/app/xcode/id497799835"),
    OSX_10_8_MOUNTAIN_LION: ("LINK", "http://itunes.apple.com/us/app/xcode/"
                             "id497799835"),
    OSX_10_9_MAVERICKS: ("COMMAND", "xcode-select --install"),
    OSX_10_10_YOSEMITE: ("COMMAND", "xcode-select --install"),
    OSX_10_11_EL_CAPITAN: ("COMMAND", "xcode-select --install")
}

# A list of supported OSX Versions, with their cmake download link and
#    corresponding SHA-1 hash
# version: (method, hash)
CMAKE_VERSIONS = {
    OSX_10_4_TIGER: ("v3.3/cmake-3.3.2-Darwin-universal.tar.gz",
                     "88ad7ae2692a5f3f296f14ebbdc490e065b9bc0f"),
    OSX_10_5_LEOPARD: ("v3.3/cmake-3.3.2-Darwin-universal.tar.gz",
                       "88ad7ae2692a5f3f296f14ebbdc490e065b9bc0f"),
    OSX_10_6_SNOW_LEOPARD: ("v3.3/cmake-3.3.2-Darwin-universal.tar.gz",
                            "88ad7ae2692a5f3f296f14ebbdc490e065b9bc0f"),
    OSX_10_7_LION: ("v3.4/cmake-3.4.1-Darwin-x86_64.tar.gz",
                    "2667dca9103b227a0235de745ac40260052fe284"),
    OSX_10_8_MOUNTAIN_LION: ("v3.4/cmake-3.4.1-Darwin-x86_64.tar.gz",
                             "2667dca9103b227a0235de745ac40260052fe284"),
    OSX_10_9_MAVERICKS: ("v3.4/cmake-3.4.1-Darwin-x86_64.tar.gz",
                         "2667dca9103b227a0235de745ac40260052fe284"),
    OSX_10_10_YOSEMITE: ("v3.4/cmake-3.4.1-Darwin-x86_64.tar.gz",
                         "2667dca9103b227a0235de745ac40260052fe284"),
    OSX_10_11_EL_CAPITAN: ("v3.4/cmake-3.4.1-Darwin-x86_64.tar.gz",
                           "2667dca9103b227a0235de745ac40260052fe284")
}

JAVA_UPDATE_URL = ("http://support.apple.com/downloads/DL1572/en_US/"
                   "javaforosx.dmg")
JAVA_UPDATE_HASH = "c0b05cb70904350c12d4f34c8afd3fa51bc47d72"

MACPORTS_LOCATION = "/opt/local/bin/port"


class MacSetup(common.Setup):
  """Contains all necessary methods for setting up the Mac.

  Attributes:
    os_version: An int indicating the user's current version of OS X.
    bash_profile: A string of the path of the user's bash profile.
  Raises:
    VersionUnsupportedError: If Mac OS is a version other than OS X.
    VersionTooHighError: If Mac OSX version is higher than 10.11 (El Capitan)
    VersionTooLowError: If Mac OSX version is lower than 10.4 (Tiger)
    BadDirectoryError: If a path given in the cwebp, cmake or ant flag does not
        exist.
  """

  def __init__(self, options, skip_version_check=False):
    common.Setup.__init__(self, options)
    major, minor, _ = get_mac_version()
    if major != "10":
      # Script only supports Mac OS X
      raise common.VersionUnsupportedError(major)
    self.os_version = int(minor)
    if self.os_version > OSX_10_11_EL_CAPITAN:
      if skip_version_check:
        self.os_version = OSX_10_11_EL_CAPITAN
      else:
        raise common.VersionTooHighError(minor)
    elif self.os_version < OSX_10_4_TIGER:
      if skip_version_check:
        self.os_version = OSX_10_4_TIGER
      else:
        raise common.VersionTooLowError(minor)
    self.macports = not options.no_macports
    self.install_android_prereqs = not options.no_android

  def mac_install_xcode(self):
    """Check for and install Xcode and Xcode command line tools.

    Raises:
      InstallInterruptError: If the user cancels either the Xcode or Xcode
          Command Line Tools setup.
      PermissionsDeniedError: If sudo permissions are not granted for accepting
          the Xcode terms and conditions.
      CommandFailedError: Xcode is unable to install using its command line
          installer
    """
    if find_executable("xcodebuild"):
      logging.info("Xcode already installed.")
    else:
      logging.warn("Please download and install Xcode from the Apple "
                   "Developers website:\nhttps://itunes.apple.com/us/app/"
                   "xcode/id497799835?ls=1&mt=12")
      if not util.wait_for_installation("xcodebuild -version"):
        raise common.InstallInterruptError("Xcode")
      # View and accept terms and conditions for Xcode
      logging.info("Please accept the Xcode terms and conditions.\nSudo may "
                   "prompt you for your password.")
      try:
        subprocess.call("sudo xcodebuild -license", shell=True)
      except subprocess.CalledProcessError:
        raise common.PermissionDeniedError("Xcode license", "Please enter your "
                                           "password to accept the Xcode terms "
                                           "and conditions")

    # Checks to see if xcode command line tools is installed
    if find_executable("xcode-select"):
      logging.info("Xcode command line tools already installed.")
      return
    else:
      logging.info("Xcode Command Line Tools not installed. "
                   "Installing Xcode Command Line Tools now.")
    method, info = XCODE_VERSIONS.get(self.os_version, (None, None))
    if method == "INSTRUCTION":
      logging.warn("Please download " + info + " from the Apple "
                   "Developers website:\thttps://developer.apple.com/"
                   "downloads/index.action\nFor more information, see "
                   "https://guide.macports.org/#installing.xcode")
    elif method == "LINK":
      logging.warn("Please download xcode from the Mac Apple Store:\n"
                   + info + "\nFor more information, see "
                   "https://guide.macports.org/#installing.xcode")
    elif method == "COMMAND":
      logging.warn("Please click 'Install' in the dialog box.")
      try:
        subprocess.call(info, shell=True)
      except subprocess.CalledProcessError:
        raise common.CommandFailedError(info, "http://railsapps.github.io/"
                                              "xcode-command-line-tools.html")
    # Wait for user to complete setup
    if not util.wait_for_installation("xcode-select -p"):
      raise common.InstallInterruptError("Xcode Command Line Tools")
    logging.info("Xcode successfully installed.")

  def mac_install_cmake(self):
    """Check for and install cmake.

    Assumes that if cmake is already installed, then the user has correctly set
    their path variable such that the command "cmake --version" will work.

    Raises:
      FileDownloadError: If the cmake tar fails to download, or is incorrectly
          downloaded.
      ExtractionError: If the cmake tar cannot be properly extracted.
    """
    if find_executable("cmake"):
      logging.info("CMake already installed.")
      return
    cmake_version = util.get_file_name(
        CMAKE_VERSIONS.get(self.version)[0], False)
    location = util.check_dir(self.cmake_path, cmake_version, "bin/cmake")
    if location:
      self.cmake_path = location
      logging.info("CMake found at " + self.cmake_path)
      return

    logging.info("CMake not installed. Downloading now.")
    url, file_hash = CMAKE_VERSIONS.get(self.os_version, (None, None))
    url = urlparse.urljoin(CMAKE_DOWNLOAD_PREFIX, url)
    location = os.path.join(common.BASE_DIR, "cmake.tar.gz")
    location = util.download_file(url, location, "cmake", file_hash)
    if not location:
      raise common.FileDownloadError("https://cmake.org/download/", "Please "
                                     "rerun this script afterwards with the "
                                     "flag\n\t--cmake=/path/to/cmake")
    if not util.extract_tarfile(location, "r:gz", self.cmake_path, "cmake"):
      raise common.ExtractionError(location)
    logging.info("CMake successfully installed.")

  def mac_install_cwebp(self):
    """Check for and install cwebp.

    Assumes that if cwebp is already installed, then the user has correctly set
    their path variable such that the command "cwebp -h" will work.
    Raises:
      FileDownloadError: If the cwebp tar fails to download, or is incorrectly
          downloaded.
      ExtractionError: If the cwebp tar cannot be properly extracted.
    """
    if find_executable("cwebp"):
      logging.info("cwebp already installed.")
      return
    location = util.check_dir(self.cwebp_path, CWEBP_VERSION, "cwebp")
    if location:
      self.cwebp_path = location
      logging.info("cwebp found at " + self.cwebp_path)
      return
    logging.info("cwebp not installed. Downloading now.")
    location = os.path.join(common.BASE_DIR, "cwebp.tar.gz")
    location = util.download_file(CWEBP_URL, location, "cwebp", CWEBP_HASH)
    if not location:
      raise common.FileDownloadError("https://developers.google.com/speed/webp/"
                                     "docs/precompiled", "Please rerun this "
                                     "script afterwards with the flag\n"
                                     "\t--cwebp=/path/to/cwebp")
    if not util.extract_tarfile(location, "r:gz", self.cwebp_path, "cwebp"):
      raise common.ExtractionError(location)
    logging.info("cwebp successfully installed.")

  def mac_install_macports(self):
    """Check for and install MacPorts.

    Raises:
      FileDownloadError: If the MacPorts package fails to download, or is
          incorrectly downloaded.
      UnknownFileTypeError: If the type of the downloaded package does not match
          any of the supported types.
    """
    if os.path.isfile(MACPORTS_LOCATION):
      logging.info("MacPorts already installed.")
      return
    else:
      logging.info("MacPorts not installed. Downloading now.")
    url, file_hash = MACPORTS_VERSIONS.get(self.os_version)
    url = MACPORTS_DOWNLOAD_PREFIX + url
    suffix = util.get_file_type(url)
    location = os.path.join(common.BASE_DIR, "macports." + suffix)
    location = util.download_file(url, location, "macports", file_hash)
    if not location:
      raise common.FileDownloadError("https://guide.macports.org/chunked/"
                                     "installing.macports.html", "Please rerun "
                                     "this script again afterwards.")
    logging.info("Installing Mac Ports. Sudo may prompt you for your password.")
    if suffix == "pkg":
      try:
        subprocess.call("sudo installer -pkg " + location + " -target /",
                        shell=True)
      except subprocess.CalledProcessError:
        raise common.PermissionDeniedError("installer", "Please enter your "
                                           "password to install MacPorts")
    elif suffix == "dmg":
      subprocess.call("hdiutil attach " + location, shell=True)
    else:
      raise common.UnknownFileTypeError(suffix, "Please manually install "
                                        "MacPorts, or run this script again "
                                        "with the flag\n\t--no_macports")
    self.bash_profile_changed = True  # Mac ports installation will probably
                                      # change the bash profile, refresh just
                                      # in case

  def mac_install_image_magick(self):
    """Check for and install ImageMagick.

    Using MacPorts to install ImageMagick can take a long time, so the option
    to install using Homebrew is provided. However, installation with Homebrew
    doesn't always install the necessary dependencies and libraries, so
    MacPorts is preferred.

    Raises:
      InstallFailedError: If, for any reason, ImageMagick cannot be installed.
    """
    if find_executable("convert"):
      logging.info("Image Magick already installed.")
      return
    logging.info("ImageMagick not installed. Installing now.\n")
    if os.path.isfile(MACPORTS_LOCATION):
      # Warning, this takes forever
      logging.info("This process may take up to an hour to complete.")
      if (raw_input("Do you wish to attempt installation using MacPorts? (y/n)")
          .lower().startswith("y")):
        logging.info("Sudo may prompt you for your password.")
        try:
          subprocess.call("sudo " + MACPORTS_LOCATION + " install ImageMagick",
                          shell=True)
          return
        except subprocess.CalledProcessError:
          logging.warn("MacPorts encountered an error installing ImageMagick.\n"
                       "Please run this script to try again, or attempt "
                       "installation using Homebrew or manually.")
    if (raw_input("Attempt installation with Homebrew? (y/n)")
        .lower().startswith("y")):
      if find_executable("brew"):
        # Try installing using Homebrew, however Homebrew installation has been
        # known to miss dependencies.
        try:
          subprocess.call("brew install imagemagick --with-librsvg", shell=True)
          logging.warn("Homebrew insall of ImageMagick may miss depenecies.")
          return
        except subprocess.CalledProcessError:
          logging.warn("Homebrew encountered an error installing ImageMagick.\n"
                       "Please run this script to try again, or attempt manual "
                       "installataion.")
      else:
        logging.warn("ImageMagick requires either MacPorts or Homebrew to "
                     "install.\nFor more information on Homebrew, see: "
                     "http://brew.sh/\nFor more information on MacPorts, see: "
                     "https://guide.macports.org/")
    raise common.InstallFailedError("ImageMagick", "http://www.imagemagick.org/"
                                    "script/binary-releases.php#macosx",
                                    "Please rerun this script to try again.")

  def mac_install_ant(self):
    """Check for and install Apache Ant.

    Raises:
      FileDownloadError: If the ant tar fails to download, or is incorrectly
          downloaded.
      ExtractionError: If the ant tar cannot be properly extracted.
    """
    if find_executable("ant"):
      logging.info("Apache Ant already installed.")
      return
    location = util.check_dir(self.ant_path, ANT_VERSION, "bin/ant")
    if location:
      self.ant_path = location
      logging.info("Apache Ant already installed.")
      return
    logging.info("Apache Ant not installed. Installing now.")
    location = os.path.join(common.BASE_DIR, "ant.tar.gz")
    location = util.download_file(ANT_URL, location, "Ant", ANT_HASH)
    if not location:
      raise common.FileDownloadError("https://www.apache.org/dist/ant/"
                                     "binaries/", "Please rerun this script "
                                     "again afterwards.")
    if not util.extract_tarfile(location, "r:gz", self.ant_path, "Ant"):
      raise common.ExtractionError(location)
    logging.info("Apache Ant successfully installed.")

  def update_java(self):
    """Update Java Runtime Environment.

    There's a bug in the Java installer that sees Yosemite and El Capitan
    (10.10 and 10.11) as '10.1', and hence the android won't run. The official
    Apple package, which is installed in this function, doesn't have that bug.

    Raises:
      InstallInterruptError: If the wait for installing Java update was
          cancelled.
    """
    if self.os_version < OSX_10_10_YOSEMITE:
      return
    logging.info("Java update required by Android.")
    location = os.path.join(common.BASE_DIR, "java.dmg")
    location = util.download_file(JAVA_UPDATE_URL, location, "java",
                                  JAVA_UPDATE_HASH)
    if not location:
      logging.warn("Please visit https://support.apple.com/kb/DL1572 for "
                   "download link and extraction instructions.\nPlease rerun "
                   "this script afterwards to complete setup.")
    logging.info("Finder will open. Double click on \"JavaForOSX.pgk\" to "
                 "continue installation")
    subprocess.call("hdiutil attach " + location, shell=True)

  def mac_update_path(self):
    """Checks PATH variable and edits the bash profile accordingly.

    Check for the appropriate path for cmake and cwebp, and edit the bash
    profile to include it. Don't check for MacPorts or ImageMagick, as those
    are managed by their own installation scripts.
    """
    optbin_update = True
    optsbin_update = True
    cmake_path_update = True
    cwebp_path_update = True
    ant_path_update = True
    if find_executable("convert"):
      optbin_update = False
      optsbin_update = False
    if find_executable("cmake"):
      cmake_path_update = False
    if find_executable("cwebp"):
      cwebp_path_update = False
    if find_executable("ant"):
      ant_path_update = False
    if optbin_update or optsbin_update or cwebp_path_update or ant_path_update:
      with open(self.bash_profile, "a") as f:
        todays_date = (str(date.today().year) + "-" + str(date.today().month)
                       + "-" + str(date.today().day))
        f.write("\n# The following block was inserted by fplutil/bin/"
                "setup_all_prereqs.py on " + todays_date + "\n")
        if optbin_update:
          f.write("export PATH=/opt/local/bin:$PATH\n")
        if optsbin_update:
          f.write("export PATH=/opt/local/sbin:$PATH\n")
        if cmake_path_update:
          cmake_version = util.get_file_name(
              CMAKE_VERSIONS.get(self.version)[0], False)
          cmake_bin = os.path.join(self.cmake_path,
                                   os.path.join(cmake_version, CMAKE_BIN))
          f.write("export PATH=" + cmake_bin + ":$PATH\n")
        if cwebp_path_update:
          cwebp_bin = os.path.join(self.cwebp_path,
                                   os.path.join(CWEBP_VERSION, "bin"))
          f.write("export PATH=" + cwebp_bin + ":$PATH\n")
        if ant_path_update:
          ant_bin = os.path.join(self.ant_path,
                                 os.path.join(ANT_VERSION, "bin"))
          f.write("export PATH=" + ant_bin + ":$PATH\n")
        f.write("\n")
        self.bash_profile_changed = True

  def setup_all(self):
    """Performs all necessary set up."""
    self.mac_install_xcode()
    self.mac_install_cmake()
    self.mac_install_cwebp()
    self.mac_install_ant()
    if self.install_android_prereqs:
      self.mac_update_java()
    if self.macports:
      self.mac_install_macports()
    self.mac_install_image_magick()
    self.mac_update_path()
    logging.info("Set up complete!")


def get_mac_version():
  version, _, _ = platform.mac_ver()
  return tuple(version.split("."))


