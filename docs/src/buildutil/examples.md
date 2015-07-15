Examples    {#buildutil_examples}
========

# Android    {#buildutil_examples_android}

The [android](@ref buildutil/android.py) module contains functions that make
it easy to build, deploy and run Android applications.

For reference the complete source is in
[examples/buildutil/android.py](@ref buildutil_examples_android_code).

The following code parses arguments to the script and creates an
[android.BuildEnvironment](@ref fplutil.buildutil.android.BuildEnvironment)
instance which is used to perform Android specific build operations...

~~~{.py}
parser = argparse.ArgumentParser()
buildutil.android.BuildEnvironment.add_arguments(parser)
args = parser.parse_args()

env = buildutil.android.BuildEnvironment(args)
~~~

The following code then copies the NDK `native-plasma` sample to the example
directory...

~~~{.py}
samplename = 'native-plasma'
samplepath = os.path.join(env.ndk_home, 'samples', samplename)
shutil.rmtree(samplename, True)
shutil.copytree(samplepath, samplename)
~~~

The `native-plasma` application is built using `ndk-build` to build the native
(C/C++) component and `ant` to build the Java component and APK...

~~~{.py}
(rc, errmsg) = env.build_all()
~~~

Finally, the resultant APK is archived in a zip file...

~~~{.py}
env.make_archive(['apks'], 'output.zip', exclude=['objs', 'objs-debug'])
~~~

# Linux    {#buildutil_examples_linux}

The [linux](@ref buildutil/linux.py) module contains functions that make it
easy to build applications that use [cmake][] in conjunction with the [make][]
generator for Unix-like operating systems (e.g [Linux][] and [OSX][]).

For reference the complete source is in
[examples/buildutil/linux.py](@ref buildutil_examples_linux_code).

The following code, parses arguments to the script and creates an
[linux.BuildEnvironment](@ref fplutil.buildutil.linux.BuildEnvironment)
instance which is used to perform Linux specific build operations...

~~~{.py}
parser = argparse.ArgumentParser()
buildutil.linux.BuildEnvironment.add_arguments(parser)
args = parser.parse_args()

env = buildutil.linux.BuildEnvironment(args)
~~~

The example application prints the preprocessor `MESSAGE` to the standard
output stream.  So this is passed as a flag to [CMake][]...

~~~{.py}
env.cmake_flags = '-DMESSAGE="Hello, World!"'
~~~

The application is built by running [CMake][] followed by [make][]...

~~~{.py}
env.run_cmake()
env.run_make()
~~~

Finally, the build artifacts are archived in a zip file called `output.zip`...

~~~{.py}
env.make_archive(['Hello'], 'output.zip')
~~~

<br>

  [make]: http://www.gnu.org/software/make
  [CMake]: http://www.cmake.org
  [Linux]: http://en.m.wikipedia.org/wiki/Linux
  [OSX]: http://www.apple.com/osx
