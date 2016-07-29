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

#include "fplutil/android_utils.h"

namespace fplutil {
#ifdef __ANDROID__
// Static shared variable pointing the current Java Environment.
JNIEnv* JniObject::env_ = nullptr;

jobject JniObject::CreateObject(const char* cls_name, const char* signature,
                                ...) {
  JniClass cls;
  jobject obj = nullptr;
  if (cls.FindClass(cls_name)) {
    jmethodID mid = env_->GetMethodID(cls.get_class(), "<init>", signature);
    va_list args;
    va_start(args, signature);
    obj = env_->NewObjectV(cls.get_class(), mid, args);
    va_end(args);
  }
  return obj;
}

jobject JniObject::CallStaticObjectMethod(const char* cls_name,
                                          const char* method,
                                          const char* signature, ...) {
  JniClass cls;
  jobject obj = nullptr;
  if (cls.FindClass(cls_name)) {
    va_list args;
    va_start(args, signature);
    jmethodID mid = env_->GetStaticMethodID(cls.get_class(), method, signature);
    obj = env_->CallStaticObjectMethodV(cls.get_class(), mid, args);
    va_end(args);
  }
  return obj;
}

void JniObject::CallVoidMethod(const char* method, const char* signature, ...) {
  va_list args;
  va_start(args, signature);
  auto mid = GetMethodId(method, signature);
  env_->CallVoidMethodV(static_cast<jobject>(obj_), mid, args);
  va_end(args);
  return;
}

int32_t JniObject::CallIntMethod(const char* method, const char* signature,
                                 ...) {
  va_list args;
  va_start(args, signature);
  auto mid = GetMethodId(method, signature);
  auto ret = env_->CallIntMethodV(static_cast<jobject>(obj_), mid, args);
  va_end(args);
  return ret;
}

std::string JniObject::CallStringMethod(const char* method,
                                        const char* signature, ...) {
  va_list args;
  va_start(args, signature);
  auto mid = GetMethodId(method, signature);
  auto jstr = env_->CallObjectMethodV(static_cast<jobject>(obj_), mid, args);
  va_end(args);
  // Convert jstring to std::string.
  auto str = env_->GetStringUTFChars(static_cast<jstring>(jstr), NULL);
  std::string ret = str;
  env_->ReleaseStringUTFChars(static_cast<jstring>(jstr), str);
  env_->DeleteLocalRef(jstr);
  return ret;
}

void JniObject::AddGlobalReference() {
  env_->NewGlobalRef(static_cast<jobject>(obj_));
  env_->DeleteLocalRef(static_cast<jobject>(obj_));
  global_ref_ = true;
}

jmethodID JniObject::GetMethodId(const char* method, const char* signature) {
  jclass cls = env_->GetObjectClass(static_cast<jobject>(obj_));
  jmethodID mid = env_->GetMethodID(cls, method, signature);
  env_->DeleteLocalRef(cls);
  return mid;
}

void JniObject::CleanUp() {
  if (obj_) {
    if (global_ref_) {
      env_->DeleteGlobalRef(static_cast<jobject>(obj_));
    } else {
      env_->DeleteLocalRef(static_cast<jobject>(obj_));
    }
  }
}

#endif  // __ANDROID__

}  // namespace fplutil
