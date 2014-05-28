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
#include <android/log.h>
#include <stdio.h>
#include <errno.h>
#include <pthread.h>
#include "AndroidLogPrint.h"

// Remove the redefinitions we did in the header.
#undef fflush
#undef perror
#undef printf
#undef vprintf

// The size of the buffer used to log printing from this module.
#if !defined(ANDROID_LOG_PRINTF_BUFFER_SIZE)
#define ANDROID_LOG_PRINTF_BUFFER_SIZE 1024
#endif  // !defined(ANDROID_LOG_PRINTF_BUFFER_SIZE)

// Synchronization to ensure thread safety and flushing on exit.
static pthread_once_t gOnce = PTHREAD_ONCE_INIT;
static pthread_mutex_t gLock = PTHREAD_MUTEX_INITIALIZER;

// Used to buffer data for android_vprintf().
static char gPrintfBuffer[ANDROID_LOG_PRINTF_BUFFER_SIZE];
// Current write offset into gPrintfBuffer.  This is always kept
// between 0 and sizeof(gPrintfBuffer) - 1 so the buffer can be null
// teminated.
static int gPrintfBufferOffset = 0;

// Global tag used for log output.
const char *gAndroidLogPrintfTag = ANDROID_LOG_PRINT_TAG_STRING;

// Flush the log buffer to the Android log stream. gLock must be held when
// this is called.
static void AndroidPrintfFlushInternal() {
  if (gPrintfBufferOffset) {
    gPrintfBuffer[gPrintfBufferOffset] = '\0';
    __android_log_print(ANDROID_LOG_PRINT_PRIORITY, gAndroidLogPrintfTag,
                        "%s", gPrintfBuffer);
    gPrintfBufferOffset = 0;
  }
}

// Externally visible flush function that handles locking itself.
int AndroidPrintfFlush(FILE *s) {
  int rc = 0;
  if (s == stdout || s == stderr) {
    pthread_mutex_lock(&gLock);
    AndroidPrintfFlushInternal();
    pthread_mutex_unlock(&gLock);
  } else {
    rc = fflush(s);
  }
  return rc;
}

// Atexit handler to flush the log line currently buffered.
static void AndroidPrintfCleanup() {
  pthread_mutex_lock(&gLock);
  AndroidPrintfFlushInternal();
  pthread_mutex_unlock(&gLock);
}

// Install the atexit handler.
static void AndroidPrintfInit() {
  pthread_mutex_lock(&gLock);
  atexit(AndroidPrintfCleanup);
  pthread_mutex_unlock(&gLock);
}
// Print to the log via a temporary buffer to workaround __android_log_print()
// adding a newline to the end of each printed string.
void AndroidVPrintf(const char *format, va_list arg) {
  // Set up our atexit handler and perform other initialization.
  pthread_once(&gOnce, AndroidPrintfInit);

  pthread_mutex_lock(&gLock);

  // Remaining space in the buffer excluding the null terminator.
  int remaining_space = sizeof(gPrintfBuffer) - (gPrintfBufferOffset + 1);
  // Try printing to the buffer.
  int written = vsnprintf(gPrintfBuffer + gPrintfBufferOffset,
                          remaining_space + 1, format, arg);
  // If the data was written to the buffer.
  if (written >= 0 && written <= remaining_space) {
    gPrintfBufferOffset += written;
    // Flush the buffer if it's full or terminates in a newline.
    if ((gPrintfBufferOffset &&
         gPrintfBuffer[gPrintfBufferOffset - 1] == '\n') ||
        (written == remaining_space)) {
      AndroidPrintfFlushInternal();
    }
  } else {
    // If the buffer was too small, flush it and try again.
    if (gPrintfBufferOffset) {
      AndroidPrintfFlushInternal();
      AndroidVPrintf(format, arg);
    } else {
      // String being printed is too big for the buffer, write directly to
      // the log.
      __android_log_vprint(ANDROID_LOG_PRINT_PRIORITY, gAndroidLogPrintfTag,
                           format, arg);
    }
  }

  pthread_mutex_unlock(&gLock);
}

// See AndroidVPrintf().
void AndroidPrintf(const char *format, ...) {
  va_list list;
  va_start(list, format);
  AndroidVPrintf(format, list);
  va_end(list);
}

// Wrapper around AndroidVPrinf().
int AndroidLogVPrint(int prio, const char *tag, const char *fmt, va_list ap) {
  AndroidVPrintf(fmt, ap);
  return 0;
}

// Wrapper around AndroidVPrintf().
int AndroidLogPrint(int prio, const char *tag,  const char *fmt, ...) {
  va_list list;
  va_start(list, fmt);
  AndroidVPrintf(fmt, list);
  va_end(list);
  return 0;
}

void AndroidPerrorMsg(const char *msg, int err, char *msgout, size_t outsize) {
  char errbuf[256];

  strerror_r(err, errbuf, sizeof(errbuf));

  if (msg) {
    snprintf(msgout, outsize, "%s: %s", msg, errbuf);
  } else {
    strncpy(msgout, errbuf, outsize);
  }
  msgout[outsize-1] = '\0';
}

void AndroidLogPerror(const char *message) {
  char errbuf[256];

  AndroidPerrorMsg(message, errno, errbuf, sizeof(errbuf));

  AndroidLogPrint(ANDROID_LOG_ERROR, gAndroidLogPrintfTag, "%s\n", errbuf);
}
