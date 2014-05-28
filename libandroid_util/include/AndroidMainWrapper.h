/*
* Copyright (c) 2014 Google, Inc.
*
* This software is provided 'as-is', without any express or implied
* warranty.  In no event will the authors be held liable for any damages
* arising from the use of this software.
* Permission is granted to anyone to use this software for any purpose,
* including commercial applications, and to alter it and redistribute it
* freely, subject to the following restrictions:
* 1. The origin of this software must not be misrepresented; you must not
* claim that you wrote the original software. If you use this software
* in a product, an acknowledgment in the product documentation would be
* appreciated but is not required.
* 2. Altered source versions must be plainly marked as such, and must not be
* misrepresented as being the original software.
* 3. This notice may not be removed or altered from any source distribution.
*/
#ifndef ANDROID_MAIN_WRAPPER_H
#define ANDROID_MAIN_WRAPPER_H

// This includes functionality to calls a standard C main() from the
// Android's NativeActivity entry point android_main().
//
// For example:
//
// #include "AndroidMainWrapper.h"
//
// int main(int argc, char **argv) {
//   ... do stuff ...
//   return 0;
// }
//
// Will "do stuff" and exit the NativeActivity on return from main().
// For more information see ndk/sources/android/native_app_glue.

#if defined(ANDROID) || defined(__ANDROID__)
#include <android_native_app_glue.h>

#if defined(__cplusplus)
extern "C" {
#endif  // defined(__cplusplus)

#if !defined(USE_NATIVE_APP_GLUE)
#define USE_NATIVE_APP_GLUE 1
#endif // !defined(USE_NATIVE_APP_GLUE)

#if USE_NATIVE_APP_GLUE
// This should be implemented by the application including this header.
extern int main(int argc, char** argv);
// Nonportable pthread function available on some platforms that returns nonzero
// if the calling thread is the main thread.  This is used in
// libdispatch/queue.c.  It is optional.
int pthread_main_np();
// Avoid redefining this as it has been set in config.h to the platform default.
#undef HAVE_PTHREAD_MAIN_NP
#define HAVE_PTHREAD_MAIN_NP 1
#endif // USE_NATIVE_APP_GLUE

// Service android events on the main NativeActivity thread ALooper.
//
// If the application was compiled using native_app_glue's android_main()
// support, we need to poll the thread's ALooper periodically to process
// events from Android event sources.
//
// This waits for and processes any pending events from the Android SDK being
// passed into the NDK. The call will block up to maxWait milliseconds for
// pending Android events.  0 returns immediately, -1 blocks indefinitely until
// an event arrives.
//
// If the application was compiled to NOT use the android_main() glue, then
// this call returns immediately for maxWait >= 0, and blocks forever if
// maxWait < 0.
void IdleAndroid(int maxWait);

#if defined(__cplusplus)
}
#endif  // defined(__cplusplus)

#endif // defined(ANDROID) || defined(__ANDROID__)
#endif // ANDROID_MAIN_WRAPPER_H
