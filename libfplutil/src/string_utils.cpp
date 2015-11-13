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

#include <assert.h>
#include "fplutil/string_utils.h"

namespace fplutil {

static const char kSpaceChars[] = { '_', ' ' };

static inline bool IsSpace(char c) {
  for (size_t i = 0; i < sizeof(kSpaceChars) / sizeof(kSpaceChars[0]); ++i) {
    if (c == kSpaceChars[i]) return true;
  }
  return false;
}

static inline bool CanAppendSnakeBar(const std::string& s) {
  return s.size() > 0 && !IsSpace(s.back());
}

std::string SnakeCase(const std::string& source) {
  std::string snake;
  snake.reserve(2 * source.size());

  bool prev_is_digit = false;
  for (size_t i = 0; i < source.size(); ++i) {
    const char c = source[i];

    // When transitioning to or from a string of digits, we want to insert '_'.
    const bool is_digit = isdigit(c) != 0;
    const bool is_digit_transition = is_digit != prev_is_digit;
    prev_is_digit = is_digit;

    // Convert spaces to underbars.
    if (IsSpace(c)) {
      if (CanAppendSnakeBar(snake)) snake += '_';
      continue;
    }

    // Convert upper case letters into '_' + lower case letter.
    if (isupper(c) || is_digit_transition) {
      if (CanAppendSnakeBar(snake)) snake += '_';
      // tolower() returns digits unchanged.
      snake += static_cast<char>(tolower(c));      continue;
    }

    // Send through as-is.
    snake += c;
  }

  // Remove trailing underbar. There should be at most one since we never
  // output double underbars.
  if (snake.size() > 0 && snake.back() == '_') {
    snake.resize(snake.size() - 1);
  }
  assert(snake.size() == 0 || snake.back() != '_');

  return snake;
}

std::string CamelCase(const std::string& source) {
  std::string camel;
  camel.reserve(source.size());

  bool capitalize_next = true;
  for (size_t i = 0; i < source.size(); ++i) {
    const char c = source[i];

    // Skip spaces, but flag the next letter as start of new word.
    if (IsSpace(c)) {
      capitalize_next = true;
      continue;
    }

    // If flagged for capitalization, capitalize and clear flag.
    if (capitalize_next) {
      camel += static_cast<char>(toupper(c));
      capitalize_next = false;
      continue;
    }

    // Send through as-is.
    camel += c;
  }
  return camel;
}

}  // namespace fplutil
