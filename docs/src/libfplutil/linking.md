Linking Applications with libfplutil    {#libfplutil_linking}
====================================

By default the linker will not link an application against `libfplutil_main`
or `libfplutil_print` as the application will not typically reference symbols
in the libraries.  Therefore the linker must be instructed to *always* link
against the libraries.  This can be achieved by using:

   * `LOCAL_WHOLE_STATIC_LIBRARIES` when using [Android NDK][] makefiles.
   * `--whole-archive` linker flag when directly using the compiler toolchain.

For example, a build target in an [Android NDK][] makefile which builds an
application that links against both `libfplutil_main` and `libfplutil_print`
may look like this:

~~~{.mk}
    include $(CLEAR_VARS)
    LOCAL_MODULE:=myapp
    LOCAL_SRC_FILES:=$(LOCAL_PATH)/main.c
    LOCAL_WHOLE_STATIC_LIBRARIES:=android_native_app_glue libfplutil_main \
        libfplutil_print
    LOCAL_ARM_MODE:=arm
    include $(BUILD_SHARED_LIBRARY)

    $(call import-add-path,path/to/fplutil)
    $(call import-module,android/native_app_glue)
    $(call import-module,libfplutil/jni)
~~~

`LOCAL_WHOLE_STATIC_LIBRARIES` adds `--whole-archive` to the linker command
line for each of the listed libraries.

# Linking with libfplutil_print   {#libfplutil_linking_print}

When using the Android make system (ndk-build), linking `libfplutil_print` will
automatically wrap calls to stdio and iostreams.  When imported using
`import-module`, the module exports the appropriate flags for the compiler and
linker:

~~~{.mk}
    $(call import-module,libfplutil/jni)
~~~

When using the toolchain directly, to link against `libfplutil_print`, you must
manually wrap the functions it implements manually.  To wrap functions, pass
the corresponding `--wrap=<name>` option on your link line.

For example:

~~~{.mk}
    LDFLAGS+= -Wl,--wrap=perror,--wrap=fflush,--wrap=fprintf,--wrap=vprintf \
              -Wl,--wrap=putc,--wrap=fputc,--wrap=putchar,--wrap=puts \
              -Wl,--wrap=fputs,--wrap=fwrite,--wrap=write,--wrap=writev \
              -Wl,--wrap=printf
    CFLAGS+= -fno-builtin-printf -fno-builtin-fprintf \
              -fno-builtin-fflush -fno-builtin-perror -fno-builtin-vprintf \
              -fno-builtin-putc -fno-builtin-putchar -fno-builtin-fputc \
              -fno-builtin-fputs -fno-builtin-puts -fno-builtin-fwrite \
              -fno-builtin-write -fno-builtin-writev
~~~

<br>

  [Android NDK]: http://developer.android.com/tools/sdk/ndk/index.html
  [dummy]: dummy
