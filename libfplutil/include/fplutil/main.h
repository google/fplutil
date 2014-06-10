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
#ifndef FPLUTIL_MAIN_H
#define FPLUTIL_MAIN_H

// Linking this library adds functionality to call a standard C main() from
// Android's NativeActivity NDK entry point, android_main(). This helps
// you by by making it very easy to resuse existing programs with a C main()
// entry point.
//
// For example, this code:
//
// #include "fplutil/main.h"
//
// int main(int argc, char **argv) {
//   ... do stuff ...
//   return 0;
// }
//
// will launch, "do stuff", and exit the NativeActivity on return from main().
// The android_main() is implemented inside this library for you.
//
// If "do stuff" requires nontrivial amounts of time, such as entering a main
// loop and looping forever, then it is advisable to add a call the
// ProcessAndroidEvents() function below periodically, which will minimally
// service events on the native activity looper.
//
// For more information see ndk/sources/android/native_app_glue.

#if defined(ANDROID) || defined(__ANDROID__)

#if defined(__cplusplus)
extern "C" {
#endif  // defined(__cplusplus)

// This should be implemented by the application including this header.
extern int main(int argc, char** argv);

// Process android events on the main NativeActivity thread ALooper.
//
// This waits for and processes any pending events from the Android SDK being
// passed into the NDK. The call will block up to maxWait milliseconds for
// pending Android events.  0 returns immediately, -1 blocks indefinitely until
// an event arrives.
void ProcessAndroidEvents(int maxWait);

#if defined(__cplusplus)
}
#endif  // defined(__cplusplus)

#endif // defined(ANDROID) || defined(__ANDROID__)
#endif // FPLUTIL_MAIN_H
