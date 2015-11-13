// Copyright 2015 Google Inc. All rights reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include <algorithm>
#include <assert.h>
#if defined(_MSC_VER)
#include <direct.h>    // Windows functions for directory creation.
#else
#include <dirent.h>
#endif
#include <fstream>
#include <sys/stat.h>  // POSIX functions for directory creation.

#include "fplutil/file_utils.h"

namespace fplutil {

using std::string;

#if defined(_WIN32)
static const char kDirectorySeparator = '\\';
#else
static const char kDirectorySeparator = '/';
#endif
static const char kDirectorySeparators[] = "\\/";

string FormatAsDirectoryName(const string& s) {
  const bool needs_slash = s.length() > 0 &&
                           s.find_first_of(kDirectorySeparators,
                                           s.length() - 1) == string::npos;
  return needs_slash ? s + kDirectorySeparator : s;
}

string RemoveExtensionFromName(const string& s) {
  const size_t dot = s.find_last_of('.');
  return dot == string::npos ? s : s.substr(0, dot);
}

string RemoveDirectoryFromName(const string& s) {
  const size_t slash = s.find_last_of(kDirectorySeparators);
  return slash == string::npos ? s : s.substr(slash + 1);
}

string BaseFileName(const string& s) {
  return RemoveExtensionFromName(RemoveDirectoryFromName(s));
}

string DirectoryName(const string& s) {
  const size_t slash = s.find_last_of(kDirectorySeparators);
  return slash == string::npos ? string("") : s.substr(0, slash + 1);
}

string FileExtension(const string& s) {
  const size_t dot = s.find_last_of('.');
  return dot == string::npos ? string("") : s.substr(dot + 1);
}

bool AbsoluteFileName(const string& s) {
  if (s.length() == 0) return false;
  const char c = s[0];
  for (const char* slash = kDirectorySeparators; *slash != '\0'; ++slash) {
    if (c == *slash) return true;
  }
  return false;
}

#if !defined(_MSC_VER)
static void MatchCase(CaseSensitivity case_sensitivity, string* s) {
  switch (case_sensitivity) {
    case kOsDefaultCaseSensitivity:
      assert(false); // not implemented
      break;

    case kCaseSensitive:
      break;

    case kCaseInsensitive:
      std::transform(s->begin(), s->end(), s->begin(), ::tolower);
      break;
  }
}
#endif  // !defined(_MSC_VER)

bool FileExists(const string& file_name) {
  struct stat buffer;
  return stat(file_name.c_str(), &buffer) == 0;
}

bool FileExists(const string& file_name,
                CaseSensitivity case_sensitivity) {
  // TODO: Implement case insensitive file name checking.
#if defined(_MSC_VER)
  (void)case_sensitivity;
  return FileExists(file_name);
#else
  // The standard C++ functions use the OS's case sensitivity.
  if (case_sensitivity == kOsDefaultCaseSensitivity) {
    return FileExists(file_name);
  }

  // There are no standard C++ functions that allow case sensitivity to be
  // specified, so we have to use directory functions.
  const string dir_name = DirectoryName(file_name);
  DIR* dir = opendir(dir_name.length() == 0 ? "." : dir_name.c_str());
  if (dir == NULL) return false;

  // Get the name of the file we want to find in this directory.
  string desired_name = RemoveDirectoryFromName(file_name);
  MatchCase(case_sensitivity, &desired_name);

  // Loop through every file in the directory.
  bool exists = false;
  for (;;) {
    dirent* ent = readdir(dir);
    if (ent == nullptr) break;

    // Return true if file name, respecting case sensitivity, is found.
    string actual_name(ent->d_name);
    MatchCase(case_sensitivity, &actual_name);
    if (desired_name == actual_name) {
      exists = true;
      break;
    }
  }

  // Strange things happen if the directory isn't closed.
  closedir(dir);
  dir = nullptr;
  return exists;
#endif  // defined(_MSC_VER)
}

#if defined(_MSC_VER)
static bool CreateSubDirectory(const string& sub_dir) {
  const int mkdir_result = _mkdir(sub_dir.c_str());
  const bool dir_created = mkdir_result == 0 || errno == EEXIST;
  return dir_created;
}
#else
static bool CreateSubDirectory(const string& sub_dir) {
  // Create the sub-directory using the POSIX mkdir function.
  // If slash is npos, we take the entire `dir` and create it.
  const mode_t kDirectoryMode = 0755;
  const int mkdir_result = mkdir(sub_dir.c_str(), kDirectoryMode);
  const bool dir_created = mkdir_result == 0 || errno == EEXIST;
  return dir_created;
}
#endif

bool CreateDirectory(const string& dir) {
  if (dir.length() == 0) return true;

  size_t slash = 0;
  for (;;) {
    // Find the next sub-directory after the last one we just created.
    slash = dir.find_first_of(kDirectorySeparators, slash + 1);

    // If slash is npos, we take the entire `dir` and create it.
    const string sub_dir = dir.substr(0, slash);

    // Create the sub-directory using the POSIX mkdir function.
    const bool dir_created = CreateSubDirectory(sub_dir);
    if (!dir_created) return false;

    // If no more slashes left, get out of here.
    if (slash == string::npos) break;
  }
  return true;
}

bool CopyFile(const string& target_file_name,
              const string& source_file_name) {
  std::ifstream source(source_file_name, std::ios::binary);
  std::ofstream target(target_file_name, std::ios::binary);
  if (!source || !target) return false;

  target << source.rdbuf();
  return true;
}

}  // namespace fplutil
