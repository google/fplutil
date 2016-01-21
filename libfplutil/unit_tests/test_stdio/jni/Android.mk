# Copyright 2014 Google Inc. All rights reserved.
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

LOCAL_PATH:=$(call my-dir)/..

PROJECT_ROOT:=$(LOCAL_PATH)/../../..

# --- project ---
include $(CLEAR_VARS)
LOCAL_MODULE:=test_stdio
LOCAL_SRC_FILES:=$(wildcard $(LOCAL_PATH)/test_*.cc)
LOCAL_WHOLE_STATIC_LIBRARIES:=android_native_app_glue libfplutil_main \
  libfplutil_print libgtest
LOCAL_LDLIBS:=-llog -landroid
LOCAL_ARM_MODE:=arm
include $(BUILD_SHARED_LIBRARY)

$(call import-add-path,$(abspath $(PROJECT_ROOT)))

$(call import-module,android/native_app_glue)
$(call import-module,libfplutil/jni)
$(call import-module,libfplutil/jni/libs/googletest)
