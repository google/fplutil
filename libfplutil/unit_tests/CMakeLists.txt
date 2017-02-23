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

option(
  gtest_force_shared_crt
  "Use shared (DLL) run-time lib even when Google Test is built as static lib."
  ON)

# Import gtest if it's not already present.
if(NOT TARGET gtest)
  set_compiler_flags_for_external_libraries()
  add_subdirectory(${dependencies_gtest_dir} googletest)
  restore_compiler_flags()
endif()

# Set some variables describing file locations.
set(GUNIT_INCDIR "${dependencies_gtest_dir}/include")
if(EXISTS "${dependencies_gtest_dir}/../../third_party")
  set(GUNIT_HACK_INCDIR "${dependencies_gtest_dir}/../..")
endif()
set(GTEST_LIBDIR "${dependencies_gtest_dir}")

# Include helper functions and macros used by Google Test.
include(${GTEST_LIBDIR}/cmake/internal_utils.cmake)
config_compiler_and_linker()
string(REPLACE "-W4" "-W3" cxx_default "${cxx_default}")
string(REPLACE "-Wshadow" "" cxx_default "${cxx_default}")
string(REPLACE "-Wextra" "" cxx_default "${cxx_default}")

# This is the directory into which the executables are built.
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}")

include_directories(${GUNIT_INCDIR}
                    ${GUNIT_HACK_INCDIR}
                    ${CMAKE_CURRENT_SOURCE_DIR})

# Common libraries for tests.
if(NOT MSVC)
  find_package(Threads)
endif()

set(COMMON_LIBS "gtest;${CMAKE_THREAD_LIBS_INIT}")

# Extra .cpp files to compile for tests
set(SUPPORT_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/../src/string_utils.cpp")

# PUT ADDITIONAL UNIT TEST BINARIES BELOW!
# The commands should be of the form:
#
# test_executable(<test-name>)
#
# Where <test-name> is the name of the output test executable and the
# basename of the source file for the test.  For example,
# test_executable(CallbackTests) generates an executable called CallbackTests
# which is the result of compiling test_CallbackTests.cc along with any files
# specified by the SUPPORT_SRCS variable.

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/bin)
function(test_executable name)
  cxx_executable_with_flags(test_${name} "${cxx_default}" "${COMMON_LIBS}"
      ${CMAKE_CURRENT_SOURCE_DIR}/test_${name}/test_${name}.cc ${SUPPORT_SRCS}
      ${ARGN})
endfunction()

test_executable(index_allocator)
test_executable(intrusive_list)
test_executable(string)
test_executable(variable_size)
