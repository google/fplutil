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

include $(CLEAR_VARS)
LOCAL_MODULE:=libfplutil_print
LOCAL_SRC_FILES:=\
	src/print.c \
	src/print_cxx.cc
LOCAL_C_INCLUDES:=$(LOCAL_PATH)/include
LOCAL_EXPORT_C_INCLUDES:=$(LOCAL_PATH)/include
# Cause the linker to substitute our implementations for these functions, at
# a .so-wide level.
LOCAL_EXPORT_LDFLAGS:=\
	-Wl,--wrap=perror,--wrap=fflush,--wrap=fprintf,--wrap=vprintf \
	-Wl,--wrap=printf,--wrap=putc,--wrap=fputc,--wrap=putchar,--wrap=puts \
    -Wl,--wrap=fputs,--wrap=fwrite,--wrap=write,--wrap=writev
# Need this to prevent auto-use of builtin functions.
LOCAL_EXPORT_CFLAGS:= -fno-builtin-printf -fno-builtin-fprintf \
	-fno-builtin-fflush -fno-builtin-perror -fno-builtin-vprintf \
	-fno-builtin-putc -fno-builtin-putchar -fno-builtin-fputc \
	-fno-builtin-fputs -fno-builtin-puts -fno-builtin-fwrite \
	-fno-builtin-write -fno-builtin-writev
LOCAL_EXPORT_LDLIBS:=-llog -landroid -latomic
LOCAL_CFLAGS:=-fPIC -Wall -Wextra -W
LOCAL_CXXFLAGS:=-fPIC -std=c++98 -Wall -Wextra -W
LOCAL_ARM_MODE:=arm
include $(BUILD_STATIC_LIBRARY)

include $(CLEAR_VARS)
LOCAL_MODULE:=libfplutil_main
LOCAL_SRC_FILES:=src/main.c
LOCAL_C_INCLUDES:=\
	$(LOCAL_PATH)/include \
	$(NDK_ROOT)/sources/android/native_app_glue
LOCAL_EXPORT_C_INCLUDES:=$(LOCAL_PATH)/include
LOCAL_EXPORT_LDLIBS:=-llog -landroid -latomic
LOCAL_CFLAGS:=-fPIC -std=c99 -Wall -Wextra -W
LOCAL_ARM_MODE:=arm
LOCAL_STATIC_LIBRARIES:=android_native_app_glue
include $(BUILD_STATIC_LIBRARY)

include $(CLEAR_VARS)
LOCAL_MODULE:=libfplutil
LOCAL_SRC_FILES:=\
	src/android_utils.cpp \
	src/string_utils.cpp
LOCAL_C_INCLUDES:=\
	$(LOCAL_PATH)/include
LOCAL_EXPORT_C_INCLUDES:=$(LOCAL_PATH)/include
LOCAL_EXPORT_LDLIBS:=-llog -landroid -latomic
LOCAL_CFLAGS:=-fPIC -std=c99 -Wall -Wextra -W
LOCAL_ARM_MODE:=arm
include $(BUILD_STATIC_LIBRARY)

$(call import-module,android/native_app_glue)
