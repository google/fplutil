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

#include <android_native_app_glue.h>
#include <android/log.h>
#include <assert.h>
#include <jni.h>
#include <pthread.h>
#include <unistd.h>
#include <stdio.h>
#include "fplutil/main.h"
#include "fplutil/version.h"

// See android.app.Activity.
enum AndroidAppActivityResults {
  ANDROID_APP_ACTIVITY_RESULT_CANCELED = 0,
  ANDROID_APP_ACTIVITY_RESULT_FIRST_USER = 1,
  ANDROID_APP_ACTIVITY_RESULT_OK = -1,
};

static struct android_app* gApp = 0;
static pthread_t gMainTID;
const char kFplUtilMainVersionString[] = FPLUTIL_VERSION_STRING;

//
// Wait for and process any pending Android events from NativeActivity.
//
void ProcessAndroidEvents(int msec)
{
  if (pthread_equal(pthread_self(), gMainTID)) {
    struct android_poll_source* source = NULL;
    int events;
    int looperId = ALooper_pollAll(msec, NULL, &events, (void**)&source);

    if (looperId >= 0 && source) {
        source->process(gApp, source);
    }
  } else {
    __android_log_print(ANDROID_LOG_ERROR, "fplutil",
        "Attempted to call ProcessAndroidEvents() from non-main thread");
    assert(0);
  }
}

// Android native activity entry point.
void android_main(struct android_app* state) {
  // Make sure android native glue isn't stripped.
  app_dummy();

  // Set state variables for ProcessAndroidEvents().
  gApp = state;
  gMainTID = pthread_self();

  static char *argv[] = {"AndroidApp"};
  int result = main(1, argv);

  // Pass the return code from main back to the Activity.
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

  // Finish the activity and exit the app.
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

