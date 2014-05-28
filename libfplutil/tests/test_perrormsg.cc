/*
* Copyright (c) 2014 Google, Inc.
*
* This software is provided 'as-is', without any express or implied
* warranty.  In no event will the authors be held liable for any damages
* arising from the use of this software.
* Permission is granted to anyone to use this software for any purpose,
* including commercial applications, and to alter it and redistribute it
* freely, subject to the following restrictions:
* 1. The origin of this software must not be misrepresented; you must not
* claim that you wrote the original software. If you use this software
* in a product, an acknowledgment in the product documentation would be
* appreciated but is not required.
* 2. Altered source versions must be plainly marked as such, and must not be
* misrepresented as being the original software.
* 3. This notice may not be removed or altered from any source distribution.
*/

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

	snprintf(PerrorMsgTests::expected, PerrorMsgTests::BUFSIZE, "%s: %s",
					 testmsg, strerror(EINTR));
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
	char big[PerrorMsgTests::BUFSIZE+10];
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
	EXPECT_EQ(0, strncmp(big, PerrorMsgTests::actual, PerrorMsgTests::BUFSIZE-1));
}

