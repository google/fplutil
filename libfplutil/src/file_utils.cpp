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

#include <fstream>
#include <sys/stat.h>  // POSIX functions, for directory creation.

#include "fplutil/file_utils.h"

namespace fpl {

#if defined(_WIN32)
static const char kDirectorySeparator = '\\';
#else
static const char kDirectorySeparator = '/';
#endif
static const char kDirectorySeparators[] = "\\/";

std::string FormatAsDirectoryName(const std::string& s) {
  const bool needs_slash = s.length() > 0 &&
                           s.find_first_of(kDirectorySeparators,
                                           s.length() - 1) == std::string::npos;
  return needs_slash ? s + kDirectorySeparator : s;
}

std::string RemoveExtensionFromName(const std::string& s) {
  const size_t dot = s.find_last_of('.');
  return dot == std::string::npos ? s : s.substr(0, dot);
}

std::string RemoveDirectoryFromName(const std::string& s) {
  const size_t slash = s.find_last_of(kDirectorySeparators);
  return slash == std::string::npos ? s : s.substr(slash + 1);
}

std::string BaseFileName(const std::string& s) {
  return RemoveExtensionFromName(RemoveDirectoryFromName(s));
}

std::string DirectoryName(const std::string& s) {
  const size_t slash = s.find_last_of(kDirectorySeparators);
  return slash == std::string::npos ? std::string("") : s.substr(0, slash + 1);
}

std::string FileExtension(const std::string& s) {
  const size_t dot = s.find_last_of('.');
  return dot == std::string::npos ? std::string("") : s.substr(dot + 1);
}

bool AbsoluteFileName(const std::string& s) {
  const bool starts_with_slash =
      s.length() > 0 &&
      s.find_first_of(kDirectorySeparators, 0, 1) != std::string::npos;
  return starts_with_slash;
}

bool FileExists(const std::string& file_name) {
  struct stat buffer;
  return stat(file_name.c_str(), &buffer) == 0;
}

bool CreateDirectory(const std::string& dir) {
  if (dir.length() == 0) return true;

  size_t slash = 0;
  for (;;) {
    // Find the next sub-directory after the last one we just created.
    slash = dir.find_first_of(kDirectorySeparators, slash + 1);

    // Create the sub-directory using the POSIX mkdir function.
    // If slash is npos, we take the entire `dir` and create it.
    const mode_t kDirectoryMode = 0755;
    const std::string sub_dir = dir.substr(0, slash);
    const int mkdir_result = mkdir(sub_dir.c_str(), kDirectoryMode);
    const bool dir_created = mkdir_result == 0 || errno == EEXIST;
    if (!dir_created) return false;

    // If no more slashes left, get out of here.
    if (slash == std::string::npos) break;
  }
  return true;
}

bool CopyFile(const std::string& target_file_name,
              const std::string& source_file_name) {
  std::ifstream source(source_file_name, std::ios::binary);
  std::ofstream target(target_file_name, std::ios::binary);
  if (!source || !target) return false;

  target << source.rdbuf();
  return true;
}

}  // namespace fpl
