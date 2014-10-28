buildutil    {#buildutil_overview}
=========

`buildutil` contains a set of [Python][] modules which can simplify the process
of automating builds of C/C++ applications for [Android][] and [Linux][].

Many builds require the following steps to be performed:
   * Configuration
   * Build
   * Archive of artifacts

Some build environments - like [autoconf][], [automake][] and [make][] -
require each of these steps to be executed manually, others - like [CMake][] -
perform the configuration step and generate scripts that are executed as part
of another build environment.  Artifact collection can be part of the build
scripts (e.g make install) or part of the continuous automation system
depending upon the build environment.

`buildutil` provides a set of modules that simplify the process of writing
continuous automation scripts that use [CMake][] to support [Linux][],
[OSX][] and [Windows][] in addition to [Ant][] and [NDK Build][] for
[Android][].  This allows developers to write cross-platform turnkey scripts
that are trivial to execute from a continuous automation system like
[Jenkins][], [Buildbot][], [Travis-CI][] etc.

In order to use this module, all [prerequisites](@ref fplutil_prerequisites)
should be installed.

For more information about this module see the following:

   * [Example](@ref buildutil_examples_android) of building an Android
     application using `buildutil`.
   * [Example](@ref buildutil_examples_linux) of building a Linux
     application using `buildutil`.
   * [Common](@ref buildutil/common.py), [Android](@ref buildutil/android.py)
     and [Linux](@ref buildutil/linux.py) API reference.

  [Android]: http://www.android.com
  [Ant]: http://ant.apache.org
  [Buildbot]: http://www.buildbot.net
  [CMake]: http://www.cmake.org
  [Jenkins]: htttp://www.jenkins-ci.org
  [Linux]: http://en.m.wikipedia.org/wiki/Linux
  [NDK Build]: http://developer.android.com/tools/sdk/ndk/index.html
  [OSX]: http://www.apple.com/osx
  [Travis-CI]: http://www.travis-ci.org
  [Windows]: http://windows.microsoft.com
  [autoconf]: http://www.gnu.org/software/autoconf
  [automake]: http://www.gnu.org/software/automake
  [make]: http://www.gnu.org/software/make
  [Python]: http://www.python.org
