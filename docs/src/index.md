fplutil    {#fplutil}
=======

fplutil is a set of small libraries and tools that can be useful when
developing applications for Android and other platforms.

## C/C++ Libraries

[libfplutil][] consists of a set of libraries that make it easier to develop
C/C++ applications for Android:

   * `libfplutil_main` makes it easy to build traditional C/C++
     applications for Android that use an `int main()` entry point.
   * `libfplutil_print` transparently redirects `printf()` and other writes to
      the `stdout` stream to the Android log.

Using both `libfplutil_main` and `libfplutil_print` make it easy to take
existing C/C++ command line applications like tests and run them on Android
devices.

## Tools

`bin` contains a set of tools that can be useful when developing cross
platform applications that also target Android.  Currently this consists of:

   * [build_all_android.py][] which simplifies the process of building /
     installing / executing native (C/C++) applications on Android.
   * [android_ndk_perf.py][] native (C/C++) performance analysis tool for
     Android.

[build_all_android.py][] is an application that will find and build all native
(C/C++) Android applications within a specified directory.  Using this
application it's also possible to deploy and run Android applications to a set
of Android devices which makes it easy to use from a developer's workstation
or integrate with build automation systems.

[android_ndk_perf.py][] can be used to analyze the performance of native
(C/C++) applications.

## Python Build Modules

[buildutil][] contains a set of [Python][] modules which can simplify the
process of automating builds of C/C++ application for Android and Linux.

`autobuild` contains a build script for this suite of libraries and
`examples/buildutil_example` contains a demonstration build script.

## C/C++ Library Prerequisites

For Android functionality you must install the Android SDK and NDK,
available here:

   * http://developer.android.com/sdk/index.html
   * http://developer.android.com/tools/sdk/ndk/index.html

## Python Tools and Build Module Prerequisites

To use the Python scripts in this package you must first ensure you have a
Python version compatible with Python 2.7 installed on your system.

  [libfplutil]: @ref libfplutil_overview
  [buildutil]: @ref buildutil_overview
  [android_ndk_perf.py]: @ref android_ndk_perf
  [build_all_android.py]: @ref build_all_android
  [Python]: http://www.python.org

