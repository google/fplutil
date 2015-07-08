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

#include <errno.h>
#include <string.h>
#include "gtest/gtest.h"
#include "fplutil/print.h"
#include "fplutil/main.h"

class PerrorMsgTests : public ::testing::Test {
 public:
  static const size_t BUFSIZE = 512;
  static char expected[BUFSIZE];
  static char actual[BUFSIZE];

 protected:
  virtual void SetUp() {}
  virtual void TearDown() {}
};

const size_t PerrorMsgTests::BUFSIZE;
char PerrorMsgTests::expected[PerrorMsgTests::BUFSIZE];
char PerrorMsgTests::actual[PerrorMsgTests::BUFSIZE];

TEST_F(PerrorMsgTests, TestWithMessage) {
  const char *testmsg = "Testing 1 2 3";

  snprintf(PerrorMsgTests::expected, PerrorMsgTests::BUFSIZE, "%s: %s", testmsg,
           strerror(EINTR));
  AndroidPerrorMsg(testmsg, EINTR, PerrorMsgTests::actual,
                   PerrorMsgTests::BUFSIZE);
  EXPECT_STREQ(PerrorMsgTests::expected, PerrorMsgTests::actual);
}

TEST_F(PerrorMsgTests, TestWithoutMessage) {
  strncpy(PerrorMsgTests::expected, strerror(EBADF), PerrorMsgTests::BUFSIZE);
  *(PerrorMsgTests::expected + PerrorMsgTests::BUFSIZE - 1) = '\0';
  AndroidPerrorMsg(NULL, EBADF, PerrorMsgTests::actual,
                   PerrorMsgTests::BUFSIZE);
  EXPECT_STREQ(PerrorMsgTests::expected, PerrorMsgTests::actual);
}

TEST_F(PerrorMsgTests, TestErrnoRange) {
  const char *testmsg = "E R R O R";
  int i;

  // Currently both glibc and bionic define valid errno values
  // as small positive ints.  This range should cover them, though
  // this is *not* a standardized value.  If this test fails, check the
  // current errno range in your android NDK.
  for (i = -10000; i < 10000; ++i) {
    snprintf(PerrorMsgTests::expected, PerrorMsgTests::BUFSIZE, "%s: %s",
             testmsg, strerror(i));
    AndroidPerrorMsg(testmsg, i, PerrorMsgTests::actual,
                     PerrorMsgTests::BUFSIZE);
    EXPECT_STREQ(PerrorMsgTests::expected, PerrorMsgTests::actual);

    strncpy(PerrorMsgTests::expected, strerror(i), PerrorMsgTests::BUFSIZE);
    *(PerrorMsgTests::expected + PerrorMsgTests::BUFSIZE - 1) = '\0';
    AndroidPerrorMsg(NULL, i, PerrorMsgTests::actual, PerrorMsgTests::BUFSIZE);
    EXPECT_STREQ(PerrorMsgTests::expected, PerrorMsgTests::actual);
  }
}

TEST_F(PerrorMsgTests, TestBigger) {
  char big[PerrorMsgTests::BUFSIZE + 10];
  int i;

  for (i = 0; i < sizeof(big); ++i) {
    big[i] = 'x';
  }
  *(big + sizeof(big) - 1) = '\0';

  snprintf(PerrorMsgTests::expected, PerrorMsgTests::BUFSIZE, "%s: %s", big,
           strerror(ENOSPC));
  AndroidPerrorMsg(big, ENOSPC, PerrorMsgTests::actual,
                   PerrorMsgTests::BUFSIZE);
  EXPECT_STREQ(PerrorMsgTests::expected, PerrorMsgTests::actual);
  EXPECT_EQ(0,
            strncmp(big, PerrorMsgTests::actual, PerrorMsgTests::BUFSIZE - 1));
}

int main(int argc, char **argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}

