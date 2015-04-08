// Copyright 2014 Google Inc. All rights reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#ifndef FPLUTIL_MAIN_H
#define FPLUTIL_MAIN_H

/// @file
/// Header for libfplutil_main.
///
/// libfplutil_main makes it easy to build traditional C/C++
/// applications for Android that use an `int main()` entry point.
///
/// Linking this library adds functionality to call a standard C main() from
/// Android's NativeActivity NDK entry point, android_main(). This helps
/// you by by making it very easy to resuse existing programs with a C main()
/// entry point.
///
/// For example, this code:
///
/// @code{.c}
/// #include "fplutil/main.h"
///
/// int main(int argc, char **argv) {
///   ... do stuff ...
///   return 0;
/// }
/// @endcode
///
/// will launch, "do stuff", and exit the NativeActivity on return from main().
/// The android_main() is implemented inside this library for you.
///
/// If "do stuff" requires nontrivial amounts of time, such as entering a main
/// loop and looping forever, then it is advisable to add a call the
/// ProcessAndroidEvents() function below periodically, which will minimally
/// service events on the native activity looper.
///
/// For more information see `ndk/sources/android/native_app_glue`.

#if defined(ANDROID) || defined(__ANDROID__)

#if defined(__cplusplus)
extern "C" {
#endif  // defined(__cplusplus)

/// This should be implemented by the application including this header.
extern int main(int argc, char** argv);

/// Process android events on the main NativeActivity thread ALooper.
///
/// This waits for and processes any pending events from the Android SDK being
/// passed into the NDK. The call will block up to maxWait milliseconds for
/// pending Android events.
///
/// @param maxWait 0 returns immediately, -1 blocks indefinitely until an
///                event arrives.
void ProcessAndroidEvents(int maxWait);

#if defined(__cplusplus)
}
#endif  // defined(__cplusplus)

#endif  // defined(ANDROID) || defined(__ANDROID__)
#endif  // FPLUTIL_MAIN_H
