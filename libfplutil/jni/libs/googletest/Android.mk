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
DEPENDENCIES_ROOT := $(wildcard $(PROJECT_ROOT)/dependencies)

# If the dependency library exists, asssume this is the root directory for
# dependencies for this project.
ifneq ($(DEPENDENCIES_ROOT),)
  GOOGLETEST_PATH ?= $(abspath $(DEPENDENCIES_ROOT)/googletest)
else
  GOOGLETEST_PATH ?= $(abspath $(PROJECT_ROOT)/../../../../external/googletest)
endif

libgtest_target_includes := $(GOOGLETEST_PATH)/googletest \
    $(GOOGLETEST_PATH)/googletest/include \
    $(GOOGLETEST_PATH)/googlemock \
    $(GOOGLETEST_PATH)/googlemock/include

include $(CLEAR_VARS)
ifeq ($(TARGET_ARCH), arm)
  LOCAL_SDK_VERSION := 8
else
# NDK support of other archs (ie. x86 and mips) are only available after android-9
  LOCAL_SDK_VERSION := 9
endif

LOCAL_NDK_STL_VARIANT := stlport_static
LOCAL_CPP_EXTENSION := .cc
LOCAL_C_INCLUDES := $(libgtest_target_includes)
LOCAL_SRC_FILES := \
  $(GOOGLETEST_PATH)/googletest/src/gtest-all.cc \
  $(GOOGLETEST_PATH)/googlemock/src/gmock-all.cc
LOCAL_EXPORT_C_INCLUDES := \
  $(GOOGLETEST_PATH)/googletest/include \
  $(GOOGLETEST_PATH)/googlemock/include
LOCAL_EXPORT_LDLIBS:= -llog
LOCAL_MODULE := libgtest
include $(BUILD_STATIC_LIBRARY)
