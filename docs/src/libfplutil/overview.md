libfplutil Overview    {#libfplutil_overview}
===================

[libfplutil][] enables C/C++ developers to write traditional applications
(like [Hello World][]) using "main()" and "printf()" on [Android][].

[libfplutil][] consists of a native (C/C++) [Android NDK][] module that builds
the following static libraries:

   * [libfplutil_main][]
   * [libfplutil_print][]

As mentioned in the [fplutil package description][], these libraries ease the
development of C/C++ applications for Android.

## Before Reading On

In order to use this module, all [prerequisites](@ref fplutil_prerequisites)
should be installed and you should already be familiar with C/C++,
the [Android NDK][] and [adb][].

## Contents

For more information about this module see the following:

   * [libfplutil_main][] description and use cases.
   * [libfplutil_print][] description and use cases.
   * An [example](@ref libfplutil_example) which demonstrates how to use
     [libfplutil_main][] and [libfplutil_print][] in an application.
   * An [API reference](@ref libfplutil/include/fplutil/main.h) for
     [libfplutil_main][]
   * An [API reference](@ref libfplutil/include/fplutil/print.h) for
     [libfplutil_print][]

  [Android]: http://www.android.com
  [adb]: http://developer.android.com/tools/help/adb.html
  [libfplutil]: @ref libfplutil_overview
  [Android NDK]: http://developer.android.com/tools/sdk/ndk/index.html
  [libfplutil_main]: @ref libfplutil_main
  [libfplutil_print]: @ref libfplutil_print
  [fplutil package description]: index.html
  [Linking]: #libfplutil_linking
  [ANR]: http://developer.android.com/training/articles/perf-anr.html
  [Android SDK]: http://developer.android.com/sdk/index.html
  [NativeActivity]: http://developer.android.com/reference/android/app/NativeActivity.html
  [Hello World]: http://en.wikipedia.org/wiki/%22Hello,_world!%22_program