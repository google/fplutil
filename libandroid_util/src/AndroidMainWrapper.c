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
#include "AndroidMainWrapper.h"
#include <jni.h>
#include "AndroidLogPrint.h"
#include <pthread.h>
#include <assert.h>
#include <unistd.h>

// See android.app.Activity.
enum AndroidAppActivityResults {
  ANDROID_APP_ACTIVITY_RESULT_CANCELED = 0,
  ANDROID_APP_ACTIVITY_RESULT_FIRST_USER = 1,
  ANDROID_APP_ACTIVITY_RESULT_OK = -1,
};

struct android_app* gApp = 0;
pthread_t gMainTID;

//
// Wait for and process any pending Android events from NativeActivity.
//
void IdleAndroid(int msec)
{
#ifdef USE_NATIVE_APP_GLUE
  if (pthread_main_np()) {
    struct android_poll_source* source = NULL;
    int events;
    int looperId = ALooper_pollAll(msec, NULL, &events, (void**)&source);

    if (looperId >= 0 && source) {
        source->process(gApp, source);
    }
  } else {
    ANDROID_LOG_ERROR("ERROR - idle attempt on non-main thread...");
    assert(0);
  }
#else  // USE_NATIVE_APP_GLUE
  while (msec < 0) {
    pause();
  }
#endif // USE_NATIVE_APP_GLUE
}



#ifdef USE_NATIVE_APP_GLUE

int pthread_main_np()
{
  return pthread_equal(pthread_self(), gMainTID);
}

// Android native activity entry point.
void android_main(struct android_app* state) {
  // Make sure android native glue isn't stripped.
  app_dummy();

  gApp = state;
  gMainTID = pthread_self();

  static const char * const argv[] = {ANDROID_LOG_PRINT_TAG_STRING};
  int result = main(1, argv);

  ANativeActivity * const activity = state->activity;
  {
    jobject nativeActivityObject = activity->clazz;
    jclass nativeActivityClass;
    jmethodID setResult;
    JNIEnv *env = activity->env;
    JavaVM *javaVm = activity->vm;
    int returnResult = result == 0 ? ANDROID_APP_ACTIVITY_RESULT_OK :
      result > 0 ? result + ANDROID_APP_ACTIVITY_RESULT_FIRST_USER :
      ANDROID_APP_ACTIVITY_RESULT_CANCELED;
    (*javaVm)->AttachCurrentThread(javaVm, &env, NULL);
    nativeActivityClass = (*env)->GetObjectClass(env, nativeActivityObject);
    setResult = (*env)->GetMethodID(env, nativeActivityClass, "setResult",
                                    "(I)V");
    (*env)->CallVoidMethod(env, nativeActivityObject, setResult, returnResult);
    (*javaVm)->DetachCurrentThread(javaVm);
  }

  for ( ; ; ) {
    struct android_poll_source* source = NULL;
    int looperId;
    int events;
    // Signal app completion.
    ANativeActivity_finish(activity);
    // Pump the event loop.
    while ((looperId = ALooper_pollAll(-1, NULL, &events,
                                       (void**)&source)) >= 0) {
      switch (looperId) {
      case LOOPER_ID_MAIN:
        // drop through
      case LOOPER_ID_INPUT:
        if (source) {
          source->process(state, source);
        }
        break;
      default:
        // >= LOOPER_ID_USER so this is a user data source which this doesn't
        // know how to process.
        break;
      }
      // If the NativeActivity is waiting for the application thread to
      // complete, exit this function.
      if (state->destroyRequested) {
        break;
      }
    }
  }
}

#endif // USE_NATIVE_APP_GLUE