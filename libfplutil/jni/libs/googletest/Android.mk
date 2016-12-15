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


LOCAL_PATH := $(call my-dir)/..

PROJECT_ROOT := $(LOCAL_PATH)/../../..
include $(PROJECT_ROOT)/buildutil/android_common.mk

# NDK support of other archs (ie. x86 and mips) are only available after
# android-9
libgtest_sdk_version:=$(if $(subst,arm,,$(TARGET_ARCH)),9,8)

GTEST_INCLUDE_DIRS := \
  $(DEPENDENCIES_GTEST_DIR)/include \
  $(DEPENDENCIES_GTEST_DIR)/../..

GMOCK_INCLUDE_DIRS := \
  $(DEPENDENCIES_GMOCK_DIR)/include \
  $(DEPENDENCIES_GMOCK_DIR)/../..

include $(CLEAR_VARS)
LOCAL_MODULE := libgtest
LOCAL_EXPORT_LDLIBS := -llog -latomic
LOCAL_SRC_FILES := $(DEPENDENCIES_GTEST_DIR)/src/gtest-all.cc
LOCAL_CPP_EXTENSION := .cc
LOCAL_CFLAGS := $(FPL_CFLAGS)
LOCAL_C_INCLUDES := \
  $(DEPENDENCIES_GTEST_DIR) \
  $(GTEST_INCLUDE_DIRS)
LOCAL_EXPORT_C_INCLUDES := $(GTEST_INCLUDE_DIRS)
LOCAL_SDK_VERSION := $(libgtest_sdk_version)
include $(BUILD_STATIC_LIBRARY)

include $(CLEAR_VARS)
LOCAL_MODULE := libgmock
LOCAL_EXPORT_LDLIBS := -llog -latomic
LOCAL_SRC_FILES := $(DEPENDENCIES_GMOCK_DIR)/src/gmock-all.cc
LOCAL_CPP_EXTENSION := .cc
LOCAL_CFLAGS := $(FPL_CFLAGS)
LOCAL_C_INCLUDES := \
  $(DEPENDENCIES_GMOCK_DIR) \
  $(GMOCK_INCLUDE_DIRS) \
  $(GTEST_INCLUDE_DIRS)
LOCAL_EXPORT_C_INCLUDES := \
  $(GMOCK_INCLUDE_DIRS) \
  $(GTEST_INCLUDE_DIRS)
LOCAL_SDK_VERSION := $(libgtest_sdk_version)
include $(BUILD_STATIC_LIBRARY)
