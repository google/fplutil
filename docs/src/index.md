fplutil    {#fplutil}
=======

fplutil is a set of small libraries and tools that can be useful when
developing applications for Android and other platforms.

Download the latest release from the
[fplutil github page](http://github.com/google/fplutil) or the
[releases page](https://github.com/google/fplutil/releases).

**Important**: fplutil uses submodules to reference other components it depends
upon so to download the source use:

~~~{.sh}
    git clone --recursive https://github.com/google/fplutil.git
~~~

   * Discuss fplutil with other developers and users on the
     [fplutil Google Group][].
   * File issues on the [fplutil Issues Tracker][]
     or post your questions to [stackoverflow.com][] with a mention of
     **fplutil**.

Before getting started, make sure all
[prerequisites](@ref fplutil_prerequisites) are installed and configured.

# Components

   * [build_all_android][] is an all-in-one build script that allows you to
     build, install and run native (C/C++) Android apps from the command line.
     This is ideal for build automation, but can also be in a developer’s
     compile/run loop.
   * [buildutil][] performs the configuration, build and archive steps
     of [Android][] and [Linux][] C/C++ applications using a suite of
     [Python][] modules.  This suite of modules can automate builds in a
     continuous integration environment.
   * [android_ndk_perf][] is a desktop tool that enables native (C/C++)
     developers to measure the CPU utilization of their applications on
     [Android][], guiding their optimization efforts.
   * [libfplutil][] enables C/C++ developers to write traditional applications
     (like [Hello World][]) using "main()" and "printf()" on [Android][].

  [Android]: http://www.android.com
  [Linux]: http://en.m.wikipedia.org/wiki/Linux
  [Python]: http://www.python.org
  [android_ndk_perf]: @ref android_ndk_perf
  [build_all_android]: @ref build_all_android
  [buildutil]: @ref buildutil_overview
  [fplutil Google Group]: http://groups.google.com/group/fplutil
  [fplutil Issues Tracker]: http://github.com/google/fplutil/issues
  [fplutil]: index.html
  [libfplutil]: @ref libfplutil_overview
  [stackoverflow.com]: http://stackoverflow.com/search?q=fplutil
  [Hello World]: http://en.wikipedia.org/wiki/%22Hello,_world!%22_program
