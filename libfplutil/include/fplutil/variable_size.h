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

#ifndef FPLUTIL_VARIABLE_SIZE_H_
#define FPLUTIL_VARIABLE_SIZE_H_

#include <stddef.h>

namespace fplutil {

/// @brief Calculates the size of a variable-size class, taking into account
///        type alignment.
///
/// A variable-size class is one that is contiguous in memory, but has members
/// (often arrays) of variable size. For example, a variable-size spline class
/// might end in an array of nodes that is not always the same length.
///
/// Why use a variable-size class? Why not just use std::vector?
/// (1) Often, memory layout is critical to performance. The spline, for
///     example, might have some class-wide member variables in addition to its
///     array of nodes. For cache-performance reasons, it's critical that
///     both of these reside one piece of contiguous memory.
/// (2) std::vectors and other dynamically-sized types require multiple
///     memory allocations per-class. For classes that are allocated thousands
///     of times on start-up, this can be a measurable cost overhead.
/// (3) Memory is often passed around from one processor to another, or across
///     the network. When all data is contiguous in memory, this becomes
///     simpler.
/// (4) From a low-level point of view, data is tidiest when each class is
///     contained in one chunk of memory. Some people never look at the memory
///     inspector in the debugger, but it is a powerful tool so other people do
///     spend significant time there. A simpler memory layout is nice when
///     things go wrong with memory (e.g. memory corruption).
class VariableSizeCalculator {
 public:
  explicit VariableSizeCalculator(size_t base_size)
      : size_(base_size), alignment_(1) {}

  /// Add a raw chunk of memory of size `alloc_size` to the class.
  /// Return the offset of the *start* of the chunk of memory.
  size_t Raw(size_t alloc_size, size_t alignment) {
    const size_t mask = alignment - 1;
    const size_t aligned = (size_ + mask) & ~mask;
    size_ = aligned + alloc_size;
    alignment_ = alignment_ > alignment ? alignment_ : alignment; // =std::max()
    return aligned;
  }

  /// Add a type T to the class.
  /// Return the offet to the *start* of T.
  template<class T>
  size_t Type() { return Raw(sizeof(T), alignof(T)); }

  /// Add an array T[count] to the size.
  /// Return the offset of the *start* of the array.
  template<class T>
  size_t Array(size_t count) { return Raw(sizeof(T) * count, alignof(T)); }

  /// Return the current size of class.
  size_t size() const { return size_; }

  /// Return the required alignment of this class.
  /// This equals the maximum required alignment of the class's member
  /// variables.
  size_t alignment() const { return alignment_; }

 private:
  /// Current total size of the class.
  size_t size_;

  /// Current required alignment of the class.
  size_t alignment_;
};

class VariableSizeBuilder {
 public:
  VariableSizeBuilder(void* base, size_t base_size)
      : base_(static_cast<uint8_t*>(base)), size_(base_size) {}

  /// Add a raw chunk of memory of size `alloc_size` to the class.
  /// Return the offset of the *start* of the chunk of memory.
  void* Raw(size_t alloc_size, size_t alignment) {
    return base_ + size_.Raw(alloc_size, alignment);
  }

  /// Add a type T to the class.
  /// Return the offet to the *start* of T.
  template<class T>
  T* Type() { return static_cast<T*>(Raw(sizeof(T), alignof(T))); }

  /// Add an array T[count] to the size.
  /// Return the offset of the *start* of the array.
  template<class T>
  T* Array(size_t count) {
    return static_cast<T*>(Raw(sizeof(T) * count, alignof(T)));
  }

  /// Return a pointer past the current end of the class.
  uint8_t* End() const { return base_ + size(); }

  /// Return the current size of class.
  size_t size() const { return size_.size(); }

 private:
  uint8_t* base_;

  VariableSizeCalculator size_;
};

}  // namespace fplutil

#endif  // FPLUTIL_VARIABLE_SIZE_H_

