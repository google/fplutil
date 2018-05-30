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

#ifndef FPLUTIL_ANDROID_UTILS_H
#define FPLUTIL_ANDROID_UTILS_H

#ifdef __ANDROID__
#include <jni.h>
#include <string>
#endif

namespace fplutil {

#ifdef __ANDROID__
/// @class JniObject
///
/// @brief A helper class wrapping jobject.
/// The class provides misc helper functions to access methods in the attached
/// object and maintains a local/global reference of the attached object.
class JniObject {
 public:
  JniObject() : global_ref_(false), obj_(nullptr) {}
  virtual ~JniObject() { CleanUp(); }

  /// @brief Copy constructors.
  JniObject(jobject obj) : global_ref_(false) { obj_ = obj; }
  JniObject(jstring str) : global_ref_(false) { obj_ = str; }

  /// @brief Add a global refrence to the object.
  void AddGlobalReference();

  /// @brief Method accessors to the object for variable return types.
  ///
  /// @param[in] method A method name.
  /// @param[in] signature A JNI style method signature.
  void CallVoidMethod(const char* method, const char* signature, ...);
  int32_t CallIntMethod(const char* method, const char* signature, ...);
  jobject CallObjectMethod(const char* method, const char* signature, ...);
  std::string CallStringMethod(const char* method, const char* signature, ...);

  /// @brief Set JNIEnv variable to the class. The function needs to be invoked
  /// on each thread before using the class on that thread.
  static void SetEnv(JNIEnv* env);

  /// @brief Static utility methods.

  /// @brief Call static method that returns an object.
  /// @param[in] cls A class name.
  /// @param[in] method A method name.
  /// @param[in] signature A JNI style method signature.
  static jobject CallStaticObjectMethod(const char* cls, const char* method,
                                        const char* signature, ...);

  /// @brief Create an object.
  ///
  /// @param[in] cls A class name to create.
  /// @param[in] signature A JNI style method signature of a constructor.
  static jobject CreateObject(const char* cls, const char* signature, ...);

  /// @brief Create a jstring from std::string.
  ///
  /// @param[in] string A string to convert.
  static jstring CreateString(std::string& str) {
    return GetEnv()->NewStringUTF(str.c_str());
  }

  /// @brief Getter of the jobject attached to the class.
  jobject get_object() { return static_cast<jobject>(obj_); }

 protected:
  static JNIEnv* GetEnv();
  jmethodID GetMethodId(const char* method, const char* signature);
  void CleanUp();
  bool global_ref_;
  void* obj_;
};

/// @class JniClass
///
/// @brief Helper class wrapping jclass object.
class JniClass : JniObject {
 public:
  JniClass() {}
  ~JniClass() {}

  /// @brief Find a class.
  ///
  /// @param[in] cls A class name to find.
  bool FindClass(const char* cls) {
    CleanUp();
    obj_ = static_cast<void*>(GetEnv()->FindClass(cls));
    return obj_ != nullptr;
  }

  /// @brief Getter of the jclass object.
  jclass get_class() { return static_cast<jclass>(obj_); }
};

#endif  // __ANDROID__
}  // namespace fplutils

#endif  // FPLUTIL_ANDROID_UTILS_H
