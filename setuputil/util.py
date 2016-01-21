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
import hashlib
import os
import subprocess
import sys
import tarfile
import time
import urllib
import webbrowser
import zipfile


# Delay (in seconds) for polling installation completion
DELAY = 1


def get_file_hash(filepath):
  """Reads the file and returns a SHA-1 hash of the file.

  Args:
    filepath: String of the path to the file to be hashed
  Returns:
    String: The SHA-1 hash of the file.
  """
  hasher = hashlib.sha1()
  blocksize = 65536
  with open(filepath, "rb") as f:
    buf = f.read(blocksize)
    while buf:
      hasher.update(buf)
      buf = f.read(blocksize)
  return hasher.hexdigest()


def download_file(url, location, name_of_file, correct_hash):
  """Attempts to download a file from the internet to the specified location.

  If the file is not found, or the retrieval of the file failed, the
  exception will be caught and the system will exit.

  Args:
    url: A string of the URL to be retrieved.
    location: A string of the path the file will be downloaded to.
    name_of_file: A string with the name of the file, for printing purposes.
    correct_hash: A string with the expected SHA-1 hash of the file
  Returns:
    String: The location of the file, if the download is successful. Will
        return an empty string upon failure.
  """
  try:
    location, _ = urllib.urlretrieve(url, location)
    assert get_file_hash(location) == correct_hash
    print "\t" + name_of_file + " successfully downloaded."
    return location
  except IOError:
    sys.stderr.write("\t" + name_of_file + " failed to download.\n")
    return ""
  except AssertionError:
    sys.stderr.write("\tIncorrect file downloaded. Please download " +
                     name_of_file + " manually.\n")
    return ""


def extract_tarfile(tar_location, tar_flag, extract_location, name_of_file):
  """Attempts to extract a tar file (tgz).

  If the file is not found, or the extraction of the contents failed, the
  exception will be caught and the function will return False. If successful,
  the tar file will be removed.

  Args:
    tar_location: A string of the current location of the tgz file
    tar_flag: A string indicating the mode to open the tar file.
        tarfile.extractall will generate an error if a flag with permissions
        other than read is passed.
    extract_location: A string of the path the file will be extracted to.
    name_of_file: A string with the name of the file, for printing purposes.
  Returns:
    Boolean: Whether or not the tar extraction succeeded.
  """
  try:
    with tarfile.open(tar_location, tar_flag) as tar:
      tar.extractall(path=extract_location, members=tar)
    os.remove(tar_location)
    print "\t" + name_of_file + " successfully extracted."
    return True
  except tarfile.ExtractError:
    return False


def extract_zipfile(zip_location, zip_flag, extract_location, name_of_file):
  """Attempts to extract a zip file (zip).

  If the file is not found, or the extraction of the contents failed, the
  exception will be caught and the function will return False. If successful,
  the zip file will be removed.

  Args:
    zip_location: A string of the current location of the zip file
    zip_flag: A string indicating the mode to open the zip file.
        zipfile.extractall will generate an error if a flag with permissions
        other than read is passed.
    extract_location: A string of the path the file will be extracted to.
    name_of_file: A string with the name of the file, for printing purposes.
  Returns:
    Boolean: Whether or not the zip extraction succeeded.
  """
  try:
    with zipfile.ZipFile(zip_location, zip_flag) as zf:
      zf.extractall(extract_location)
    os.remove(zip_location)
    print "\t" + name_of_file + " successfully extracted."
    return True
  except zipfile.BadZipfile:
    sys.stderr.write("\t" + name_of_file + " failed to extract.\n")
    return False


def wait_for_installation(program, command=False, search=False, basedir=""):
  """Once installation has started, poll until completion.

  Once an asynchronous installation has started, wait for executable to exist.
  Poll every second, until executable is found or user presses ctrl-c.

  Args:
    program: A string representing the name of the program that is being
        installed.
    command: True if the program name needs to be run in order to test
        installation. False if it the executable can be searched for.
    search: True if the executable will not be on the path, and must be searched
        for, starting from the base directory given.
    basedir: If search is true, start from this directory when looking for the
        program. If search is false, basedir will be ignored.
  Returns:
    Boolean: Whether or not the the package finished installing
  """
  print("Waiting for installation to complete.\nAlternately, press Ctrl-C to "
        "quit, and rerun this script after installation has completed.")
  try:
    while command:
      try:
        subprocess.check_output(program, shell=True, stderr=subprocess.PIPE)
        return True
      except subprocess.CalledProcessError:
        time.sleep(DELAY)

    while search and not find_file(basedir, program):
      time.sleep(DELAY)

    while not search and not find_executable(program):
      time.sleep(DELAY)
  except KeyboardInterrupt:
    sys.stderr.write("Setup exited before completion.")
    return False
  return True


def check_dir(location, additional_location, check_file):
  """Checks to see if a file exists in a location.

  Determines whether or not an important file exists in the given directory,
  or a certain subset of that directory.

  Args:
    location: A string with the full filepath of the first directory.
    additional_location: A string with the path of an additional directory
        to try. Can be relative to the first directory or another independent
        full file path.
    check_file: A string with the path to a file relative to one of the given
        locations. Used to determine if the locations given contain the correct
        contain the correct informaion.
  Returns:
    String: The correct location the checkfile was found at, or an empty string
        if it is not.
  """
  if os.path.isdir(location):
    if os.path.isfile(os.path.join(location, check_file)):
      return location
    elif os.path.isfile(os.path.join(
        location, os.path.join(additional_location, check_file))):
      return os.path.join(location, additional_location)
  return ""


def find_file(basedir, filename):
  """Will find a file if it exists in a given base directory.

  Checks all files in the base directory and all files in all subdirectories.
  May take a while, depending on how large the base directory is.

  Args:
    basedir: A string of the base file path to be checked. Must be the full
        file path, not relative to home.
    filename: A string of the file to be checked for. Must include the file
        type extension.
  Returns:
    String: The location of the file, if found, else and empty string.
  """
  if not basedir or not filename:
    return ""
  for dirpath, subdirs, files in os.walk(basedir):
    for f in files:
      if f == filename:
        return os.path.join(dirpath, filename)
  return ""


def open_link(url, name_of_link):
  """Open the given URL in the user's default webbrowser."""
  try:
    # If possible, open in a new tab, and raise the window to the front
    webbrowser.open(url, new=2, autoraise=True)
    return True
  except webbrowser.Error:
    sys.stderr.write("\t" + name_of_link + " failed to open.\n")
    return False


def get_file_type(filepath):
  """Returns the extension of a given filepath or url."""
  return filepath.split(".")[-1]


def get_file_name(filepath, extension=True):
  """Returns the name of the file of a given filepath or url.

  Args:
    filepath: String of full file path
    extension: Boolean determining whether or not the file type will be returned
        as part of the file name
  Returns:
    String: The filename
  """
  name = filepath.split("/")[-1]
  if extension:
    return name
  else:
    return name.split(".")[0]
