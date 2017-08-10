// Copyright 2016 Google Inc. All rights reserved.
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

#ifdef __ANDROID__

#include "fplutil/android_utils.h"

#include <pthread.h>

namespace {
pthread_key_t g_env_pthread_key;

void InitializeEnvThreadLocal() {
  static bool g_thread_local_initialized = []() {
    pthread_key_create(&g_env_pthread_key, nullptr);
    return true;
  }();
  (void) g_thread_local_initialized;
}

}  // namespace

namespace fplutil {

JNIEnv* JniObject::GetEnv() {
  InitializeEnvThreadLocal();
  return static_cast<JNIEnv*>(pthread_getspecific(g_env_pthread_key));
}

void JniObject::SetEnv(JNIEnv* env) {
  InitializeEnvThreadLocal();
  pthread_setspecific(g_env_pthread_key, env);
}

jobject JniObject::CreateObject(const char* cls_name, const char* signature,
                                ...) {
  JniClass cls;
  jobject obj = nullptr;
  JNIEnv* env = GetEnv();
  if (cls.FindClass(cls_name)) {
    jmethodID mid = env->GetMethodID(cls.get_class(), "<init>", signature);
    va_list args;
    va_start(args, signature);
    obj = env->NewObjectV(cls.get_class(), mid, args);
    va_end(args);
  }
  return obj;
}

jobject JniObject::CallStaticObjectMethod(const char* cls_name,
                                          const char* method,
                                          const char* signature, ...) {
  JniClass cls;
  jobject obj = nullptr;
  JNIEnv* env = GetEnv();
  if (cls.FindClass(cls_name)) {
    va_list args;
    va_start(args, signature);
    jmethodID mid = env->GetStaticMethodID(cls.get_class(), method, signature);
    obj = env->CallStaticObjectMethodV(cls.get_class(), mid, args);
    va_end(args);
  }
  return obj;
}

void JniObject::CallVoidMethod(const char* method, const char* signature, ...) {
  va_list args;
  va_start(args, signature);
  auto mid = GetMethodId(method, signature);
  GetEnv()->CallVoidMethodV(static_cast<jobject>(obj_), mid, args);
  va_end(args);
  return;
}

int32_t JniObject::CallIntMethod(const char* method, const char* signature,
                                 ...) {
  va_list args;
  va_start(args, signature);
  auto mid = GetMethodId(method, signature);
  auto ret = GetEnv()->CallIntMethodV(static_cast<jobject>(obj_), mid, args);
  va_end(args);
  return ret;
}

jobject JniObject::CallObjectMethod(const char* method, const char* signature,
                                    ...) {
  va_list args;
  va_start(args, signature);
  auto mid = GetMethodId(method, signature);
  auto ret = GetEnv()->CallObjectMethodV(static_cast<jobject>(obj_), mid, args);
  va_end(args);
  return ret;
}

std::string JniObject::CallStringMethod(const char* method,
                                        const char* signature, ...) {
  va_list args;
  JNIEnv* env = GetEnv();
  va_start(args, signature);
  auto mid = GetMethodId(method, signature);
  auto jstr = env->CallObjectMethodV(static_cast<jobject>(obj_), mid, args);
  va_end(args);
  // Convert jstring to std::string.
  auto str = env->GetStringUTFChars(static_cast<jstring>(jstr), NULL);
  std::string ret = str;
  env->ReleaseStringUTFChars(static_cast<jstring>(jstr), str);
  env->DeleteLocalRef(jstr);
  return ret;
}

void JniObject::AddGlobalReference() {
  JNIEnv* env = GetEnv();
  env->NewGlobalRef(static_cast<jobject>(obj_));
  env->DeleteLocalRef(static_cast<jobject>(obj_));
  global_ref_ = true;
}

jmethodID JniObject::GetMethodId(const char* method, const char* signature) {
  JNIEnv* env = GetEnv();
  jclass cls = env->GetObjectClass(static_cast<jobject>(obj_));
  jmethodID mid = env->GetMethodID(cls, method, signature);
  env->DeleteLocalRef(cls);
  return mid;
}

void JniObject::CleanUp() {
  if (obj_) {
    JNIEnv* env = GetEnv();
    if (global_ref_) {
      env->DeleteGlobalRef(static_cast<jobject>(obj_));
    } else {
      env->DeleteLocalRef(static_cast<jobject>(obj_));
    }
  }
}

}  // namespace fplutil

#endif  // __ANDROID__
