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

#ifndef FPLUTIL_FILE_MUTEX_H
#define FPLUTIL_FILE_MUTEX_H

#include <assert.h>
#include <errno.h>
#if !defined(_WIN32)
#include <pthread.h>
#else
#include <windows.h>
#endif  // !defined(_WIN32)

namespace fplutil {

/// @brief A simple synchronization lock. Only one thread at a time can Acquire.
class Mutex {
 public:
  /// @enum Mode
  ///
  /// @brief Bitfield that describes the mutex configuration.
  /// **Enumerations**:
  ///
  /// * `kModeNonRecursive` (`0`) - The mutex is initialized as a non-recursive
  /// mutex.
  /// * `kModeRecursive` (`1`) - The mutex is initialized as a recursive mutex.
  enum Mode {
    kModeNonRecursive = (0 << 0),
    kModeRecursive = (1 << 0),
  };

  /// @brief Default constructor that initializes a mutex as a recursive one.
  Mutex() { Initialize(kModeRecursive); }

  /// @brief Constructor that initializes a mutex with a parameter.
  /// @param[in] mode Mode indicating the mutex's recursive setting.
  explicit Mutex(Mode mode) { Initialize(mode); }

  ~Mutex() {
#if !defined(_WIN32)
    int ret = pthread_mutex_destroy(&mutex_);
    assert(ret == 0);
    (void)ret;
#else
    CloseHandle(synchronization_object_);
#endif  // !defined(_WIN32)
  }

  /// @brief Acquire the mutex's ownership.
  void Acquire() {
#if !defined(_WIN32)
    int ret = pthread_mutex_lock(&mutex_);
    assert(ret == 0);
    (void)ret;
#else
    WaitForSingleObject(synchronization_object_, INFINITE);
#endif  // !defined(_WIN32)
  }

  /// @brief Try to acquire the mutex's ownership.
  bool TryLock() {
#if !defined(_WIN32)
    int ret = pthread_mutex_trylock(&mutex_);
    return !ret;
#else
    auto ret = WaitForSingleObject(synchronization_object_, 0);
    return ret == WAIT_OBJECT_0;
#endif  // !defined(_WIN32)
  }

  /// @brief Release the mutex's ownership.
  void Release() {
#if !defined(_WIN32)
    int ret = pthread_mutex_unlock(&mutex_);
    assert(ret == 0);
    (void)ret;
#else
    if (mode_ & kModeRecursive) {
      ReleaseMutex(synchronization_object_);
    } else {
      ReleaseSemaphore(synchronization_object_, 1, 0);
    }
#endif  // !defined(_WIN32)
  }

 private:
  void Initialize(Mode mode) {
#if !defined(_WIN32)
    pthread_mutexattr_t attr;
    int ret = pthread_mutexattr_init(&attr);
    assert(ret == 0);
    if (mode & kModeRecursive) {
      ret = pthread_mutexattr_settype(&attr, PTHREAD_MUTEX_RECURSIVE);
      assert(ret == 0);
    }
    ret = pthread_mutex_init(&mutex_, &attr);
    assert(ret == 0);
    ret = pthread_mutexattr_destroy(&attr);
    assert(ret == 0);
    (void)ret;
#else
    mode_ = mode;
    if (mode & kModeRecursive) {
      synchronization_object_ = CreateMutex(nullptr, FALSE, nullptr);
    } else {
      synchronization_object_ = CreateSemaphore(nullptr, 1, 1, nullptr);
    }
#endif  // !defined(_WIN32)
  }

#if !defined(_WIN32)
  pthread_mutex_t mutex_;
#else
  HANDLE synchronization_object_;
  Mode mode_;
#endif  // !defined(_WIN32)
};

/// @brief Acquire and hold a /ref Mutex, while in scope.
///
/// Example usage:
///   \code{.cpp}
///   Mutex syncronization_mutex;
///   void MyFunctionThatRequiresSynchronization() {
///     MutexLock lock(syncronization_mutex);
///     // ... logic ...
///   }
///   \endcode
class MutexLock {
 public:
  /// @brief Acquires specified mutex's ownership for a life time of the object.
  ///
  /// @param[in] mutex Mutex to aquire an ownership.
  explicit MutexLock(Mutex& mutex) : mutex_(&mutex) { mutex_->Acquire(); }
  ~MutexLock() { mutex_->Release(); }

 private:
  // Copy is disallowed.
  MutexLock(const MutexLock& rhs);
  MutexLock& operator=(const MutexLock& rhs);

  Mutex* mutex_;
};

/// @brief Acquires and hold a /ref Mutex, if not held by someone else.
///
/// Example usage:
///   \code{.cpp}
///   Mutex syncronization_mutex;
///   bool MyFunctionThatRequiresSynchronization() {
///     MutexTryLock lock;
///     if (!lock.Try(syncronization_mutex)) return false;
///     // ... logic ...
///     return true;
///   }
///   \endcode
class MutexTryLock {
 public:
  /// @brief Acquires specified mutex's ownership for a life time of the object.
  ///
  /// @param[in] mutex Mutex to aquire an ownership.
  explicit MutexTryLock() : mutex_(nullptr) {}
  ~MutexTryLock() { if (mutex_) mutex_->Release(); }

  /// @brief Acuires specified mutex's ownership for a life time of the object.
  bool Try(Mutex& mutex) {
    assert(mutex_ == nullptr);
    const bool locked = mutex.TryLock();
    if (locked) {
      mutex_ = &mutex;
    }
    return locked;
  }

 private:
  // Copy is disallowed.
  MutexTryLock(const MutexTryLock& rhs);
  MutexTryLock& operator=(const MutexTryLock& rhs);

  Mutex* mutex_;
};

}  // namespace fplutil

#endif  // FPLUTIL_FILE_MUTEX_H
