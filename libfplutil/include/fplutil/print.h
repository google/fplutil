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
#ifndef FPLUTIL_PRINT_H
#define FPLUTIL_PRINT_H

// Linking this library will automatically wrap calls to stdio and iostreams
// using the Android make system if you import this module using the NDK
// import-module function:
//
// $(call import-module,libfplutil/jni)
//
// Note: If using your own make system, to link against this library at all,
// you must manually wrap these functions. To manually wrap functions, pass the
// corresponding '--wrap=<name>' option on your link line. For example:
//
// LDFLAGS+= -Wl,--wrap=perror,--wrap=fflush,--wrap=fprintf,--wrap=vprintf
//   -Wl,--wrap=putc,--wrap=fputc,--wrap=putchar,--wrap=puts,--wrap=fputs
//   -Wl,--wrap=fwrite,--wrap=write,--wrap=writev,--wrap=printf
// CFLAGS+= -fno-builtin-printf -fno-builtin-fprintf
//   -fno-builtin-fflush -fno-builtin-perror -fno-builtin-vprintf
//   -fno-builtin-putc -fno-builtin-putchar -fno-builtin-fputc
//   -fno-builtin-fputs -fno-builtin-puts -fno-builtin-fwrite
//   -fno-builtin-write -fno-builtin-writev
//
// Again, no need to do this if using ndk-build and the Android.mk make system.
//
// In code, simply include this project's headers and everything should work.
// For example:
//
// #include "fplutil/print.h"
// #include "fplutil/main.h"
//
// int main(int argc, char **argv) {
//   SetAndroidLogWrapperTag("my_application");
//   printf("Print to the log from printf\n");
//   std::cout << "Print to the log from a stream" << std::endl;
//   return 0;
// }
//
// will print "Print to the log from printf" and
// "Print to the log from a stream" to Android's log stream which can be viewed
// using "adb logcat".  All log messages from the application will be prefixed
// with the tag, "my_application" so they can optionally extracted from
// "adb logcat" output.

#if defined(ANDROID) || defined(__ANDROID__)

#include <android/log.h>
#include <stdarg.h>
#include <stdio.h>

#if defined(__cplusplus)
extern "C" {
#endif  // defined(__cplusplus)

// This is the function signature to use if you would like to intercept
// printf calls in your code. See SetAndroidLogOutputFunction() below.
// The first two parameters to this function are the log priority and tag,
// respectively. The remaining ones are the same as for the stdio function
// vprintf(), and overall the expected semantics for this function are the
// same as for vprintf(). Please see:
// http://pubs.opengroup.org/onlinepubs/9699919799/functions/vfprintf.html
typedef int (*AndroidLogOutputFunction)(int priority, const char *tag,
                                        const char *format, va_list list);

// Set the tag used for log output by the wrappers.  This can used when
// filtering the output of "adb logcat" to distinguish the log messages from
// this application vs. other applications and the rest of the system.
// Note that this pointer is simply assigned so it must have permanent lifetime.
//
// Arguments:
//  tag: A null terminated C string to use as the log tag. Default is "main".
//
// Returns:
//  0 on success, -1 if tag is null or an empty string.
int SetAndroidLogWrapperTag(const char *tag);

// Set the priority used for log output by the wrappers.
//
// Arguments:
//  priority: An android log priority, as described in the Android NDK header
//            file android/log.h.  Default is ANDROID_LOG_INFO from that file.
void SetAndroidLogWrapperPriority(int priority);

// Set the buffer size for the wrappers. Default is 256 bytes. Setting this to
// zero will force unbuffered output, which may have unexpected formatting
// such as additional newlines as text is immediately sent to the log. Nonzero
// values will accumulate writes until a newline is encountered or the buffer
// size is reached.
//
// Buffering is done to allow multiple stdio calls to output on the same line,
// as per normal behavior of stdio. So, something like this:
//
//   for (i = 0; i < 5; ++i) {
//      printf("%c", '1' + i);
//   }
//
// would output:
//
//   12345
//
// and not five separate log lines, which is the unbuffered behavior.
//
// Arguments:
//  size: The number of bytes to use for buffering. 0 sets unbuffered mode.
//        Default is 256 bytes.
//
// Returns:
//  0 on success, -1 if buffer allocation failed (nonfatal, buffer is unchanged)
int SetAndroidLogWrapperBufferSize(size_t size);

// Set the function called when these wrappers perform output. This defaults
// to __android_log_vprint(), which will cause the output to go to the Android
// log. You may intercept the output yourself by setting this function. Do not
// call any stdio output functions or use C++ std::cout/cerr from the function
// you set here, or infinite recursion will result.
//
// Arguments:
//  func: A function pointer of typedef AndroidLogOutputFunction to use for
//        stdio output.
void SetAndroidStdioOutputFunction(AndroidLogOutputFunction func);

// An internal function that will behave like a snprintf-based version of
// perror.  Used by __wrap_perror() and factored out/exposed to be testable.
//
// output should look equivalent to what you would expect for:
//
// sprintf(msgout, "%s: %s", msg, strerror(err));
// or
// strcpy(msgout, strerror(err));
//
// depending on the value of msg.
//
// Arguments:
//  msg: An optional message to prepend to the error to be printed.  May
//       be NULL.
//  err: The error value to be printed (via strerror).  Error value behavior is
//       the same as for strerror.
//  msgout: The output buffer. Must not be NULL.
//  outsize: The size of the memory pointed to by the output buffer. msgout
//           will be null-terminated to this length.
//
// Returns:
//  0 on success, -1 on error.
int AndroidPerrorMsg(const char *msg, int err, char *msgout, size_t outsize);

#if defined(__cplusplus)
} // extern "C"
#endif  // defined(__cplusplus)

#endif  // defined(ANDROID) || defined(__ANDROID__)
#endif  // FPLUTIL_PRINT_H
