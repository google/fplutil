fplutil version 1.0    {#fplutil_readme}
===================

# FPL Utilities

fplutil is a set of small libraries and tools that can be useful when
developing applications for Android and other platforms.

   * [build_all_android.py][] is a tool simplifies the process of building /
     installing / executing native (C/C++) applications on Android.
   * [buildutil][] contains a set of [Python][] modules which can simplify the
     process of automating builds of C/C++ application for Android and Linux.
   * [android_ndk_perf.py][] is a tool which makes it easier to profile
     native (C/C++) applications on Android.
   * [libfplutil][] consists of a set of libraries that make it easier to
     develop C/C++ applications for Android.


For applications on Google Play that integrate these libraries, usage is
tracked.  This tracking is done automatically using the embedded version string
(kFplUtilVersionString). Aside from consuming a few extra bytes in your
application binary, it shouldn't affect your application at all. We use this
information to let us know if fplutil libraries are useful and if we should
continue to invest in them. Since this is open source, you are free to remove
the version string but we would appreciate if you would leave it in.

  [android_ndk_perf.py]: @ref android_ndk_perf
  [build_all_android.py]: @ref build_all_android
  [buildutil]: @ref buildutil_overview
  [libfplutil]: @ref libfplutil_overview
  [Python]: http://www.python.org