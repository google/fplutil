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

#ifndef FPLUTIL_STRING_UTILS_H
#define FPLUTIL_STRING_UTILS_H

#include <string>

namespace fplutil {

/// Return `source` as a_string_in_snake_case.
/// https://en.wikipedia.org/wiki/Snake_case
std::string SnakeCase(const std::string& source);

/// Return `source` as AStringInCamelCase.
/// https://en.wikipedia.org/wiki/CamelCase
std::string CamelCase(const std::string& source);

}  // namespace fplutil

#endif  // FPLUTIL_STRING_UTILS_H
