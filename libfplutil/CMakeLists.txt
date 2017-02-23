# Copyright 2015 Google Inc. All rights reserved.
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
cmake_minimum_required(VERSION 2.8.12)

project(fplutil)

option(fplutil_build_tests "Build tests for this project." ON)
option(fplutil_build_library "Build library with file utils, etc.." ON)

# Output library files into `obj`.
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obj)

# Get locations of dependencies and set common build settings.
include("${CMAKE_CURRENT_LIST_DIR}/../buildutil/cmake_common.txt")
set_common_build_variables()

# Includes for this project.
include_directories(src)
include_directories(include)

# Source files for the fplutil library.
set(fplutil_SRCS
    src/file_utils.cpp
    src/string_utils.cpp)

# Library.
if(fplutil_build_library)
  add_library(fplutil ${fplutil_SRCS})
endif()

# Tests.
if(fplutil_build_tests)
  add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/unit_tests)
endif()
