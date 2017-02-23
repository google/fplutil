# Copyright 2016 Google Inc. All rights reserved.
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

project(fbx_common)

# Include common setup for FBX projects.
include("cmake_fbx.txt")

# Output library files into `obj`.
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obj)

# Set compile options for FBX programs.
fbx_compile_options()

# Source files for the library.
set(fbx_common_SRCS
    include/fbx_common/fbx_common.h
    src/fbx_common.cpp)

# Create the executable for mesh_pipeline.
add_library(fbx_common ${fbx_common_SRCS})

# Add common link libraries and include directories.
fbx_configure_target(fbx_common)
