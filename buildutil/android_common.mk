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

# Culls all relative paths in $(2) paths that don't exist relative to $(1)
fplutil_existing_relative_paths_ret_abs = \
  $(foreach rel_path,$(2),$(wildcard $(1)/$(rel_path)))

# Removes path prefex in $(1) from all absolute paths in $(2).
fplutil_make_relative_path = \
  $(foreach abs_path,$(2),$(subst $(1)/,,$(abs_path)))

# Culls all relative paths in $(2) paths that don't exist relative to $(1)
fplutil_existing_relative_paths = \
  $(call fplutil_make_relative_path,$(1),\
    $(call fplutil_existing_relative_paths_ret_abs,$(1),$(2)))

# Sets $(1) to be the first path in $(2) that exists, or to an error value
# otherwise.
fplutil_set_to_first_path_that_exists = \
  $(foreach path,$(call fplutil_existing_paths,$(2))\
                 CANNOT_FIND_DIRECTORY_FOR_$1,\
    $(eval $(1)?=$(path)))

# Sets $(1) to be the first path in $(3) that exists relative to $(2),
# or to an error value otherwise.
fplutil_set_to_first_relative_path_that_exists = \
  $(foreach path,$(call fplutil_existing_relative_paths,$(2),$(3))\
                 CANNOT_FIND_DIRECTORY_FOR_$1,\
    $(eval $(1)?=$(path)))

# Retuns space-separated list of files in $(1)/$(2) that have extension $(3).
# Files are returned relative to $(1).
#   $(1) holds the root path; all returned files are relative to this path
#   $(2) holds the subdirectory name
#   $(3) extension of files
fplutil_all_files_relative_to_path_in_subdirectory = \
  $(call fplutil_make_relative_path,$(1),\
    $(wildcard $(1)/$(2)/*.$(3)) $(wildcard $(1)/$(2)/**/*.$(3)))


# Flags to set in all compilations.
FPL_CFLAGS := -DGUNIT_NO_GOOGLE3

# Directory above the source directory.
LOCAL_REAL_DIR:=$(call realpath-portable,$(LOCAL_PATH))

# Directory above the fplutil directory.
FPLUTIL_PARENT_DIR:=$(call realpath-portable,$(call my-dir)/../..)

# GitHub's `dependencies` directory.
$(call fplutil_set_to_first_path_that_exists,GITHUB_DEPENDENCIES_DIR,\
    $(LOCAL_REAL_DIR)/../dependencies \
    $(LOCAL_REAL_DIR)/../../dependencies \
    $(LOCAL_REAL_DIR)/../../../dependencies \
    $(LOCAL_REAL_DIR)/../../../../dependencies \
    $(LOCAL_REAL_DIR)/../../../../../dependencies \
    $(LOCAL_REAL_DIR)/../../../../../../dependencies)

# FPL_ROOT is the directory that holds all of the FPL projects.
# When using --clone from GitHub, it will be the `dependencies` directory.
# In this case, the cloned project itself will be under PARENT_DIR instead of
# FPL_ROOT, but all the other FPL projects will be under FPL_ROOT.
$(call fplutil_set_to_first_path_that_exists,FPL_ROOT,\
    $(DEPENDENCIES_ROOT) \
    $(GITHUB_DEPENDENCIES_DIR) \
    $(FPLUTIL_PARENT_DIR)/../libs \
    $(FPLUTIL_PARENT_DIR)/../third_party \
    $(FPLUTIL_PARENT_DIR))

# THIRD_PARTY_ROOT is the directory that holds the non-FPL projects
# upon which the FPL projects depend.
$(call fplutil_set_to_first_path_that_exists,THIRD_PARTY_ROOT,\
    $(DEPENDENCIES_ROOT) \
    $(GITHUB_DEPENDENCIES_DIR) \
    $(FPLUTIL_PARENT_DIR)/../third_party \
    $(FPLUTIL_PARENT_DIR)/../../../external \
    $(FPL_ROOT))

# PREBUILTS_ROOT is the directory that holds the prebuilt libraries
# upon which FPL projects depend.
$(call fplutil_set_to_first_path_that_exists,PREBUILTS_ROOT,\
    $(DEPENDENCIES_ROOT) \
    $(GITHUB_DEPENDENCIES_DIR) \
    $(FPLUTIL_PARENT_DIR)/../../../prebuilts \
    $(FPL_ROOT))

# Location of the Breadboard library.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_BREADBOARD_DIR,\
    $(FPL_ROOT)/breadboard \
    $(GITHUB_DEPENDENCIES_DIR)/../../breadboard)

# Location of the breadboard module library's module collection.
$(call fplutil_set_to_first_path_that_exists,\
    DEPENDENCIES_BREADBOARD_MODULE_LIBRARY_DIR,\
    $(DEPENDENCIES_BREADBOARD_DIR)/module_library)

# Location of the CORGI library.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_CORGI_DIR,\
    $(FPL_ROOT)/corgi\
    $(GITHUB_DEPENDENCIES_DIR)/../../corgi)

# Location of the CORGI component library.
$(call fplutil_set_to_first_path_that_exists,\
    DEPENDENCIES_CORGI_COMPONENT_LIBRARY_DIR,\
    $(DEPENDENCIES_CORGI_DIR)/component_library)

# Location of the Flatbuffers library.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_FLATBUFFERS_DIR,\
    $(FPL_ROOT)/flatbuffers \
    $(GITHUB_DEPENDENCIES_DIR)/../../flatbuffers)

# Location of the flatui library.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_FLATUI_DIR,\
    $(FPL_ROOT)/flatui \
    $(GITHUB_DEPENDENCIES_DIR)/../../flatui)

# Location of the fplbase library.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_FPLBASE_DIR,\
    $(FPL_ROOT)/fplbase \
    $(GITHUB_DEPENDENCIES_DIR)/../../fplbase)

# Location of the fplutil library.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_FPLUTIL_DIR,\
    $(FPL_ROOT)/fplutil \
    $(GITHUB_DEPENDENCIES_DIR)/../../fplutil)

# Location of the MathFu library.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_MATHFU_DIR,\
    $(FPL_ROOT)/mathfu \
    $(GITHUB_DEPENDENCIES_DIR)/../../mathfu)

# Location of the motive library.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_MOTIVE_DIR,\
    $(FPL_ROOT)/motive \
    $(GITHUB_DEPENDENCIES_DIR)/../../motive)

# Location of the Pindrop library.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_PINDROP_DIR,\
    $(FPL_ROOT)/pindrop \
    $(GITHUB_DEPENDENCIES_DIR)/../../pindrop)

# Location of the Scene Lab library.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_SCENE_LAB_DIR,\
    $(FPL_ROOT)/scene_lab \
    $(GITHUB_DEPENDENCIES_DIR)/../../scene_lab)

# Location of the SDL library.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_SDL_DIR,\
    $(THIRD_PARTY_ROOT)/SDL2 \
    $(THIRD_PARTY_ROOT)/sdl)

# Location of the SDL Mixer library.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_SDL_MIXER_DIR,\
    $(THIRD_PARTY_ROOT)/SDL_mixer \
    $(THIRD_PARTY_ROOT)/sdl_mixer)

# Location of the Ogg library relative to the SDL Mixer library.
# Must come after SDL Mixer.
$(call fplutil_set_to_first_relative_path_that_exists,\
    DEPENDENCIES_LIBOGG_REL_SDL_MIXER,$(DEPENDENCIES_SDL_MIXER_DIR),\
    ../libogg \
    external/libogg-1.3.1)

# Location of the Tremor library relative to the SDL Mixer library.
# Must come after SDL Mixer.
$(call fplutil_set_to_first_relative_path_that_exists,\
    DEPENDENCIES_TREMOR_REL_SDL_MIXER,$(DEPENDENCIES_SDL_MIXER_DIR),\
    ../tremor \
    external/libvorbisidec-1.2.1)

# Location of the Vorbis library relative to the SDL Mixer library.
# Must come after SDL Mixer.
$(call fplutil_set_to_first_relative_path_that_exists,\
    DEPENDENCIES_LIBVORBIS_REL_SDL_MIXER,$(DEPENDENCIES_SDL_MIXER_DIR),\
    ../libvorbis \
    external/libvorbis-1.3.3)

# Location of the Bullet physics library.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_BULLETPHYSICS_DIR,\
    $(THIRD_PARTY_ROOT)/bulletphysics \
    $(THIRD_PARTY_ROOT)/bullet)

# Location of the Freetype library.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_FREETYPE_DIR,\
    $(THIRD_PARTY_ROOT)/freetype2/freetype-2.8.1 \
    $(THIRD_PARTY_ROOT)/freetype)

# Location of the Firebase C++ library.
# You can specify FIREBASE_SDK in the environment.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_FIREBASE_DIR,\
    $(FIREBASE_SDK) \
    $(PREBUILTS_ROOT)/firebase_cpp_sdk \
    $(PREBUILTS_ROOT)/cpp-firebase/firebase_cpp_sdk)

# Location of the Google Play Games library.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_GPG_DIR,\
    $(GPG_SDK) \
    $(PREBUILTS_ROOT)/gpg-cpp-sdk/android)

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
    ${THIRD_PARTY_ROOT}/gtest)

# Location of the googlemock library.
$(call fplutil_set_to_first_path_that_exists,DEPENDENCIES_GMOCK_DIR,\
    ${THIRD_PARTY_ROOT}/googletest/googlemock \
    ${THIRD_PARTY_ROOT}/gmock)

# Some internal libraries have their #include paths relative to the root
# of the internal directory tree.
# We compensate by adding the root of the internal directory tree to the
# include path, in this situation.
ifneq ("$(wildcard ${THIRD_PARTY_ROOT}/../third_party)","")
    FPL_ABSOLUTE_INCLUDE_DIR := ${THIRD_PARTY_ROOT}/..
endif

ifeq (,$(DETERMINED_DEPENDENCY_DIRS))
DETERMINED_DEPENDENCY_DIRS:=1
$(eval DEPENDENCIES_DIR_VALUE:=$$(DEPENDENCIES_$(DEP_DIR)_DIR))
print_dependency:
	@echo $(call realpath-portable,$(DEPENDENCIES_DIR_VALUE))
endif
