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

#include <android/log.h>
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/uio.h>
#include "fplutil/print.h"
#include "fplutil/version.h"

// Output function.
static AndroidLogOutputFunction g_output_function = __android_log_vprint;
// Logging output parameters for the wrapped functions.
static const char *g_wrapper_tag = "main";
static int g_wrapper_priority = ANDROID_LOG_INFO;
static const size_t DEFAULT_BUFSIZE = 256;
// Output buffering support.
static size_t g_wrapper_buffer_size = 0;
static char *g_print_buffer = NULL;
static size_t g_print_buffer_offset = 0;
// Synchronization to ensure thread safety and flushing on exit.
static pthread_once_t g_once = PTHREAD_ONCE_INIT;
static pthread_mutex_t g_lock = PTHREAD_MUTEX_INITIALIZER;
const char kFplUtilPrintVersionString[] = FPLUTIL_VERSION_STRING;

extern void AndroidPrintfCxxInit();

///////////////////////////////////////////////////////////////////////////
// Wrappers for stdio calls.
//
// All of these have the same semantics as their stdio.h counterparts.
int __wrap_printf(const char *format, ...);
int __wrap_fprintf(FILE *stream, const char *format, ...);
int __wrap_vprintf(const char *format, va_list ap);
int __wrap_fflush(FILE *stream);
int __wrap_fputc(int c, FILE *stream);
int __wrap_putc(int c, FILE *stream);
int __wrap_putchar(int c);
void __wrap_perror(const char *message);
int __wrap_puts(const char *s);
int __wrap_fputs(const char *s, FILE *f);
size_t __wrap_fwrite(const void *ptr, size_t size, size_t nmemb, FILE *stream);
ssize_t __wrap_write(int fd, const void *ptr, size_t count);
ssize_t __wrap_writev(int fd, const struct iovec *iov, int iovcnt);

// Resolved by linker to the actual function.
int __real_fflush(FILE *s);
size_t __real_fwrite(const void *ptr, size_t size, size_t nmemb, FILE *stream);
ssize_t __real_write(int fd, const void *ptr, size_t count);
ssize_t __real_writev(int fd, const struct iovec *iov, int iovcnt);

///////////////////////////////////////////////////////////////////////////
// Statics and helper functions.

// A helper to send normal log prints to the output function in addition to
// the wrapped calls calling __wrap_vprintf().
static int Output(const char *format, ...) {
  va_list list;
  int rc;
  va_start(list, format);
  rc = g_output_function(g_wrapper_priority, g_wrapper_tag, format, list);
  va_end(list);
  return rc;
}

// Flush the log buffer to the Android log stream. g_lock must be held when
// this is called.
static void FlushInternal() {
  if (g_print_buffer_offset) {
    assert(g_print_buffer);
    // Null terminate the buffer.
    g_print_buffer[g_print_buffer_offset] = '\0';
    // If the final char is a newline, trim it as it will be added again
    // by the android log.
    if (g_print_buffer[g_print_buffer_offset - 1] == '\n') {
      g_print_buffer[g_print_buffer_offset - 1] = 0;
    }
    // This conditional guards against empty-string writes and extra flushing
    // from std::endl.
    if (*g_print_buffer) {
      Output("%s", g_print_buffer);
    }
    g_print_buffer_offset = 0;
  }
}

// Atexit handler to flush the log line currently buffered.
static void AndroidPrintfCleanup() {
  // This call will flush and free the buffer.
  SetAndroidLogWrapperBufferSize(0);
}

// Install the atexit handler.
static void AndroidPrintfInit() {
  SetAndroidLogWrapperBufferSize(DEFAULT_BUFSIZE);
  pthread_mutex_lock(&g_lock);
  AndroidPrintfCxxInit();
  atexit(AndroidPrintfCleanup);
  pthread_mutex_unlock(&g_lock);
}

// Our perror() helper as described in android_print_util.h.
int AndroidPerrorMsg(const char *msg, int err, char *msgout, size_t outsize) {
  char errbuf[DEFAULT_BUFSIZE];

  if (!msgout || outsize == 0) {
    // Invalid arguments.
    return -1;
  }

  strerror_r(err, errbuf, sizeof(errbuf));

  if (msg) {
    snprintf(msgout, outsize, "%s: %s", msg, errbuf);
  } else {
    strncpy(msgout, errbuf, outsize);
  }
  msgout[outsize-1] = '\0';
  return 0;
}

///////////////////////////////////////////////////////////////////////////
// Wrappers for stdio functions.

// Wrap perror() to output to the Android log.
void __wrap_perror(const char *message) {
  char errbuf[DEFAULT_BUFSIZE];

  AndroidPerrorMsg(message, errno, errbuf, sizeof(errbuf));
  Output("%s", errbuf);
}

// Wrap printf() to output to the Android log.
int __wrap_printf(const char *format, ...) {
  va_list list;
  int rc;
  va_start(list, format);
  rc = __wrap_vprintf(format, list);
  va_end(list);
  return rc;
}

// Wrap fputc() in terms of __wrap_fprintf().
int __wrap_fputc(int c, FILE *stream) {
  int rc = __wrap_fprintf(stream, "%c", c);
  if (rc < 0) {
    return EOF;
  }
  return c;
}

// Wrap putc() in terms of __wrap_fputc(), in case it is not a macro.
int __wrap_putc(int c, FILE *stream) {
  return __wrap_fputc(c, stream);
}

// Wrap puts() in terms of __wrap_fputs(), in case it is not a macro.
int __wrap_puts(const char *s) {
  return __wrap_fputs(s, stdout);
}

// Wrap fputs() in terms of __wrap_fprintf().
int __wrap_fputs(const char *s, FILE *stream) {
  return __wrap_fprintf(stream, "%s", s);
}

// Wrap putc() in terms of __wrap_fputc(), in case it is not a macro.
int __wrap_putchar(int c) {
  return __wrap_fputc(c, stdout);
}

// Wrap fprintf() to output to the Android log.
//
// If the stream is not stdout or stderr, call the real fprintf().
int __wrap_fprintf(FILE *stream, const char *format, ...) {
  va_list list;
  int rc = -1;
  if (stream == stdout || stream == stderr) {
    va_start(list, format);
    rc = __wrap_vprintf(format, list);
    va_end(list);
  } else {
    va_start(list, format);
    rc = vfprintf(stream, format, list);
    va_end(list);
  }
  return rc;
}

// Wrap fwrite() to output to the Android log, implemented in terms
// of __wrap_write().
//
// If the stream is not stdout or stderr, call the real fwrite().
size_t __wrap_fwrite(const void *ptr, size_t size, size_t nmemb,
                     FILE *stream) {
  ssize_t rc = 0;

  if (stream == stdout || stream == stderr) {
    size_t bytes = size * nmemb;
    rc = __wrap_write(fileno(stream), ptr, bytes);
    // fwrite() should return the number of members written, so
    // return (total bytes / member size), or 0 on write error.
    if (rc < 0) {
      rc = 0;
    } else {
      rc /= size;
    }
  } else {
    rc = __real_fwrite(ptr, size, nmemb, stream);
  }
  return rc;
}

// Wrap write() to output to the Android log.
//
// If the stream is not stdout or stderr, call the real write().
ssize_t __wrap_write(int fd, const void *ptr, size_t count) {
  int rc = -1;
  if (fd == fileno(stdout) || fd == fileno(stderr)) {
    // Copy required because we need to null terminate, and also things like
    // this are a valid use case:
    //   write(1, "shorter than my null terminated len", 7);
    // which would be expected to only write "shorter".
    char buf[DEFAULT_BUFSIZE];
    const size_t maxcpy = sizeof(buf) - 1;
    const char *c = (const char *)ptr;
    size_t left = count;

    while (left) {
      size_t copy = left > maxcpy ? maxcpy : left;
      memcpy(buf, c, copy);
      c += copy;
      left -= copy;
      buf[copy] = '\0';
      __wrap_puts(buf);
    }
    rc = count;
  } else {
    rc = __real_write(fd, ptr, count);
  }
  return rc;
}

// Wrap writev() to output to the Android log, in terms of write().
//
// If the stream is not stdout or stderr, call the real writev().
ssize_t __wrap_writev(int fd, const struct iovec *iov, int iovcnt)
{
  ssize_t rc = 0;

  if (fd == fileno(stdout) || fd == fileno(stderr)) {
    int i;
    for (i = 0; i < iovcnt; ++i) {
      const struct iovec *vec = iov + i;
      const ssize_t written = __wrap_write(fd, vec->iov_base, vec->iov_len);
      if (written < 0) {
        rc = -1;
        break;
      }
      rc += written;
    }
  } else {
    rc = __real_writev(fd, iov, iovcnt);
  }
  return rc;
}

// Wrap vprintf() to output to the Android log.
//
// Also provide optional buffering. All other wrappers are implemented in
// terms of this call, eventually.
int __wrap_vprintf(const char *format, va_list arg) {
  int rc = -1;
  // Set up our atexit handler and perform other initialization.

  pthread_once(&g_once, AndroidPrintfInit);
  pthread_mutex_lock(&g_lock);
  // If we are not buffered, call directly.
  if (g_wrapper_buffer_size == 0) {
    rc = g_output_function(g_wrapper_priority, g_wrapper_tag, format, arg);
  } else {
    // Need to copy the arg list pointer because vsnprintf may consume part
    // of it and fail, in which case we need to have a copy to output directly
    // since the arg pointer is undefined after the call to vsnprintf.
    va_list arg_copy;
    va_copy(arg_copy, arg);

    // Remaining space in the buffer excluding the null terminator.
    int remaining_space = g_wrapper_buffer_size - (g_print_buffer_offset + 1);
    // Try printing to the buffer.
    int written = vsnprintf(g_print_buffer + g_print_buffer_offset,
                            remaining_space + 1, format, arg);
    // If the data was written to the buffer.
    if (written >= 0 && written <= remaining_space) {
      g_print_buffer_offset += written;
      // Flush the buffer if it's full or terminates in a newline.
      if ((g_print_buffer_offset &&
          g_print_buffer[g_print_buffer_offset - 1] == '\n') ||
          (written == remaining_space)) {
        FlushInternal();
      }
      rc = written;
    } else {
      // If the buffer was too small, flush it and write directly.
      if (g_print_buffer_offset) {
        FlushInternal();
      }
      // String being printed is too big for the buffer, write directly to
      // the log. Use arg_copy as arg is now undefined.
      rc = g_output_function(g_wrapper_priority, g_wrapper_tag, format,
                                  arg_copy);

    }
    // finished with our copy
    va_end(arg_copy);
  }
  pthread_mutex_unlock(&g_lock);
  return rc;
}

// Wrap fflush() to flush to the Android log.
//
// If the stream being flushed is not stdout or stderr, call the real fflush().
int __wrap_fflush(FILE *s) {
  int rc = 0;
  if (s == stdout || s == stderr) {
    pthread_mutex_lock(&g_lock);
    FlushInternal();
    pthread_mutex_unlock(&g_lock);
  } else {
    // The linker will resolve this symbol to the real call.
    rc = __real_fflush(s);
  }
  return rc;
}

///////////////////////////////////////////////////////////////////////////
// Accessors and setters.

int SetAndroidLogWrapperTag(const char *tag) {
  int rc = -1;
  if (tag && *tag) {
    pthread_mutex_lock(&g_lock);
    g_wrapper_tag = tag;
    pthread_mutex_unlock(&g_lock);
    rc = 0;
  }
  return rc;
}

void SetAndroidLogWrapperPriority(int prio) {
  pthread_mutex_lock(&g_lock);
  g_wrapper_priority = prio;
  pthread_mutex_unlock(&g_lock);
}

int SetAndroidLogWrapperBufferSize(size_t size) {
  int rc = 0;
  pthread_mutex_lock(&g_lock);
  // Flush if we would lose data.
  if (size < g_print_buffer_offset) {
    FlushInternal();
  }
  char *tmp = (char *)realloc(g_print_buffer, size);
  if (size == 0) {
    // The call to realloc freed the buffer.
    g_print_buffer = NULL;
    g_wrapper_buffer_size = 0;
  } else if (tmp) {
    // Realloc succeeded.
    g_print_buffer = tmp;
    g_wrapper_buffer_size = size;
  } else {
    // Buffer is unchanged but report the realloc failure.
    rc = -1;
  }
  pthread_mutex_unlock(&g_lock);
  return rc;
}

void SetAndroidStdioOutputFunction(AndroidLogOutputFunction func) {
  pthread_mutex_lock(&g_lock);
  g_output_function = func ? func : __android_log_vprint;
  pthread_mutex_unlock(&g_lock);
}
