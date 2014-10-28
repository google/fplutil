build_all_android.py    {#build_all_android}
====================

[build_all_android.py][] is an all-in-one build script that allows you to
build, install and run native (C/C++) Android apps from the command line.
This is ideal for build automation, but can also be in a developer’s
compile/run loop.

In order to use this tool, all [prerequisites](@ref fplutil_prerequisites)
should be installed.

# Building Applications    {#build_all_android_build}

By default [build_all_android.py][] will build all Android projects under the
current working directory.  For example, from the command line, the following
will change into the [fplutil][] directory and build all Android projects:

~~~{.sh}
    cd fplutil
    ./bin/build_all_android.py
~~~

The application will place the build artifacts in the following locations:

   * APKs in `fplutil/apks`
   * Shared (.so) and Static (.a) libraries in `fplutil/libs`.

The following files are produced when building all Android targets in
[fplutil][]:

~~~~
    apks/example-release-unsigned.apk
    apks/tests-release-unsigned.apk
~~~~

# Signing Applications    {#build_all_android_sign}

In order to install a release APK on a device it must be signed.  By default
[build_all_android.py][] build but not sign release APKs.  The `-S` or
`--sign_apk` flag will enable signing of APKs.

For example, the following will build and sign all APKs with a temporary key:

~~~{.sh}
    cd fplutil
    ./bin/build_all_android.py -S
~~~

In a similar fashion to unsigned APKs, signed APKs are placed in the apks
directory.  Signed APK names do not end in `-unsigned.apk`.

~~~{.sh}
    apks/example-release-unsigned.apk
    apks/example.apk
    apks/tests-release-unsigned.apk
    apks/tests.apk
~~~

TODO: Describe signing with a real key

# Installing Applications    {#build_all_android_install}

Using the `-i` or `--apk_install` flag, [build_all_android.py][] can install
applications to one or more devices attached to a workstation.

For example, the following will build all Android applications in [fplutil][],
sign the APKs and install them to an attached device:

~~~{.sh}
    cd fplutil
    ./bin/build_all_android.py -S -i
~~~

# Running Applications    {#build_all_android_run}

[build_all_android.py][] will run applications on an attached Android device
when the `-r` or `--apk_run` flag is specified.

For example, the following will build all Android applications in [fplutil][],
sign the APKs, install them to an attached device and then execute them in
sequence:

~~~{.sh}
    cd fplutil
    ./bin/build_all_android.py -S -i -r
~~~

# Build Configuration    {#build_all_android_build_config}

By default [build_all_android.py][] will build all applications in `release`
mode.  It's possible to select the `debug` with the `-T` or `--ant_target`
flag.

For example, the following will build all [fplutil][] applications in debug
mode with no native (C/C++) symbols:

~~~{.sh}
    cd fplutil
    ./bin/build_all_android.py -T debug
~~~

In order to perform symbolic debugging of native (C/C++) components with
`ndk-gdb` `NDK_DEBUG=1` must be passed to `ndk-build`.  Arguments are passed to
`ndk-build` using the `-f` or `--make_flags` flag.

For example:

~~~{.sh}
    cd fplutil
    ./bin/build_all_android.py -T debug -f NDK_DEBUG=1
~~~

To force optimization in debug mode, set `NDK_DEBUG=0`.

~~~{.sh}
    cd fplutil
    ./bin/build_all_android.py -T debug -f NDK_DEBUG=0
~~~

# Cleaning Build Artifacts    {#build_all_android_clean}

Build artifacts can be cleaned using the `-c` or `--clean` flag.  For example:

~~~{.sh}
    ./bin/build_all_android.py -c
~~~

# Working with Multiple Devices    {#build_all_android_multiple_devices}

By default, [build_all_android.py][] will only install or run applications on
one connected device.  It's possible to select the set of devices using
`-d` followed by a list of device serial numbers or `@` which selects all
devices attached to the workstation.

For example, the following will build all Android applications in [fplutil][],
sign them, install and run them on all attached devices:

~~~{.sh}
    cd fplutil
    ./bin/build_all_android.py -S -i -r -d @
~~~

<br>

  [build_all_android.py]: @ref build_all_android
  [buildutil]: @ref buildutil_overview
  [fplutil]: index.html
