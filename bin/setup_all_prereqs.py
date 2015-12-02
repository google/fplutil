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

import sys

import platforms.linux

"""Installs all necessary requirements for building.

   Determines user's OS and downloads and installs prerequisitexs accoringly.
"""


def say_hello():
  print("Welcome to the fplutil setup script!\n"
        "This script will install any necessary prerequisites so you can build "
        "Android and Desktop applications using FPL's suite of tools\n"
        "For more information, including instructions for manual setup, "
        "visit:\nhttp://google.github.io/fplutil/fplutil_prerequisites.html")
  answer = raw_input("Press enter to continue, or q to quit: ")
  if answer.lower().startswith("q"):
    sys.exit()


def main():
  say_hello()
  if sys.platform.startswith("linux"):
    # linux or linux2
    setup = platforms.linux.LinuxSetup()
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
