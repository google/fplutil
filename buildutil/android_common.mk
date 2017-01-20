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
# Configurable locations of dependencies of this project.

# TODO: Remove when the LOCAL_PATH expansion bug in the NDK is fixed.
# Portable version of $(realpath) that omits drive letters on Windows.
realpath-portable = $(join $(filter %:,$(subst :,: ,$1)),\
                      $(realpath $(filter-out %:,$(subst :,: ,$1))))

# Converts the list of paths in $(1) into a list of paths that exist.
fplutil_existing_paths = $(foreach path,$(1),$(wildcard $(path)))

# Sets $(1) to be the first path in $(2) that exists, or to an error value
# otherwise.
fplutil_set_to_first_path_that_exists = \
  $(foreach path,$(call fplutil_existing_paths,$(2))\
                 CANNOT_FIND_DIRECTORY_FOR_$1,\
    $(eval $(1)?=$(path)))

# Flags to set in all compilations.
FPL_CFLAGS := -DGUNIT_NO_GOOGLE3

# Directory above the fplutil director.
FPLUTIL_PARENT_DIR:=$(call realpath-portable,$(call my-dir)/../..)

# FPL_ROOT is the directory that holds all of the FPL projects.
$(call fplutil_set_to_first_path_that_exists,FPL_ROOT,\
    $(DEPENDENCIES_ROOT) \
    $(LOCAL_PATH)/../dependencies \
    $(FPLUTIL_PARENT_DIR)/../libs \
    $(FPLUTIL_PARENT_DIR)/../third_party \
    $(FPLUTIL_PARENT_DIR))

# THIRD_PARTY_ROOT is the directory that holds the non-FPL projects
# upon which the FPL projects depend.
$(call fplutil_set_to_first_path_that_exists,THIRD_PARTY_ROOT,\
    $(DEPENDENCIES_ROOT) \
    $(LOCAL_PATH)/../dependencies \
    $(FPLUTIL_PARENT_DIR)/../third_party \
    $(FPLUTIL_PARENT_DIR)/../../../external \
    $(FPL_ROOT))

# PREBUILTS_ROOT is the directory that holds the prebuilt libraries
# upon which FPL projects depend.
$(call fplutil_set_to_first_path_that_exists,PREBUILTS_ROOT,\
    $(DEPENDENCIES_ROOT) \
    $(LOCAL_PATH)/../dependencies \
    $(FPLUTIL_PARENT_DIR)/../../../prebuilts \
    $(FPL_ROOT))

# Location of the Flatbuffers library.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_FLATBUFFERS_DIR,\
    $(FPL_ROOT)/flatbuffers)

# Location of the fplutil library.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_FPLUTIL_DIR,\
    $(FPL_ROOT)/fplutil)

# Location of the MathFu library.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_MATHFU_DIR,\
    $(FPL_ROOT)/mathfu)

# Location of the motive library.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_MOTIVE_DIR,\
    $(FPL_ROOT)/motive)

# Location of the fplbase library.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_FPLBASE_DIR,\
    $(FPL_ROOT)/fplbase)

# Location of the flatui library.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_FLATUI_DIR,\
    $(FPL_ROOT)/flatui)

# Location of the SDL library.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_SDL_DIR,\
    $(THIRD_PARTY_ROOT)/SDL2 \
    $(THIRD_PARTY_ROOT)/sdl)

# Location of the Freetype library.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_FREETYPE_DIR,\
    $(THIRD_PARTY_ROOT)/freetype2/freetype-2.6.1 \
    $(THIRD_PARTY_ROOT)/freetype)

# Location of the Gumbo library.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_GUMBO_DIR,\
    $(THIRD_PARTY_ROOT)/gumbo-parser \
    $(THIRD_PARTY_ROOT)/gumbo)

# Location of Gumbo include directory.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_GUMBO_INCLUDE_DIR,\
    $(DEPENDENCIES_GUMBO_DIR)/src \
    $(DEPENDENCIES_GUMBO_DIR))

# Location of the HarfBuzz library.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_HARFBUZZ_DIR,\
    $(THIRD_PARTY_ROOT)/harfbuzz)

# Location of the libunibreak library.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_LIBUNIBREAK_DIR,\
    $(THIRD_PARTY_ROOT)/libunibreak)

# Location of the hyphenation_pattern files.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_HYPHENATION_PATTERN_DIR,\
    $(THIRD_PARTY_ROOT)/hyphenation_patterns \
    $(THIRD_PARTY_ROOT)/hyphenation-patterns)

# Location of the Cardboard java library (required for fplbase)
# TODO(jsanmiya): Temporarily put the cardboard libs in fplutil/libs in case
# we don't have the ability to grab the Cardboard SDK.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_CARDBOARD_DIR,\
    $(PREBUILTS_ROOT)/cardboard-java/CardboardSample \
    $(DEPENDENCIES_FPLUTIL_DIR))

# Location of the STB library.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_STB_DIR,\
    $(THIRD_PARTY_ROOT)/stb \
    $(THIRD_PARTY_ROOT)/stblib)

# Location of the Webp library.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_WEBP_DIR,\
    $(THIRD_PARTY_ROOT)/webp \
    $(THIRD_PARTY_ROOT)/libwebp/v0_2)

# Location of the Vectorial library.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_VECTORIAL_DIR,\
    $(THIRD_PARTY_ROOT)/vectorial)

# Location of the googletest JNI files.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_GTEST_JNI_DIR,\
    $(FPL_ROOT)/fplutil/libfplutil/jni/libs/googletest)

# Location of the googletest library.
# Depending on googletest version, the gtest directory may be nested under
# googletest/googletest.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_GTEST_DIR,\
    ${THIRD_PARTY_ROOT}/googletest/googletest \
    ${FPL_ROOT}/googletest/googletest \
    ${FPL_ROOT}/googletest \
    ${THIRD_PARTY_ROOT}/gtest)

# Location of the googlemock library.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_GMOCK_DIR,\
    ${THIRD_PARTY_ROOT}/googletest/googlemock \
    ${THIRD_PARTY_ROOT}/gmock)

ifeq (,$(DETERMINED_DEPENDENCY_DIRS))
DETERMINED_DEPENDENCY_DIRS:=1
$(eval DEPENDENCIES_DIR_VALUE:=$$(DEPENDENCIES_$(DEP_DIR)_DIR))
print_dependency:
	@echo $(call realpath-portable,$(DEPENDENCIES_DIR_VALUE))
endif
