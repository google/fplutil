# Copyright (c) 2014 Google, Inc.
#
# This software is provided 'as-is', without any express or implied
# warranty.  In no event will the authors be held liable for any damages
# arising from the use of this software.
# Permission is granted to anyone to use this software for any purpose,
# including commercial applications, and to alter it and redistribute it
# freely, subject to the following restrictions:
# 1. The origin of this software must not be misrepresented; you must not
# claim that you wrote the original software. If you use this software
# in a product, an acknowledgment in the product documentation would be
# appreciated but is not required.
# 2. Altered source versions must be plainly marked as such, and must not be
# misrepresented as being the original software.
# 3. This notice may not be removed or altered from any source distribution.
LOCAL_PATH:=$(call my-dir)/..

include $(CLEAR_VARS)
LOCAL_MODULE:=libandroid_util
LOCAL_SRC_FILES:=\
	$(LOCAL_PATH)/src/AndroidLogPrint.c \
	$(LOCAL_PATH)/src/AndroidMainWrapper.c
LOCAL_C_INCLUDES:=\
	$(LOCAL_PATH)/include \
	$(NDK_ROOT)/sources/android/native_app_glue
LOCAL_EXPORT_C_INCLUDES:=$(LOCAL_PATH)/include
LOCAL_CFLAGS:=-fPIC -std=c99 -Wall -Wextra -W -pedantic -Wno-unused-parameter
LOCAL_ARM_MODE:=arm
LOCAL_STATIC_LIBRARIES:=android_native_app_glue
include $(BUILD_STATIC_LIBRARY)

$(call import-module, native_app_glue)
