Using libfplutil_print   {#libfplutil_print}
======================

`libfplutil_print` implements a set of wrappers for functions that write to
the standard output stream.  This enables applications that write to the
terminal using printf to have their output redirected to the Android log.

Using both `libfplutil_main` and `libfplutil_print` makes it possible to
compile and run non-interactive command line applications on Android devices.

It's possible to use `libfplutil_print` without `libfplutil_main` in
conjunction with [NativeActivity][] by implementing an `android_main` entry
point or using `printf` in libraries that are called from Java modules.
However, the typical use case is to use `libfplutil_print` in conjunction with
`libfplutil_main` so that C/C++ applications can easily be cross compiled
to multiple platforms including Android.

For example, the canonical C "Hello World" application will compile and run on
Android simply by linking with both `libfplutil_print` and `libfplutil_main`:

~~~{.c}
    #include <stdio.h>

    int main(int argc, char *argv[]) {
      printf("Hello World\n");
      return 0;
    }
~~~

The above application, when compiled and linked against `libfplutil_print` and
`libfplutil_main` (see [Linking][])
will print "Hello World" to the Android log which can be viewed using [adb][]'s
[logcat][] command.

# Customizing the Log Tag    {#libfplutil_print_tag}

By default, the tag used to annontate log messages is "main", this can be
modified using the `SetAndroidLogWrapperTag()` function.  For example:

~~~{.c}
    #include "fplutil/print.h"
    #include "fplutil/main.h"
    
    int main(int argc, char **argv) {
      SetAndroidLogWrapperTag("my_application");
      printf("Print to the log from printf\n");
      std::cout << "Print to the log from a stream" << std::endl;
      return 0;
    }
~~~

Prints the following to Android's log:

     Print to the log from printf
     Print to the log from a stream

All log messages from the application will be prefixed with the tag,
"my_application" so they can optionally extracted from [adb][] [logcat][] using

~~~{.sh}
     adb logcat -s "my_application"
~~~

In addition to changing the tag, it's possible to modify the log priority
`SetAndroidLogWrapperPriority()`.

# Configuring Buffering    {#libfplutil_print_buffering}

Each Android log message is terminated with a newline, so in order to simulate
printf behavior where newlines are explicit, `libfplutil_print` will buffer
messages up to 256 bytes before writing a line to the log.  The size of this
buffer can be modified using `SetAndroidLogWrapperBufferSize()`.

For example, after increasing the buffer size to 1KB, the following will print
a line longer than 256 bytes to a single log message:

~~~{.c}
    #include "fplutil/print.h"
    #include "fplutil/main.h"
    
    int main(int argc, char **argv) {
      SetAndroidLogWrapperBufferSize(1024);
      for (i = 0; i < 256; i++) {
        printf("*");
      }
      printf("A long line\n");
      return 0;
    }
~~~

# Redirecting Output {#libfplutil_print_redirection}

`libfplutil_print` captures all output to the standard output stream and by
default sends it to the Android log.  Applications can capture data sent
to the standard output stream and perform further processing before sending it
to the log.  This can be useful when logging to files or annotating log
messages with custom logic.

For example:

~~~{.c}
    #include <stdarg.h>
    #include "fplutil/print.h"
    #include "fplutil/main.h"
    
    int CaptureLog(int priority, const char *tag, const char *format,
                   va_list list) {
      // Do something with the message.
      return 0;
    }
    
    int main(int argc, char **argv) {
      SetAndroidStdioOutputFunction(CaptureLog);
      printf("A message to capture\n");
      return 0;
    }
~~~

<br>

  [adb]: http://developer.android.com/tools/help/adb.html
  [logcat]: http://developer.android.com/tools/help/logcat.html
  [Linking]: @ref libfplutil_linking
  [NativeActivity]: http://developer.android.com/reference/android/app/NativeActivity.html