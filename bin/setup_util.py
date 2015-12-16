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
from os import remove
from select import select
import subprocess
import sys
import tarfile
import urllib


def remove_line(filename, to_remove, all_lines=""):
  """Removes any instances of a line from a file.

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
  exception will be caught and the system will exit.

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
    tar = tarfile.open(tar_location, tar_flag)
    tar.extractall(path=extract_location, members=tar)
    remove(tar_location)
    return True
  except tarfile.ExtractError:
    return False


def wait_for_installation(program):
  """Once installation has started, poll until completion.

  Once an asynchronous installation has started, wait for executable to exist.
  Poll every second, until executable is found or user presses ctrl-c.

  Args:
    program: A string representing the name of the program that is being
        installed.
  Returns:
    Boolean: Whether or not the the package finished installing
  """
  print("Waiting for installation to complete.\nAlternately, press Ctrl-c to "
        "quit, and rerun this script after installation has completed.")
  try:
    while not find_executable(program):
      time.sleep(1)
  except KeyboardInterrupt:
    return False
  return True