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
LOCAL_MODULE:=libfplutil_print
LOCAL_SRC_FILES:=\
	$(LOCAL_PATH)/src/print.c \
	$(LOCAL_PATH)/src/print_cxx.cc
LOCAL_C_INCLUDES:=$(LOCAL_PATH)/include
LOCAL_EXPORT_C_INCLUDES:=$(LOCAL_PATH)/include
# Cause the linker to substitute our implementations for these functions, at
# a .so-wide level.
LOCAL_EXPORT_LDFLAGS:=\
	-Wl,--wrap=perror,--wrap=fflush,--wrap=fprintf,--wrap=vprintf,--wrap=printf \
	-Wl,--wrap=putc,--wrap=fputc,--wrap=putchar,--wrap=puts,--wrap=fputs \
	-Wl,--wrap=fwrite,--wrap=write,--wrap=writev
# Need this to prevent auto-use of builtin functions.
LOCAL_EXPORT_CFLAGS:= -fno-builtin-printf -fno-builtin-fprintf \
	-fno-builtin-fflush -fno-builtin-perror -fno-builtin-vprintf \
	-fno-builtin-putc -fno-builtin-putchar -fno-builtin-fputc \
	-fno-builtin-fputs -fno-builtin-puts -fno-builtin-fwrite \
	-fno-builtin-write -fno-builtin-writev
LOCAL_CFLAGS:=-fPIC -std=c99 -Wall -Wextra -W
LOCAL_CXXFLAGS:=-fPIC -std=c++98 -Wall -Wextra -W
LOCAL_ARM_MODE:=arm
include $(BUILD_STATIC_LIBRARY)

include $(CLEAR_VARS)
LOCAL_MODULE:=libfplutil_main
LOCAL_SRC_FILES:=$(LOCAL_PATH)/src/main.c
LOCAL_C_INCLUDES:=\
	$(LOCAL_PATH)/include \
	$(NDK_ROOT)/sources/android/native_app_glue
LOCAL_EXPORT_C_INCLUDES:=$(LOCAL_PATH)/include
LOCAL_CFLAGS:=-fPIC -std=c99 -Wall -Wextra -W
LOCAL_ARM_MODE:=arm
LOCAL_STATIC_LIBRARIES:=android_native_app_glue
include $(BUILD_STATIC_LIBRARY)

$(call import-module, native_app_glue)
