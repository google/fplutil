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

#include <iostream>
#include <inttypes.h>
#include <string.h>
#include <sys/uio.h>
#include "gtest/gtest.h"
#include "fplutil/print.h"
#include "fplutil/main.h"

class AndroidStdioTests : public ::testing::Test {
 public:
  static const int NO_PRIORITY = -1;
  static const char *NO_TAG;
  static void Validate(const char *expect_str,
                       int expect_priority = ANDROID_LOG_WARN,
                       const char *expect_tag = "test");

 protected:
  virtual void SetUp() {
    SetAndroidStdioOutputFunction(Intercept);
    SetAndroidLogWrapperBufferSize(PRINTSIZE);
    fflush(stdout);
    fflush(stderr);
    // We set the tag and prio to nondefault values here to test that they
    // get correctly set, see Validate().
    SetAndroidLogWrapperPriority(ANDROID_LOG_WARN);
    SetAndroidLogWrapperTag(TEST_TAG);
    *buffer_ = '\0';
    priority_ = NO_PRIORITY;
    tag_ = NO_TAG;
  }
  virtual void TearDown() {
    SetAndroidStdioOutputFunction(__android_log_vprint);
  }

 private:
  static int Intercept(int priority, const char *tag, const char *fmt,
                       va_list ap);

  static int priority_;
  static const char *tag_;
  static const char *TEST_TAG;
  static const size_t PRINTSIZE = 1024;
  static char buffer_[PRINTSIZE];
};

int AndroidStdioTests::priority_;
const char *AndroidStdioTests::tag_;
const char *AndroidStdioTests::TEST_TAG = "test";
const size_t AndroidStdioTests::PRINTSIZE;
char AndroidStdioTests::buffer_[AndroidStdioTests::PRINTSIZE];
const int AndroidStdioTests::NO_PRIORITY;
const char *AndroidStdioTests::NO_TAG = "";

int AndroidStdioTests::Intercept(int priority, const char *tag, const char *fmt,
                                 va_list list) {
  priority_ = priority;
  tag_ = tag;  // Safe as this should always be set to the global internal tag.
  int rc = vsnprintf(buffer_, sizeof(buffer_), fmt, list);
  // Uncomment for fun debugging.
  //__android_log_vprint(prio, "intercept", fmt, list);
  EXPECT_LT(rc, sizeof(buffer_)) << "print overflow";
}

void AndroidStdioTests::Validate(const char *expect_str, int expect_priority,
                                 const char *expect_tag) {
  SetAndroidStdioOutputFunction(__android_log_vprint);
  EXPECT_STREQ(expect_str, buffer_);
  EXPECT_STREQ(expect_tag, tag_);
  EXPECT_EQ(expect_priority, priority_);
  SetAndroidStdioOutputFunction(Intercept);
}

TEST_F(AndroidStdioTests, TestPrintfTrivial) {
  SCOPED_TRACE("TestPrintfTrivial");
  const char *msg = "TestPrintfTrivial\n";
  const char *out = "TestPrintfTrivial";  // Note: no newline, trailing newlines
                                          // are trimmed internally because the
                                          // android log adds one per line out.
  printf(msg);
  AndroidStdioTests::Validate(out);
}

TEST_F(AndroidStdioTests, TestPrintfUnbuffered) {
  SCOPED_TRACE("TestPrintfUnbuffered");
  SetAndroidLogWrapperBufferSize(0);
  const char *msg = __PRETTY_FUNCTION__;  // Note: no newline.
  printf(msg);
  AndroidStdioTests::Validate(msg);
}

TEST_F(AndroidStdioTests, TestPrintfBuffered) {
  SCOPED_TRACE("TestPrintfBuffered");
  const char *msg = __PRETTY_FUNCTION__;  // Note: no newline.
  printf(msg);
  // Should get nothing yet as this is smaller than the buffer.
  AndroidStdioTests::Validate("", AndroidStdioTests::NO_PRIORITY,
                              AndroidStdioTests::NO_TAG);
  fflush(stdout);
  AndroidStdioTests::Validate(msg);
}

TEST_F(AndroidStdioTests, TestPrintfBufferedSequential) {
  SCOPED_TRACE("TestPrintfBufferedSequential");
  const size_t SIZE = 64;
  char expected[SIZE + 1];
  for (int i = 0; i < SIZE; ++i) {
    char c = 'a' + (i % ('z' - 'a'));
    printf("%c", c);
    expected[i] = c;
  }
  expected[SIZE] = '\0';
  // Should get nothing yet as this is smaller than the buffer.
  AndroidStdioTests::Validate("", AndroidStdioTests::NO_PRIORITY,
                              AndroidStdioTests::NO_TAG);
  fflush(stdout);
  AndroidStdioTests::Validate(expected);
}

TEST_F(AndroidStdioTests, TestPrintfTooBig) {
  SCOPED_TRACE("TestPrintfTooBig");
  SetAndroidLogWrapperBufferSize(5);
  const char *msg = "TestPrintfTooBig\n";
  printf(msg);
  AndroidStdioTests::Validate(msg);
}

TEST_F(AndroidStdioTests, TestPrintfEdge) {
  SCOPED_TRACE("TestPrintfEdge");
  SetAndroidLogWrapperBufferSize(1);
  const char *msg = __PRETTY_FUNCTION__;
  char expected[2];
  expected[1] = '\0';
  for (int i = 0; msg[i]; ++i) {
    printf("%c", msg[i]);
    expected[0] = msg[i];
    AndroidStdioTests::Validate(expected);
  }
}

TEST_F(AndroidStdioTests, TestPutc) {
  SCOPED_TRACE("TestPutc");
  const size_t SIZE = 64;
  char expected[SIZE + 1];
  for (int i = 0; i < SIZE; ++i) {
    char c = 'a' + (i % ('z' - 'a'));
    putc(c, stdout);
    expected[i] = c;
  }
  expected[SIZE] = '\0';
  // Should get nothing yet as this is smaller than the buffer.
  AndroidStdioTests::Validate("", AndroidStdioTests::NO_PRIORITY,
                              AndroidStdioTests::NO_TAG);
  fflush(stdout);
  AndroidStdioTests::Validate(expected);
}

TEST_F(AndroidStdioTests, TestPutchar) {
  SCOPED_TRACE("TestPutchar");
  const size_t SIZE = 64;
  char expected[SIZE + 1];
  for (int i = 0; i < SIZE; ++i) {
    char c = 'A' + (i % ('Z' - 'A'));
    putchar(c);
    expected[i] = c;
  }
  expected[SIZE] = '\0';
  // Should get nothing yet as this is smaller than the buffer.
  AndroidStdioTests::Validate("", AndroidStdioTests::NO_PRIORITY,
                              AndroidStdioTests::NO_TAG);
  fflush(stdout);
  AndroidStdioTests::Validate(expected);
}

TEST_F(AndroidStdioTests, TestFputc) {
  SCOPED_TRACE("TestFputc");
  const size_t SIZE = 64;
  char expected[SIZE + 1];
  for (int i = 0; i < SIZE; ++i) {
    char c = 'a' + (i % ('z' - 'a'));
    fputc(c, stderr);
    expected[i] = c;
  }
  expected[SIZE] = '\0';
  // Should get nothing yet as this is smaller than the buffer.
  AndroidStdioTests::Validate("", AndroidStdioTests::NO_PRIORITY,
                              AndroidStdioTests::NO_TAG);
  fflush(stdout);
  AndroidStdioTests::Validate(expected);
}

TEST_F(AndroidStdioTests, TestFprintfTrivial) {
  SCOPED_TRACE("TestFprintfTrivial");
  SetAndroidLogWrapperBufferSize(0);
  const char *msg = __FUNCTION__;
  const char *msg2 = __PRETTY_FUNCTION__;
  fprintf(stdout, msg);
  AndroidStdioTests::Validate(msg);
  fprintf(stderr, msg2);
  AndroidStdioTests::Validate(msg2);
}

TEST_F(AndroidStdioTests, TestFwriteTrivial) {
  SCOPED_TRACE("TestFwriteTrivial");
  SetAndroidLogWrapperBufferSize(0);
  const char *msg = __FUNCTION__;
  const char *msg2 = __PRETTY_FUNCTION__;
  int rc = fwrite(msg, strlen(msg) + 1, 1, stdout);
  EXPECT_EQ(1, rc);
  AndroidStdioTests::Validate(msg);
  rc = fwrite(msg2, 1, strlen(msg2) + 1, stderr);
  EXPECT_EQ(strlen(msg2) + 1, rc);
  AndroidStdioTests::Validate(msg2);
}

TEST_F(AndroidStdioTests, TestWriteTrivial) {
  SCOPED_TRACE("TestWriteTrivial");
  SetAndroidLogWrapperBufferSize(0);
  const char *msg = __FUNCTION__;
  const char *msg2 = __PRETTY_FUNCTION__;
  write(fileno(stdout), msg, strlen(msg) + 1);
  AndroidStdioTests::Validate(msg);
  write(fileno(stderr), msg2, strlen(msg2) + 1);
  AndroidStdioTests::Validate(msg2);
}

TEST_F(AndroidStdioTests, TestWritevTrivial) {
  SCOPED_TRACE("TestWritevTrivial");
  SetAndroidLogWrapperBufferSize(0);
  const char *msg = __FUNCTION__;
  const char *msg2 = __PRETTY_FUNCTION__;
  struct iovec iov;
  iov.iov_len = strlen(msg) + 1;
  iov.iov_base = (void *)msg;
  writev(fileno(stdout), &iov, 1);
  AndroidStdioTests::Validate(msg);
  iov.iov_len = strlen(msg2) + 1;
  iov.iov_base = (void *)msg2;
  writev(fileno(stderr), &iov, 1);
  AndroidStdioTests::Validate(msg2);
}

TEST_F(AndroidStdioTests, TestFprintfOther) {
  SCOPED_TRACE("TestFprintfOther");
  const char *msg = "TestFprintfOther\n";
  FILE *devnull = fopen("/dev/null", "w");
  EXPECT_NE((intptr_t)devnull, NULL);
  fprintf(devnull, msg);
  // Should get nothing.
  AndroidStdioTests::Validate("", AndroidStdioTests::NO_PRIORITY,
                              AndroidStdioTests::NO_TAG);
  fclose(devnull);
}

TEST_F(AndroidStdioTests, TestFputcOther) {
  SCOPED_TRACE("TestFPutcfOther");
  FILE *devnull = fopen("/dev/null", "w");
  EXPECT_NE((intptr_t)devnull, NULL);
  fputc('a', devnull);
  // Should get nothing.
  AndroidStdioTests::Validate("", AndroidStdioTests::NO_PRIORITY,
                              AndroidStdioTests::NO_TAG);
  fclose(devnull);
}

TEST_F(AndroidStdioTests, TestCoutTrivial) {
  SCOPED_TRACE("TestCoutTrivial");
  const char *msg = __PRETTY_FUNCTION__;
  std::cout << msg << std::endl;  // Since Android will add an extra newline,
                                  // endl should be trimmed internally.
  AndroidStdioTests::Validate(msg);
}

TEST_F(AndroidStdioTests, TestCerrTrivial) {
  SCOPED_TRACE("TestCerrTrivial");
  const char *msg = __PRETTY_FUNCTION__;
  std::cerr << msg << std::endl;  // Since Android will add an extra newline,
                                  // endl should be trimmed internally.
  AndroidStdioTests::Validate(msg);
}

int main(int argc, char **argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}

