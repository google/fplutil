Prerequisites    {#fplutil_prerequisites}
=============

The follow sections describe how to install the packages required to use
**fplutil** libraries and tools.

# Android SDK    {#fplutil_install_sdk}

## Linux    {#fplutil_install_sdk_linux}

Download and install:

   * [Android SDK][], required to build Android applications.<br/>
     Download the latest [Android SDK][] and unpack it to a directory on your
     machine.
   * [Java 1.7][] required to use Android tools.
        * For example, on systems that support apt-get...<br/>
          `sudo apt-get install jdkTODO`
   * [Apache Ant][], required to build Android applications with [fplutil][].
        * For example, on systems that support `apt-get`...<br/>
          `sudo apt-get install ant`

## OSX / Windows    {#fplutil_install_sdk_osx_windows}

Download and install:

   * [Android SDK][], required to build Android applications.<br/>
     Download the latest [Android SDK][] package and unpack to a directory on
     your machine.
   * [Java 1.7][], required to use Android tools.<br/>
     Download the [Java 1.7][] installer and run it to install.
   * [Apache Ant][], required to build Android applications with
     [fplutil][].<br/>
     Download the latest version of [Apache Ant][] and unpack it to a
     directory.

# Android NDK    {#fplutil_install_ndk}

Download and install:

   * [Android NDK][], required to develop Android native (C/C++)
     applications.<br/>
     Download and unpack the latest version of the [Android NDK][] to a
     directory on your machine.

# Python    {#fplutil_install_python}

## Linux    {#fplutil_install_python_linux}

Download and install:

   * [Python 2.7][], required to use [fplutil][] tools.<br/>
     For example, on a systems that support `apt-get`...<br/>
     `sudo apt-get install python`

## OSX / Windows    {#fplutil_install_python_osx_windows}

Download and install:

   * [Python 2.7][], required to use [fplutil][] tools.<br/>
     Download the latest package from the [Python 2.7][] page and run the
     installer.

# Configure the Command Line Environment    {#fplutil_command_line}

## Linux    {#fplutil_command_line_linux}

   * Add the `sdk/tools` directory from the [Android SDK][] installation
     directory to the [PATH variable][].
        * For example, if the [Android SDK][] is installed in
         `/home/androiddev/adt` the following line should be added
          to user's bash resource file `~/.bashrc`.<br/>
          `export PATH="$PATH:/home/androiddev/android-adt/sdk/tools"`
   * Add the [Android NDK][] directory to the [PATH variable][].
        * For example, if the [Android NDK][] is installed in
          `/home/androiddev/ndk` the following line should be added to the
          user's bash resource file `~/.bashrc`.<br/>
          `export PATH="$PATH:/home/androiddev/android-ndk"`
   * Make sure [Java 1.7][] is selected in the event multiple Java versions
     are installed on the system.  For example, on Ubunutu run
     `update-java-alternatives` to select the correct Java version.

## OSX    {#fplutil_command_line_osx}

   * Add the `sdk/tools` directory from the [Android SDK][] installation
     directory to the [PATH variable][].
        * For example, if the [Android SDK][] is installed in
          `/home/androiddev/adt` the following line should be added to user's
          bash resource file `~/.bashrc`.<br/>
          `export PATH="$PATH:/home/androiddev/android-adt/sdk/tools"`
   * Add the [Android NDK][] directory to the [PATH variable][].
        * For example, if the [Android NDK][] is installed in
          `/home/androiddev/ndk` the following line should be added to the
          user's bash resource file `~/.bashrc`.<br/>
         `export PATH="$PATH:/home/androiddev/android-ndk"`
   * Add the [Apache Ant][] install directory to the [PATH variable][].
       * For example, if [Apache Ant][] is installed in
         `/home/androiddev/apache-ant`, the following line should be added to
         the user's bash resource file `~/,basrhc`.<br/>
         `export PATH="$PATH:/home/androiddev/apache-ant"`

## Windows    {#fplutil_command_line_windows}

See [Setting Windows Environment Variables][].

   * Add the `sdk\tools` directory from the [Android SDK][] installation
     directory to the [PATH variable][].
        * For example, if the [Android SDK][] is installed in
         `c:\android-adt`, the path `c:\android-adt\sdk\tools`
          should be added to the [PATH variable][].
   * Add the [Android NDK][] directory to the [PATH variable][].
        * For example, if the [Android NDK][] is installed in `c:\android-ndk`,
          the path `c:\android-ndk` should be added to the [PATH variable][].

  [Android NDK]: http://developer.android.com/tools/sdk/ndk/index.html
  [Android SDK]: http://developer.android.com/sdk/index.html
  [Apache Ant]: https://www.apache.org/dist/ant/binaries/
  [Java 1.7]: http://www.oracle.com/technetwork/java/javase/downloads/jdk7-downloads-1880260.html
  [PATH variable]: http://en.wikipedia.org/wiki/PATH_(variable)
  [Python 2.7]: https://www.python.org/download/releases/2.7/
  [Setting Windows Environment Variables]: http://www.computerhope.com/issues/ch000549.htm
