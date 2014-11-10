Example    {#libfplutil_example}
=======

`examples/libfplutil_example` is a sample application which prints
"Hello World" to the Android log.  It's as possible to compile the application
for other platforms and see "Hello World" printed to the standard output
stream.

The following sections will describe:

   * Setting up the build environment.
   * Building the sample.
   * Installing the sample.
   * Running the sample.

# Before Getting Started    {#libfplutil_example_preparation}

   * Install the [Android SDK][].
   * Install the [Android NDK][].
   * Install [Python][] (optionally required to build with fplutil's build
     tools).

# Build, Install and Run with fplutil    {#libfplutil_example_build_fplutil}

Building, installing and running the application using fplutil's build tool
consists of the following steps:

   * Open a command line.
   * Change into the example directory.
   * Run [fplutil][]'s [build_all_android][]

For example, the following will build the application APK in debug, install
the APK on an attached Android device and execute the application:

~~~{.sh}
    cd examples/libfplutil_example
    ../../bin/build_all_android -T debug -i -r
~~~

Which should display:

    --------- beginning of /dev/log/main
    --------- beginning of /dev/log/system
    I/main    (  550): Hello, World!

# Building manually with ndk-build    {#libfplutil_example_build_ndkbuild}

The following steps *only* need to be performed if [build_all_android][]
isn't sufficient for your build environment.

To build the shared library that constitutes the native component of the
application:

   * Open a terminal.
   * Change into the example directory.
   * Run ndk-build.

For example:

~~~{.sh}
    cd examples/libfplutil_example
    ndk-build
~~~

## Packaging the Application

This will create a shared library in the `libfplutil_example/libs` directory
which needs to be packaged into an APK before it can be deployed to a device.
To do this you need to:

   * Create an [Android Ant][] project.
   * Build a *debug* APK to avoid the [APK Signing] step.

For example, the following generates a project to build against
[Android API Level][] 18 and builds an APK:

~~~{.sh}
    android update project --path . --target android-18 --name libfplutil_example
    ant debug
~~~

This results in the application's APK in `bin/libfplutil_example-debug.apk`.

## Deploying the Application

To run this application:

   * Deploy the APK to an Android device.
   * Run the application on the Android device.

For example:

~~~{.sh}
    adb install bin/libfplutil_example-debug.apk
    adb shell am start -S -n com.google.fpl.libfplutil.example/android.app.NativeActivity
~~~

## Running the Application

Finally, it's possible to view the application's output using `adb logcat`:

~~~{.sh}
    adb logcat -s main
~~~

Which should display:

    --------- beginning of /dev/log/main
    --------- beginning of /dev/log/system
    I/main    (  550): Hello, World!

<br>

  [fplutil]: index.html
  [Python]: http://www.python.org
  [Android Ant]: http://developer.android.com/tools/building/building-cmdline.html
  [Android NDK]: http://developer.android.com/tools/sdk/ndk/index.html
  [Android SDK]: http://developer.android.com/sdk/index.html
  [APK Signing]: http://developer.android.com/tools/publishing/app-signing.html
  [Android API Level]: http://developer.android.com/guide/topics/manifest/uses-sdk-element.html#ApiLevels
  [build_all_android]: @ref build_all_android
