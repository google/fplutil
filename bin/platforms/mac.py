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
from optparse import OptionParser
import os
import platform
import subprocess
import urlparse

import setup_util

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

# The user's home directory, and the default location for installing
#   cmake and cwebp folders.
BASE_DIR = os.path.expanduser("~")

# The default names of the folders cmake and cwebp will be downloaded and
#   installed to.
CWEBP_DIR = "cwebp"
CMAKE_DIR = "cmake"

# SHA-1 hash for the cwebp tarfile
CWEBP_HASH = "18c9a9bbfdd988b44d393895bad7de422b40228c"
# Version of cwebp that will be downloaded
CWEBP_VERSION = "libwebp-0.4.4-mac-10.9"
# Download link for cwebp tarfile
CWEBP_URL = ("http://downloads.webmproject.org/releases/webp/"
             + CWEBP_VERSION + ".tar.gz")

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

MACPORTS_LOCATION = "/opt/local/bin/port"

parser = OptionParser()
parser.add_option("--cwebp", action="store", type="string",
                  dest="cwebp_location", default=BASE_DIR,
                  help="Specify path to cwebp directory. Can either be a "
                       "reference to existing cwebp tools, or an indication "
                       "of where to install them. Path can either be the "
                       "full file path, or relative to the home directory.")
parser.add_option("--cmake", action="store", type="string",
                  dest="cmake_location", default=BASE_DIR,
                  help="Specify path to CMake directory. Can either be a "
                       "reference to existing CMake tools, or an indication "
                       "of where to install them. Path can either be the "
                       "full file path, or relative to the home directory.")
parser.add_option("--no_macports", action="store_true",
                  dest="no_macports", default=False,
                  help="Don't attempt to install Mac Ports. If Mac Ports is "
                       "already installed, then installation will be skipped "
                       "irrespectively. Intended to people that wish to "
                       "install ImageMagick using Homebrew.")

(options, args) = parser.parse_args()


class MacSetup(object):
  """Contains all necessary methods for setting up the Mac.

  Attributes:
    bash_profile_changed: A boolean indicating whether or not the bash profile
        has been edited by the script, and the user should call source.
    os_version: An int indicating the user's current version of OS X.
    bash_profile: A string of the path of the user's bash profile.
    cwebp_path: A string of the path to the location of the cwebp directory.
    cmake_path: A string of the path to the location of the cmake directory.
  """

  def __init__(self, skip_version_check=False):
    self.bash_profile_changed = False
    major, minor, _ = get_mac_version()
    if major != "10":
      # Script only supports Mac OS X
      raise VersionUnsupportedError(major)
    self.os_version = int(minor)
    if self.os_version > OSX_10_11_EL_CAPITAN:
      if skip_version_check:
        self.os_version = OSX_10_11_EL_CAPITAN
      else:
        raise VersionTooHighError(minor)
    elif self.os_version < OSX_10_4_TIGER:
      if skip_version_check:
        self.os_version = OSX_10_4_TIGER
      else:
        raise VersionTooLowError(minor)
    self.bash_profile = os.path.join(BASE_DIR, ".bash_profile")
    self.cwebp_path = os.path.join(BASE_DIR, options.cwebp_location)
    if not os.path.isdir(self.cwebp_path):
      raise BadDirectoryError(self.cwebp_path)
    self.cmake_path = os.path.join(BASE_DIR, options.cmake_location)
    if not os.path.isdir(self.cmake_path):
      raise BadDirectoryError(self.cmake_path)

  def mac_install_xcode(self):
    """Check for and install Xcode and Xcode command line tools.

    Raises:
      InstallInterruptError: If the user cancels either the Xcode or Xcode
          Command Line Tools setup.
    """
    try:
      subprocess.check_output("xcodebuild -version", shell=True)
      logging.info("Xcode already installed.")
    except subprocess.CalledProcessError:
      logging.warn("Please download and install Xcode from the Apple "
                   "Developers website:\nhttps://itunes.apple.com/us/app/"
                   "xcode/id497799835?ls=1&mt=12")
      if not setup_util.wait_for_installation("xcodebuild -version"):
        raise InstallInterruptError("Xcode")
      # View and accept terms and conditions for Xcode
      subprocess.call("sudo xcodebuild -license", shell=True)

    # Checks to see if xcode command line tools is installed
    try:
      subprocess.check_output("xcode-select -p", shell=True)
      logging.info("Xcode command line tools already installed.")
      return
    except subprocess.CalledProcessError:
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
      subprocess.call(info, shell=True)
    # Wait for user to complete setup
    if not setup_util.wait_for_installation("xcode-select -p"):
      raise InstallInterruptError("Xcode Command Line Tools")
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
    try:
      subprocess.check_output("cmake --version", shell=True)
      logging.info("CMake already installed.")
      return
    except subprocess.CalledProcessError:
      logging.info("CMake not installed. Downloading now.")
    url, file_hash = CMAKE_VERSIONS.get(self.os_version, (None, None))
    url = urlparse.urljoin(CMAKE_DOWNLOAD_PREFIX, url)
    location = os.path.join(BASE_DIR, "cmake.tar.gz")
    location = setup_util.download_file(url, location, "cmake", file_hash)
    if not location:
      raise FileDownloadError("https://cmake.org/download/",
                              "Please rerun this script afterwards with the "
                              "flag\n\t--cmake=/path/to/cmake")
    if not setup_util.extract_tarfile(location, "r:gz", self.cmake_path,
                                      "cmake"):
      raise ExtractionError(location)
    logging.info("cmake successfully installed.")

  def mac_install_cwebp(self):
    """Check for and install cwebp.

    Assumes that if cwebp is already installed, then the user has correctly set
    their path variable such that the command "cwebp -h" will work.

    Raises:
      FileDownloadError: If the cwebp tar fails to download, or is incorrectly
          downloaded.
      ExtractionError: If the cwebp tar cannot be properly extracted.
    """
    try:
      subprocess.check_output("cwebp -h", shell=True)
      logging.info("cwebp already installed.")
      return
    except subprocess.CalledProcessError:
      logging.info("cwebp not installed. Downloading now.")
    location = os.path.join(BASE_DIR, "cwebp.tar.gz")
    location = setup_util.download_file(CWEBP_URL, location, "cwebp",
                                        CWEBP_HASH)
    if not location:
      raise FileDownloadError("https://developers.google.com/speed/webp/docs/"
                              "precompiled", "Please rerun this script "
                              "afterwards with the flag\n"
                              "\t--cwebp=/path/to/cwebp")
    if not setup_util.extract_tarfile(location, "r:gz", self.cwebp_path,
                                      "cwebp"):
      raise ExtractionError(location)
    logging.info("cwebp successfully installed.")

  def mac_install_macports(self):
    """Check for and install MacPorts.

    Raises:
      FileDownloadError: If the MacPorts package fails to download, or is
          incorrectly downloaded.
    """
    if os.path.isfile(MACPORTS_LOCATION):
      logging.info("MacPorts already installed.")
      return
    else:
      logging.info("MacPorts not installed. Downloading now.")
    url, file_hash = MACPORTS_VERSIONS.get(self.os_version, (None, None))
    url = urlparse.urljoin(MACPORTS_DOWNLOAD_PREFIX, url)
    suffix = url.split(".")[-1]
    location = os.path.join(BASE_DIR, "macports" + suffix)
    location = setup_util.download_file(url, location, "macports", file_hash)
    if not location:
      raise FileDownloadError("https://guide.macports.org/chunked/installing."
                              "macports.html", "Please rerun this script "
                              "again afterwards.")
    logging.info("Installing Mac Ports. Sudo may prompt you for your "
                 "password.")
    subprocess.call("sudo installer -pkg " + location + " -target /",
                    shell=True)
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
    try:
      subprocess.check_output("convert --version", shell=True)
      logging.info("Image Magick already installed.")
      return
    except subprocess.CalledProcessError:
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
          logging.warn("MacPorts encountered an error installing "
                       "ImageMagick.\nPlease run this script to try again, "
                       "or attempt installation using Homebrew or "
                       "manually.")
    if (raw_input("Attempt installation with Homebrew? (y/n)")
        .lower().startswith("y")):
      try:
        # Try installing using Homebrew, however Homebrew installation has been
        # known to miss dependencies.
        subprocess.call("brew --version", shell=True)
        brew = True
      except subprocess.CalledProcessError:
        logging.warn("Homebrew is not installed.")
      if brew:
        try:
          subprocess.call("brew install imagemagick --with-librsvg", shell=True)
          logging.warn("Homebrew install of ImageMagick may miss "
                       "dependecies.")
          return
        except subprocess.CalledProcessError:
          logging.warn("Homebrew encountered an error installing "
                       "ImageMagick.\nPlease run this script to try again, "
                       "or attempt manual installataion.")
      else:
        logging.warn("ImageMagick requires either MacPorts or Homebrew to "
                     "install.\nFor more information on Homebrew, see: "
                     "http://brew.sh/\nFor more information on MacPorts, "
                     "see: https://guide.macports.org/")
    raise InstallFailedError("ImageMagick", "http://www.imagemagick.org/"
                             "script/binary-releases.php#macosx",
                             "Please rerun this script to try again.")

  def mac_update_path(self):
    """Checks PATH variable and edits the bash profile accordingly.

    Check for the appropriate path for cmake and cwebp, and edit the bash
    profile to include it. Don't check for MacPorts or ImageMagick, as those
    are managed by their own installation scripts.
    """
    optbin_update = True
    optsbin_update = True
    cwebp_path_update = True
    if find_executable("cmake"):
      optbin_update = False
    if find_executable("convert"):
      optbin_update = False
      optsbin_update = False
    if find_executable("cwebp"):
      cwebp_path_update = False
    if optbin_update or optsbin_update or cwebp_path_update:
      with open(self.bash_profile, "a") as f:
        todays_date = (str(date.today().year) + "-" + str(date.today().month)
                       + "-" + str(date.today().day))
        f.write("\n# The following block was inserted by fplutil/bin/"
                "setup_all_prereqs.py on " + todays_date + "\n")
        if optbin_update:
          f.write("export PATH=/opt/local/bin:$PATH\n")
        if optsbin_update:
          f.write("export PATH=/opt/local/sbin:$PATH\n")
        if cwebp_path_update:
          cwebp_bin = os.path.join(os.path.join(self.cwebp_path,
                                                CWEBP_VERSION), "bin")
          f.write("export PATH=" + cwebp_bin + ":$PATH\n")
        f.write("\n")
        self.bash_profile_changed = True

  def print_bash_profile_changed(self):
    """Print a warning message if the bash profile has been changed."""
    if self.bash_profile_changed:
      logging.warn("\n~/.bash_profile has been changed. Please refresh your"
                   " bash profile by running:\n\tsource ~/.bash_profile")

  def setup_all(self):
    """Performs all necessary set up."""
    # TODO(ngibson) add android setup
    self.mac_install_xcode()
    self.mac_install_cmake()
    self.mac_install_cwebp()
    if not options.no_macports:
      self.mac_install_macports()
    self.mac_install_image_magick()
    self.mac_update_path()
    self.print_bash_profile_changed()
    logging.info("Set up complete!")


def get_mac_version():
  version, _, _ = platform.mac_ver()
  return tuple(version.split("."))


class VersionUnsupportedError(Exception):
  """Raised when Mac OS is not OS X."""

  def __init__(self, version):
    Exception.__init__(self)
    self.version = version


class VersionTooHighError(Exception):
  """Raised when Mac OS is greater than the highest supported version."""

  def __init__(self, version):
    Exception.__init__(self)
    self.version = version


class VersionTooLowError(Exception):
  """Raised when Mac OS is less than the lowest supported version."""

  def __init__(self, version):
    Exception.__init__(self)
    self.version = version


class BadDirectoryError(Exception):
  """Raised when a given directory does not exist."""

  def __init__(self, directory):
    Exception.__init__(self)
    self.directory = directory


class InstallInterruptError(Exception):
  """Raised when installation of a program was interrupted by the user."""

  def __init__(self, program):
    Exception.__init__(self)
    self.program = program


class InstallFailedError(Exception):
  """Raised when installation fails for reasons other than user interrupt."""

  def __init__(self, program, link, instructions=""):
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


class ExtractionError(Exception):
  """Raised when a compressed file was unable to be extracted."""

  def __init__(self, filepath):
    Exception.__init__(self)
    self.filepath = filepath
