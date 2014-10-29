Using libfplutil_main   {#libfplutil_main}
=====================

`libfplutil_main` implements an Android [NativeActivity][] entry point
`android_main()` which calls the traditional C/C++ entry point `int main()`.
This makes it possible to write an application with a `int main()` entry point
(just like any standard C application), link against this library
(see [Linking][]) and have it run on Android.

For example, the following prints "Hello World" to the Android log:

~~~{.c}
    #include <android/log.h>
    
    int main(int argc, char *argv[]) {
      __android_log_print(ANDROID_LOG_VERBOSE, "test", "Hello World");
      return 0;
    }
~~~

# Event Processing # {#libfplutil_main_events}

Android applications must process system events otherwise they trigger an
"Application Not Responding" dialog ([ANR][]) which prompts the user to
close the application.  For long running tasks the `ProcessAndroidEvents()`
function makes it easy to process events and avoid the [ANR][] dialog.

For example:

~~~{.c}
    #include <android/log.h>
    
    int main(int argc, char *argv[]) {
      int complete = 0;
      __android_log_print(ANDROID_LOG_VERBOSE, "test", "Long running task...");
      while (!complete) {
        // Performing part of a task that takes a long time, set "complete"
        // when finished.
        // Process events to avoid ANR.
        ProcessAndroidEvents(0);
      }
      __android_log_print(ANDROID_LOG_VERBOSE, "test", "Task complete!");
      return 0;
    }
~~~

<br>

  [ANR]: http://developer.android.com/training/articles/perf-anr.html
  [Linking]: @ref libfplutil_linking
  [NativeActivity]: http://developer.android.com/reference/android/app/NativeActivity.html