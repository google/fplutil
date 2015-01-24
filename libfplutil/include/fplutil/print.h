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

#ifndef FPLUTIL_PRINT_H
#define FPLUTIL_PRINT_H

/// @file
/// Header for libfplutil_print.
///
/// libfplutil_print makes it easy to redirect writes to the standard output
/// stream to the Android log.

#if defined(ANDROID) || defined(__ANDROID__)

#include <android/log.h>
#include <stdarg.h>
#include <stdio.h>

#if defined(__cplusplus)
extern "C" {
#endif  // defined(__cplusplus)

/// This is the function signature to use if you would like to intercept
/// printf calls in your code. See SetAndroidLogOutputFunction().
///
/// The first two parameters to this function are the log priority and tag,
/// respectively. The remaining ones are the same as for the stdio function
/// vprintf(), and overall the expected semantics for this function are the
/// same as for vprintf(). Please see:
/// http://pubs.opengroup.org/onlinepubs/9699919799/functions/vfprintf.html
///
/// @param priority Android log priority.
/// @param tag Tag to display before the logged string.
/// @param format printf format string.
/// @param list Additional list of arguments referenced by the printf format
///             string.
typedef int (*AndroidLogOutputFunction)(int priority, const char *tag,
                                        const char *format, va_list list);

/// Set the tag used for log output by the wrappers.  This can used when
/// filtering the output of "adb logcat" to distinguish the log messages from
/// this application vs. other applications and the rest of the system.
/// Note that this pointer is simply assigned so it must have permanent
/// lifetime.
///
/// @param tag A null terminated C string to use as the log tag.
///            Default is "main".
///
/// @return 0 on success, -1 if tag is null or an empty string.
int SetAndroidLogWrapperTag(const char *tag);

/// Set the priority used for log output by the wrappers.
///
/// @param priority An android log priority, as described in the Android NDK
///                 header file android/log.h.  Default is ANDROID_LOG_INFO
///                 from that file.
void SetAndroidLogWrapperPriority(int priority);

/// Set the buffer size for the wrappers. Default is 256 bytes. Setting this to
/// zero will force unbuffered output, which may have unexpected formatting
/// such as additional newlines as text is immediately sent to the log. Nonzero
/// values will accumulate writes until a newline is encountered or the buffer
/// size is reached.
///
/// Buffering is done to allow multiple stdio calls to output on the same line,
/// as per normal behavior of stdio. So, something like this:
///
/// @code{.c}
///   for (i = 0; i < 5; ++i) {
///      printf("%c", '1' + i);
///   }
/// @endcode
///
/// would output:
///
/// @code{.c}
///   12345
/// @endcode
///
/// and not five separate log lines, which is the unbuffered behavior.
///
/// @param size The number of bytes to use for buffering. 0 sets unbuffered
///             mode. Default is 256 bytes.
///
/// @return 0 on success, -1 if buffer allocation failed (nonfatal, buffer is
/// unchanged)
int SetAndroidLogWrapperBufferSize(size_t size);

/// Set the function called when these wrappers perform output. This defaults
/// to __android_log_vprint(), which will cause the output to go to the Android
/// log. You may intercept the output yourself by setting this function. Do not
/// call any stdio output functions or use C++ std::cout/cerr from the function
/// you set here, or infinite recursion will result.
///
/// @param func A function pointer of typedef AndroidLogOutputFunction to use
///            for stdio output.
void SetAndroidStdioOutputFunction(AndroidLogOutputFunction func);

/// An internal function that will behave like a snprintf-based version of
/// perror.  Used by __wrap_perror() and factored out/exposed to be testable.
///
/// Output should look equivalent to what you would expect for:
///
/// @code{.c}
/// sprintf(msgout, "%s: %s", msg, strerror(err));
/// @endcode
///
/// or
///
/// @code{.c}
/// strcpy(msgout, strerror(err));
/// @endcode
///
/// depending on the value of msg.
///
/// @param msg An optional message to prepend to the error to be printed.
///            May be NULL.
/// @param err The error value to be printed (via strerror).  Error value
///            behavior is the same as for strerror.
/// @param msgout The output buffer. Must not be NULL.
/// @param outsize The size of the memory pointed to by the output buffer.
///                msgout will be null-terminated to this length.
///
/// @return 0 on success, -1 on error.
int AndroidPerrorMsg(const char *msg, int err, char *msgout, size_t outsize);

#if defined(__cplusplus)
}  // extern "C"
#endif  // defined(__cplusplus)

#endif  // defined(ANDROID) || defined(__ANDROID__)
#endif  // FPLUTIL_PRINT_H
