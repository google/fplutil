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

#include "gtest/gtest.h"
#include "fplutil/string_utils.h"

using fplutil::SnakeCase;
using fplutil::CamelCase;

class StringTests : public ::testing::Test {
 public:

 protected:
  virtual void SetUp() {}
  virtual void TearDown() {}
};

struct StringVariant {
  const char* snake;  // Snake-case version of string.
  const char* camel;  // Camel-case version of same string.
  const char* bars;   // Mixed-up version of string, with extra underbars.
  const char* spaces; // Mixed-up version of string, with extra spaces.
  const char* extra;  // Mixed-up version of string, with extra bars and spaces.
};

static const StringVariant kTestStrings[] = {
  { "word", "Word", "__word", "  word", "_ word" },
  { "two_words", "TwoWords", "Two__words__", "Two  words  ", "Two  words_ " },
  { "three_of_em", "ThreeOfEm", "three_OfEm", "three OfEm", "_three_ OfEm " },
  { "a_b_c_mart", "ABCMart", "_a_BC__Mart____", " a BC  Mart    ",
    "_ a BC__Mart    " },
  { "1_digit", "1Digit", "1__Digit", "1  Digit", " 1 Digit__" },
  { "99_digit", "99Digit", "__99Digit", "  99Digit", "99_ Digit " },
  { "digit_123", "Digit123", "Digit_123_", "Digit 123 ", "Digit 123  __" },
};

TEST_F(StringTests, Snake_FromSnake) {
  for (size_t i = 0; i < sizeof(kTestStrings) / sizeof(kTestStrings[0]); ++i) {
    EXPECT_EQ(kTestStrings[i].snake, SnakeCase(kTestStrings[i].snake));
  }
}

TEST_F(StringTests, Snake_FromCamel) {
  for (size_t i = 0; i < sizeof(kTestStrings) / sizeof(kTestStrings[0]); ++i) {
    EXPECT_EQ(kTestStrings[i].snake, SnakeCase(kTestStrings[i].camel));
  }
}

TEST_F(StringTests, Snake_FromBars) {
  for (size_t i = 0; i < sizeof(kTestStrings) / sizeof(kTestStrings[0]); ++i) {
    EXPECT_EQ(kTestStrings[i].snake, SnakeCase(kTestStrings[i].bars));
  }
}

TEST_F(StringTests, Snake_FromSpaces) {
  for (size_t i = 0; i < sizeof(kTestStrings) / sizeof(kTestStrings[0]); ++i) {
    EXPECT_EQ(kTestStrings[i].snake, SnakeCase(kTestStrings[i].spaces));
  }
}

TEST_F(StringTests, Snake_FromExtra) {
  for (size_t i = 0; i < sizeof(kTestStrings) / sizeof(kTestStrings[0]); ++i) {
    EXPECT_EQ(kTestStrings[i].snake, SnakeCase(kTestStrings[i].extra));
  }
}

TEST_F(StringTests, Camel_FromSnake) {
  for (size_t i = 0; i < sizeof(kTestStrings) / sizeof(kTestStrings[0]); ++i) {
    EXPECT_EQ(kTestStrings[i].camel, CamelCase(kTestStrings[i].snake));
  }
}

TEST_F(StringTests, Camel_FromCamel) {
  for (size_t i = 0; i < sizeof(kTestStrings) / sizeof(kTestStrings[0]); ++i) {
    EXPECT_EQ(kTestStrings[i].camel, CamelCase(kTestStrings[i].camel));
  }
}

TEST_F(StringTests, Camel_FromBars) {
  for (size_t i = 0; i < sizeof(kTestStrings) / sizeof(kTestStrings[0]); ++i) {
    EXPECT_EQ(kTestStrings[i].camel, CamelCase(kTestStrings[i].bars));
  }
}

TEST_F(StringTests, Camel_FromSpaces) {
  for (size_t i = 0; i < sizeof(kTestStrings) / sizeof(kTestStrings[0]); ++i) {
    EXPECT_EQ(kTestStrings[i].camel, CamelCase(kTestStrings[i].spaces));
  }
}

TEST_F(StringTests, Camel_FromExtra) {
  for (size_t i = 0; i < sizeof(kTestStrings) / sizeof(kTestStrings[0]); ++i) {
    EXPECT_EQ(kTestStrings[i].camel, CamelCase(kTestStrings[i].extra));
  }
}

int main(int argc, char **argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}

