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
import platform
import subprocess
import sys

import common
import util

""" Contains all necessary methods for setting up the Windows environment """

# Program Files directories. The default place for installation through an exe,
# hence the first place to search for completed installation.
PROGRAM_FILES = os.environ.get("ProgramFiles")
PROGRAM_FILES_X86 = os.environ.get("ProgramFiles(x86)")


# VISUAL STUDIO
# Download link and hash for Visual Studio 2013 Community edition, which will
# be downloaded if the user does not have any version of VS installed.
VS_DEFAULT_NAME = "Microsoft Visual Studio Community 2013"
VS_DEFAULT_VERSION = "Microsoft Visual Studio 12.0"
VS_DEFAULT_URL = "https://go.microsoft.com/fwlink/?LinkId=532495&clcid=0x409"
VS_DEFAULT_HASH = "748764ba84ce2ecf29f3ee1475c8cf0da664b351"

# Versions of Visual Studio and Visual C++ that are accepted for using fplutil
VS_NAME_PREFIX = "Microsoft Visual Studio "
VS_COMPILER_PREFIX = "Microsoft Visual C++ "
VS_COMPATIBLE_TYPES = [
    "Community",
    "Professional"
]
# Product year: Version name
VS_COMPATIBLE_VERSIONS = {
    "2010": "10.0",
    "2012": "11.0",
    "2013": "12.0",
    "2015": "14.0"
}

VS_COMPILER_BASE_URL = ("https://www.microsoft.com/en-us/download/"
                        "details.aspx?id=")
VS_COMPILER_DOWNLOADS = {
    "10.0": "23691",
    "11.0": "30679",
    "12.0": "40784",
    "14.0": "40784"
}

# CMAKE
# Default directory name, latest version name, and download link and
# corresponding SHA-1 hash, and minimum version:
CMAKE_DIR = "CMake"
CMAKE_VERSION = "cmake-3.4.1-win32-x86"
CMAKE_URL = "https://cmake.org/files/v3.4/" + CMAKE_VERSION + ".zip"
CMAKE_HASH = "4894baeafc0368d6530bf2c6bfe4fc94056bd04a"
CMAKE_MIN_VERSION = 3, 4, 1

# CWEBP
# Default directory name, base download link, and OS version dependent url
# suffix with corresponding SHA-1 hash in the format:
# OS version: (download link ending, hash)
# and minimum version
CWEBP_DIR = "cwebp"
CWEBP_BASE_URL = "http://downloads.webmproject.org/releases/webp/"
CWEBP_VERSIONS = {
    common.WINDOWS_32: ("libwebp-0.4.4-windows-x86",
                        "88f44c6434535ef9a0470d7a5352ba5a883a6342"),
    common.WINDOWS_64: ("libwebp-0.4.4-windows-x64",
                        "59cd4347029d9acbb6eda7efb6d15fe74d1232a2")
}
CWEBP_MIN_VERSION = 0, 4, 0

# IMAGEMAGICK
# Base download link, and OS version dependent url suffix with corresponding
# SHA-1 hash in the format:
# OS version: (download link ending, hash)
IMAGEMAGICK_BASE_URL = "http://www.imagemagick.org/download/binaries/"
IMAGEMAGICK_VERSIONS = {
    common.WINDOWS_32: ("ImageMagick-6.9.2-10-Q16-x86-dll.exe",
                        "3a6d9d6e0989771e472b084bfd1cb15b5aeed720"),
    common.WINDOWS_64: ("ImageMagick-6.9.2-10-Q16-x64-dll.exe",
                        "19f05721960ff0b28602cc4317f3942d0e2bf705")
}

# JAVA
# Base download link, and OS version dependent url suffix with corresponding
# SHA-1 hash in the format:
# OS version: (download link ending, hash)
JAVA_URL = ("http://www.oracle.com/technetwork/java/javase/downloads/"
            "jdk8-downloads-2133151.html")
JAVA_VERSIONS = {
    common.WINDOWS_32: "Windows x86 jdk-8u65-windows-i586.exe",
    common.WINDOWS_64: "Windows x64 jdk-8u65-windows-x64.exe"
}

# PYTHON
# Base download link, and OS version dependent url suffix with corresponding
# SHA-1 hash in the format:
# OS version: (download link ending, hash)
# and minimum version
PYTHON_BASE_URL = "https://www.python.org/ftp/python/"
PYTHON_VERSIONS = {
    common.WINDOWS_32: ("2.7.8/python-2.7.8.msi",
                        "a945690f9837e1a954afaabb8552b79a7abfd53d5"),
    common.WINDOWS_64: ("2.7.8/python-2.7.8.amd64.msi",
                        "a19375bc3d7ca7d3c022f2d4a42fdf2c54f79d1d")
}
PYTHON_MIN_VERSION = 2, 7, 8

# DIRECTX
# Download link and hash for DirectX June 2010 edition
DIRECTX_URL = ("https://download.microsoft.com/download/A/E/7/AE743F1F-632B"
               "-4809-87A9-AA1BB3458E31/DXSDK_Jun10.exe")
DIRECTX_HASH = "8fe98c00fde0f524760bb9021f438bd7d9304a69"


class WindowsSetup(common.Setup):
  """Contains all necessary methods for setting up Windows.

  Attributes:
    programs: A string of all the programs that are currently installed. Used
        for determining if Visual Studio has been installed or not.
    path_update: A string of the update to the Windows path that needs to be
        appended.
    vs_version: The version of Visual Studio either has installed, or is to be
        installed.
    version: Whether the system is 32bit or 64bit.
    program_files: The default place of installation from exe installers. Used
        for searching to check when programs are installed.
    java_path: A string of the path to the location of the java directory. Used
        for path setting if java.exe cannot be located in any of the default
        locations.
    python_path: A string of the path to the location of the python directory.
        Used for path setting if python.exe cannot be located in any of the
        default locations.
    install_vs: Whether or not Visual Studio should be checked for or installed.
    fix_directx: Whether or not to try and fix problems DirectX might be having
        with Visual Studio
    fix_path: Windows path seems easily corruptable. If set, only call
        update_path and don't reinstall anything.

  Raises:
    VersionUnsupportedError: If the system version is neither 32bit or 64bit
    VersionTooLowError: If the OS is older than Windows 7
    BadDirectoryError: If the given cwebp or cmake path does not exist.
  """

  def __init__(self, options):
    common.Setup.__init__(self, options)
    self.programs = ""
    self.path_update = ""
    self.vs_version = VS_DEFAULT_VERSION
    version = platform.architecture()[0]
    if version == "32bit":
      self.version = common.WINDOWS_32
      self.program_files = PROGRAM_FILES
    elif version == "64bit":
      self.version = common.WINDOWS_64
      self.program_files = PROGRAM_FILES_X86
    else:
      raise common.VersionUnsupportedError("Not 32 or 64 bit Windows")
    major, minor = get_windows_os_number()
    if major < 6 or (major == 6 and minor < 1):  # Windows Vista and below
      raise common.VersionTooLowError(platform.release())
    self.java_path = options.java_location
    self.python_path = options.python_location
    self.install_vs = not options.no_visual_studio
    self.fix_directx = options.fix_directx
    self.fix_path = options.fix_path

  def check_programs(self):
    """Get a list of all programs currently installed.

    Raises:
      PermissionDeniedError: If wmic fails for any reason.
    """
    logging.info("Checking what needs to be installed..")
    try:
      self.programs = subprocess.check_output("wmic product get name",
                                              shell=True)
    except subprocess.CalledProcessError:
      raise common.PermissionDeniedError("wmic", "Try closing cmd.exe and "
                                         "reopening as Administrator. (Right "
                                         "click, select 'Run as "
                                         "Administrator')")

  def windows_setup_visual_studio(self):
    """Check for compatible versions of Visual Studio and Visual C++.

    If no compatible version of Visual Studio is detected, download default
    version. If a compatible version is detected, check if a compatible
    version of the C++ compiler has been installed.

    Raises:
      FileDownloadError: If the Visual Studio installer fails to download, or
          is downloaded incorrectly.
    """
    for line in self.programs.splitlines():
      if VS_NAME_PREFIX in line:
        for name in get_all_vs():
          if line.strip() == name:
            self.vs_version = VS_COMPATIBLE_VERSIONS.get(name.split(" ")[-1])
            logging.info("Visual Studio already installed.")
            self.windows_check_compiler()
            return
    logging.info("Visual Studio not installed. Installing " + VS_DEFAULT_NAME +
                 " now...")
    location = os.path.join(common.BASE_DIR, "vs_community.exe")
    location = util.download_file(VS_DEFAULT_URL, location,
                                  "Visual Studio Installer", VS_DEFAULT_HASH)
    if not location:
      raise common.FileDownloadError("https://www.visualstudio.com/en-us/"
                                     "downloads/download-visual-studio-vs.aspx",
                                     "Please rerun this script after "
                                     "completing manual installation.")
    logging.info("Now lauching Visual Stusio Installer.\n*** Please ensure you "
                 "select \"Visual C++\" ***\nYour computer will "
                 "likely need to be restarted. If so, click 'Restart Now' when "
                 "prompted and rerun this script after reboot.\nIf no restart "
                 "is required, click 'Finish' and rerun script.")
    subprocess.call("cmd /k " + location, shell=True)
    # cmd /k will stop the script, but just in case, exit
    sys.exit()

  def windows_check_compiler(self):
    """check for compatible version of Visual C++.

    If no compatible version is found, download the same one was the version
    of Visual Studio currently installed.

    Raises:
      InstallFailedError: If the user does not want to install Visual C++.
      WebbrowserFailedError: If the link to Visual C++ could not be opened in
          the user's default browser.
      InstallInterruptError: If the user cancels the wait for installation of
          Visual C++.
    """
    for line in self.programs.splitlines():
      if VS_COMPILER_PREFIX in line:
        for name in VS_COMPATIBLE_VERSIONS.iterkeys():
          if line.startswith(VS_COMPILER_PREFIX + name):
            logging.info("Visual C++ already installed.")
            return
    logging.warn("Could not find Visual C++ compiler.\nPlease open Visual "
                 "Studio installer now and repair installation, or continue "
                 "and download Visual C++.")
    if not raw_input("Continue? (y/n) ").lower().startswith("y"):
      raise common.InstallFailedError("Visual C++", "https://www.microsoft.com/"
                                      "en-us/download/details.aspx?id=48145",
                                      "If you would like to skip Visual Studio "
                                      "installation, please rerun this script "
                                      "with the flag\n\t--no_visual_studio")
    if self.version == common.WINDOWS_32:
      filename = "vcredist_x86.exe"
    else:
      filename = "vcredist_x64.exe"
    logging.info("Opening web browser. Please download\n\t" + filename + "\n"
                 "Once download is complete, double click the exe and follow "
                 "installation instructions.")
    url = VS_COMPILER_BASE_URL + VS_COMPILER_DOWNLOADS.get(self.vs_version)
    if not util.open_link(url, "Visual C++"):
      raise common.WebbrowserFailedError("Visual C++", url)
    if not util.wait_for_installation("cl.exe", search=True,
                                      basedir=self.program_files):
      raise common.InstallInterruptError("Visual C++", "If you would like to "
                                         "skip Visual Studio installation, "
                                         "please rerun this script with the "
                                         "flag\n\t--no_visual_studio")
    logging.info("Visual C++ installed.")

  def windows_fix_directx(self):
    """Attempt to fix problems DirectX may be having with Visual Studio.

    DirectX comes pre-installed on Windows 7 and up, but having Visual C++ 2010
    or higher may give an "S1023" error due to it being newer than the latest
    version of DirectX, June 2010 DirectX SDK. This can be fixed by
    reinstalling DirectX once Visual C++ has been established.

    Raises:
      FileDownloadError: If the Visual Studio installer fails to download, or
          is downloaded incorrectly.
    """
    logging.info("Attempting to fix problems with DirectX...")
    try:
      subprocess.call("MsiExec.exe /passive /X{F0C3E5D1-1ADE-321E-8167-"
                      "68EF0DE699A5}", shell=True)
      subprocess.call("MsiExec.exe /passive /X{1D8E6291-B0D5-35EC-8441-"
                      "6616F567A0F7}", shell=True)
    except subprocess.CalledProcessError:
      logging.warning("MsiExec.exe failed. Could not resolve conflicts with "
                      "DirectX and Visual Studio.")
      return
    location = os.path.join(common.BASE_DIR, "directx.exe")
    location = util.download_file(DIRECTX_URL, location, "DirectX",
                                  DIRECTX_HASH)
    if not location:
      raise common.FileDownloadError("http://www.microsoft.com/en-us/download/"
                                     "details.aspx?id=6812", "Please rerun "
                                     "this script after completing manual "
                                     "installation.")
    subprocess.call("start cmd /c " + location, shell=True)
    logging.info("DirectX successfully reinstalled.")

  def windows_install_cmake(self):
    """Check for and install cmake.

    Raises:
      FileDownloadError: If the CMake zip fails to download, or is downloaded
          incorrectly.
    """
    if find_executable("cmake"):
      if check_cmake_version():
        logging.info("CMake already installed.")
        return
      else:
        logging.info("CMake version not sufficient. Updating now.")
    else:
      location = util.check_dir(self.cmake_path, CMAKE_VERSION,
                                os.path.join("bin", "cmake.exe"))
      if location:
        logging.info("CMake already installed.")
        self.cmake_path = location
        return
      else:
        logging.info("CMake not installed. Downloading now...")
    location = os.path.join(common.BASE_DIR, "cmake.zip")
    location = util.download_file(CMAKE_URL, location, "cmake", CMAKE_HASH)
    if not location:
      raise common.FileDownloadError("https://cmake.org/download/", "Please "
                                     "rerun this script afterwards with the "
                                     "flag\n\t--cmake=\\path\\to\\cmake")
    util.extract_zipfile(location, "r", self.cmake_path, "cmake")
    logging.info("cmake successfully installed.")

  def windows_install_cwebp(self):
    """Check for and install cwebp in given directory.

    Raises:
      FileDownloadError: If the cwebp zip fails to download, or is downloaded
          incorrectly.
    """
    if find_executable("cwebp"):
      if check_cwebp_version():
        logging.info("cwebp already installed.")
        return
      else:
        logging.info("cwebp version not sufficient. Updating now.")
    else:
      location = util.check_dir(self.cwebp_path,
                                CWEBP_VERSIONS.get(self.version)[0],
                                "\\bin\\cmake.exe")
      if location:
        logging.info("CMake already installed.")
        self.cmake_path = location
        return
    version, file_hash = CWEBP_VERSIONS.get(self.version)
    logging.info("cwebp not installed. Downloading now...")
    url = CWEBP_BASE_URL + version + ".zip"
    location = os.path.join(common.BASE_DIR, "cwebp.zip")
    location = util.download_file(url, location, "cwebp", file_hash)
    if not location:
      raise common.FileDownloadError("https://developers.google.com/speed/webp/"
                                     "docs/precompiled", "Please rerun this "
                                     "script afterwards with the flag\n\t"
                                     "--cmake=\\path\\to\\cmake")
    util.extract_zipfile(location, "r", self.cwebp_path, "cwebp")
    logging.info("cwebp successfully installed.")

  def windows_install_imagemagick(self):
    """Check for and install ImageMagick.

    Raises:
      FileDownloadError: If the ImageMagick installer fails to download, or is
          downloaded incorrectly.
      InstallInterruptError: If the user cancels the wait for installation of
          ImageMagick.
    """
    if find_executable("convert"):
      logging.info("ImageMagick is already installed.")
      return
    logging.info("ImageMagick not installed. Downloading now...")
    url, file_hash = IMAGEMAGICK_VERSIONS.get(self.version)
    url = IMAGEMAGICK_BASE_URL + url
    location = os.path.join(common.BASE_DIR, "imagemagick.exe")
    location = util.download_file(url, location, "imagemagick", file_hash)
    if not location:
      raise common.FileDownloadError("http://www.imagemagick.org/script/binary-"
                                     "releases.php", "Please rerun this script "
                                     "after completing manual installation.\n")
    subprocess.call("start cmd /c " + location, shell=True)
    if not util.wait_for_installation("convert"):
      raise common.InstallInterruptError("ImageMagick")
    logging.info("ImageMagick successfully installed.")

  def windows_install_java(self):
    """Check for and install Java.

    Downloading the jdk installer can't be done through python, or equivalent
    bash commands due to some javascript on the download site. It instead has
    to be through the users default browser.

    Raises:
      WebbrowserFailedError: If the link to Java JDK could not be opened in
          the user's default browser.
      InstallInterruptError: If the user cancels the wait for installation of
          Java JDK.
    """
    if find_executable("java"):
      logging.info("Java already installed.")
      return
    # Since installing Java is annoying, we want to make doubly sure the user
    # doesn't have it already.
    location = util.find_file(PROGRAM_FILES, "java.exe")
    if not location and self.program_files == PROGRAM_FILES_X86:
      # In case the user has installed the 32 bit version on a 64 bit machine
      location = util.find_file(PROGRAM_FILES_X86, "java.exe")
    if location:
      logging.info("Java already installed at " + location + ".")
      self.java_path = os.path.dirname(location)
      return
    logging.warn("Java not installed. Please accept the terms and conditions, "
                 "and download:\n\t" + JAVA_VERSIONS.get(self.version) +
                 "\nOnce download is complete, double click the exe and follow "
                 "installation instructions.")
    # Java JDK can't be installed without the user accepting the terms and
    # conditions, which can only be done in their browser
    logging.warn("Java not installed. Opening browser...")
    if not util.open_link(JAVA_URL, "Java JDK"):
      raise common.WebbrowserFailedError("Java JDK", JAVA_URL)
    if not util.wait_for_installation("java.exe", search=True,
                                      basedir=PROGRAM_FILES):
      raise common.InstallInterruptError("Java JDK")
    logging.info("Java successfully installed.")

  def windows_install_python(self):
    """Checks for and installs at least Python 2.7.8.

    Raises:
      FileDownloadError: If the Python installer fails to download, or is
          downloaded incorrectly.
      InstallInterruptError: If the user cancels the wait for installation of
          ImageMagick.
      InstallFailedError: If msiexec fails, or Python cannot be installed.
    """
    if find_executable("python"):
      if check_python_version():
        logging.info("Python already installed.")
        return
      else:
        logging.info("Python version not sufficient. Updating now.")
    else:
      logging.info("Python not installed. Downloading now.")
    url, file_hash = PYTHON_VERSIONS.get(self.version)
    url = PYTHON_BASE_URL + url
    location = os.path.join(common.BASE_DIR, "python.msi")
    location = util.download_file(url, location, "python", file_hash)
    if not location:
      raise common.FileDownloadError("https://www.python.org/downloads/release/"
                                     "python-278/", "Please rerun this script "
                                     "after completing manual installation.\n")
    logging.info("Opening Python installer. For convenience, please select the "
                 "'Add python.exe to Path' option.")
    try:
      subprocess.call("msiexec /i " + location, shell=True)
    except subprocess.CalledProcessError:
      raise common.InstallFailedError("Python", "https://www.python.org/"
                                      "downloads/release/python-278/", "Please "
                                      "rerun this script after installating "
                                      "Python manually.")

  def update_path(self):
    """Checks PATH variable and edits it accordingly.

    Update or repair Windows PATH. If called after setup, path will be updated.
    If called by the flag --fix_path, path will be repaired.
    """
    update = ""
    # Installed by this script
    if not find_executable("cwebp"):
      cwebp_ver, _ = CWEBP_VERSIONS.get(self.version)
      update = (os.path.join(self.cwebp_path, cwebp_ver, "bin") + os.pathsep
                + update)
    if not find_executable("cl"):
      update = (os.path.join(self.program_files, self.vs_version, "VC", "bin")
                + os.pathsep + update)

    # Installed by exe installers
    if not find_executable("cmake"):
      location = util.check_dir(self.cmake_path,
                                os.path.join(CMAKE_VERSION, "bin"), "cmake.exe")
      if not location:
        location = util.find_file(self.program_files, "cmake.exe")
        if location:
          location = os.path.dirname(location)
      if location:
        update = location + os.pathsep + update
      else:
        logging.warn("Unable to set path for CMake. Please rerun this script "
                     "with additional flag:\n\t--cmake=\\path\\to\\cmake")
    if not find_executable("java"):
      location = util.check_dir(self.java_path, "bin", "java.exe")
      if not location:
        location = util.find_file(os.path.dirname(self.program_files),
                                  "java.exe")
        if location:
          location = os.path.dirname(location)
      if location:
        update = location + os.pathsep + update
      else:
        logging.warn("Unable to set path for Java. Please rerun this script "
                     "with the additional flag:\n\t--java=\\path\\to\\java")
    if not find_executable("python"):
      location = util.check_dir(self.python_path, "files", "python.exe")
      if not location:
        location = util.find_file(os.path.dirname(self.program_files),
                                  "python.exe")
        if location:
          location = os.path.dirname(location)
      if location:
        update = location + os.pathsep + update
      else:
        logging.warn("Unable to set path for Python. Please rerun this script "
                     "with the additional flag:\n\t--python=\\path\\to\\python")
    self.path_update = update
    self.bash_profile_changed = True

  def get_windows_path_update(self):
    """Returns all the paths that needs to be appended to the Windows PATH."""
    return self.path_update

  def setup_all(self):
    """Perform all necessary setup."""
    if self.fix_path:
      self.update_path()
      return
    if self.install_vs:
      self.check_programs()
      self.windows_setup_visual_studio()
    if self.fix_directx:
      self.windows_fix_directx()
    self.windows_install_cmake()
    self.windows_install_cwebp()
    self.windows_install_imagemagick()
    self.windows_install_java()
    self.windows_install_python()
    self.update_path()
    logging.info("Windows setup complete.")


def update_windows_path(path):
  """Performs the bash command to update the path. Must be done last."""
  subprocess.call("setx PATH \"" + path)


def get_windows_os_number():
  """Gets an integer of the Windows OS number."""
  build = platform.version().split(".")
  return int(build[0]), int(build[1])


def check_cmake_version():
  """Gets current version of CMake and checks if it's high enough.

  Returns:
    Boolean: True if the version is high enough, False if it is not.
  """
  output = subprocess.check_output("cmake --version")
  version = output.splitlines()[0].split(" ")[-1]
  major, minor, build = tuple(int(x) for x in version.split("."))
  if ((major > CMAKE_MIN_VERSION[0]) or
      (major == CMAKE_MIN_VERSION[0] and minor > CMAKE_MIN_VERSION[1]) or
      (major == CMAKE_MIN_VERSION[0] and minor == CMAKE_MIN_VERSION[1] and
       build >= CMAKE_MIN_VERSION[2])):
    return True
  else:
    return False


def check_cwebp_version():
  """Gets current version of cwebp and checks if it's high enough.

  Returns:
    Boolean: True if the version is high enough, False if it is not.
  """
  output = subprocess.check_output("cwebp -version")
  version = output.strip()
  major, minor, build = tuple(int(x) for x in version.split("."))
  if ((major > CWEBP_MIN_VERSION[0]) or
      (major == CWEBP_MIN_VERSION[0] and minor > CWEBP_MIN_VERSION[1]) or
      (major == CWEBP_MIN_VERSION[0] and minor == CWEBP_MIN_VERSION[1] and
       build >= CWEBP_MIN_VERSION[2])):
    return True
  else:
    return False


def check_python_version():
  """Gets current version of Python and checks if it's high enough.

  Python version must be obtained through the command line, rather than
  Python's internal version check.

  Returns:
    Boolean: True if the version is high enough, False if it is not.
  """
  version = subprocess.Popen("python -V", stderr=subprocess.PIPE)
  version = version.stderr.read().strip().split(" ")[1]
  major, minor, build = tuple(int(x) for x in version.split("."))
  if ((major > PYTHON_MIN_VERSION[0]) or
      (major == PYTHON_MIN_VERSION[0] and minor > PYTHON_MIN_VERSION[1]) or
      (major == PYTHON_MIN_VERSION[0] and minor == PYTHON_MIN_VERSION[1] and
       build >= PYTHON_MIN_VERSION[2])):
    return True
  else:
    return False


def get_all_vs():
  """Creates a list of all the compatible versions of Visual Studio."""
  all_vs = []
  for vs_type in VS_COMPATIBLE_TYPES:
    for year_num in VS_COMPATIBLE_VERSIONS.iterkeys():
      all_vs.append(VS_NAME_PREFIX + vs_type + " " + year_num)
  return all_vs
