// Copyright 2014 Google Inc. All rights reserved.
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

#ifndef FPLUTIL_FILE_UTILS_H
#define FPLUTIL_FILE_UTILS_H

#include <string>

namespace fpl {

/// Ensure that `s` has a directory slash on the end of it.
std::string DirectoryName(const std::string& s);

/// Remove the last `.` from `s`, and any text after it.
std::string RemoveExtensionFromName(const std::string& s);

/// Remove all text up to and including the last `/` or `\` in `s`.
std::string RemoveDirectoryFromName(const std::string& s);

/// Remove both the extention and directory from name.
std::string BaseFileName(const std::string& s);

/// Create the sequence of directories specified by `dir`.
/// @param dir Directory to create. Can be and absolute path, or a path
///            relative to the current directory.
/// @return true iff the directory was created successfully.
bool CreateDirectory(const std::string& dir);

/// Copy a file from one location to another. Does *not* create the directory
/// for the target file, so will fail if it doesn't exist.
/// @return true iff the file was successfully copied.
bool CopyFile(const std::string& target_file_name,
              const std::string& source_file_name);

}  // namespace fpl

#endif  // FPLUTIL_FILE_UTILS_H
