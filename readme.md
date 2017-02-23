fplutil Version 1.1.0
=====================

# fplutil    {#fplutil_readme}

fplutil is a set of small libraries and tools that can be useful when
developing applications for Android and other platforms.

   * **build_all_android** is an all-in-one build script that allows you to
     build, install and run native (C/C++) Android apps from the command line.
     This is ideal for build automation, but can also be in a developer’s
     compile/run loop.
   * **buildutil** performs the configuration, build and archive steps
     of [Android][] and [Linux][] C/C++ applications using a suite of
     [Python][] modules.  This suite of modules can automate builds in a
     continuous integration environment.
   * **android_ndk_perf** is a desktop tool that enables native (C/C++)
     developers to measure the CPU utilization of their applications on
     [Android][], guiding their optimization efforts.
   * **libfplutil** enables C/C++ developers to write traditional applications
     (like [Hello World][]) using "main()" and "printf()" on [Android][].

Goto fplutil's [landing page][] for documentation.

   * Discuss fplutil with other developers and users on the
     [fplutil Google Group][].
   * File issues on the [fplutil Issues Tracker][]
     or post your questions to [stackoverflow.com][] with a mention of
     **fplutil**.

**Important**: fplutil uses submodules to reference other components it depends
upon so to download the source use:

    git clone --recursive https://github.com/google/fplutil.git

To contribute to this project see [CONTRIBUTING][].

For applications on Google Play that integrate these libraries, usage is
tracked.  This tracking is done automatically using the embedded version string
(kFplUtilVersionString). Aside from consuming a few extra bytes in your
application binary, it shouldn't affect your application at all. We use this
information to let us know if fplutil libraries are useful and if we should
continue to invest in them. Since this is open source, you are free to remove
the version string but we would appreciate if you would leave it in.

  [Android]: http://www.android.com
  [Linux]: http://en.m.wikipedia.org/wiki/Linux
  [Python]: http://www.python.org
  [fplutil Google Group]: https://groups.google.com/forum/#!forum/fplutil
  [fplutil Issues Tracker]: http://github.com/google/fplutil/issues
  [stackoverflow.com]: http://stackoverflow.com/search?q=fplutil
  [landing page]: http://google.github.io/fplutil
  [Hello World]: http://en.wikipedia.org/wiki/%22Hello,_world!%22_program
  [CONTRIBUTING]: http://github.com/google/fplutil/blob/master/CONTRIBUTING
