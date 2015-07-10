buildutil API Reference    {#buildutil_api_reference}
=======================

`buildutil` consists of the following modules:

   * [common.py][]
   * [android.py][]
   * [linux.py][]

The [common.py][] module implements functionality shared across multiple build
environments.

[android.py][] implements functions to build [Android][] projects, sign APKs,
deploy APKs to [Android][] devices and launch the built applications.

[linux.py][] implements functions to build applications using [CMake][] and
[make][] on Unix-like operating systems (e.g [Linux][] and [OSX][]).

Each module implements a [BuildEnvironment][] class which contains functions
to build for a specific build environment.

Each [BuildEnvironment][] class implements an [add_arguments][] which adds
a set of arguments to an [ArgumentParser][] instance.  The arguments parsed by
[ArgumentParser][] can be passed to a [BuildEnvironment][] on construction to
configure the instance.

After constructing a [BuildEnvironment][] instance, it's possible to build
projects for the selected build environment using methods like the following:

   * [run_make](@ref fplutil.buildutil.common.BuildEnvironment.run_make)
   * [run_cmake](@ref fplutil.buildutil.linux.BuildEnvironment.run_cmake)
   * [build_all](@ref fplutil.buildutil.android.BuildEnvironment.build_all)

  [ArgumentParser]: @ref argparse.ArgumentParser
  [BuildEnvironment]: @ref fplutil.buildutil.common.BuildEnvironment
  [add_arguments]: @ref fplutil.buildutil.common.BuildEnvironment.add_arguments
  [android.py]: @ref buildutil/android.py
  [common.py]: @ref buildutil/common.py
  [linux.py]: @ref buildutil/linux.py
  [Android]: http://www.android.com
  [make]: http://www.gnu.org/software/make
  [CMake]: http://www.cmake.org
  [Linux]: http://en.m.wikipedia.org/wiki/Linux
  [OSX]: http;//www.apple.com/osx
