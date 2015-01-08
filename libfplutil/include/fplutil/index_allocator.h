// Copyright 2015 Google Inc. All rights reserved.
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

#ifndef FPLUTIL_INDEX_ALLOCATOR_H
#define FPLUTIL_INDEX_ALLOCATOR_H

/// @file
/// Header (and all code) for IndexAllocator.
///
/// IndexAllocator lets you allocate and free items in an array, and still
/// keep that array contiguous in memory. The array is managed by the caller,
/// who provides callbacks for moving indices around.


#include <algorithm>

namespace fpl {

/// @class IndexAllocator "fplutil/index_allocator.h"
/// @brief Allocate, free, and defragment array indices.
///
///   Purpose
///   =======
/// Allocate and free indices into an array. Tries to keep the array as small
/// as possible by recycling indices that have been freed.
///
///   Example Usage
///   =============
/// We have an array of items that we would like to process with SIMD
/// instructions. Items can be added and deleted from the array though. We don't
/// want many unused indices in the array, since these holes still have to be
/// processed with SIMD (which processes indices in groups of 4 or 8 or 16).
///
/// The IndexAllocator is great for this situation since you can call
/// Defragment() before running the SIMD algorithm. The Defragment() call will
/// backfill unused indices and ensure the data is contiguous.
///
///   Details
///   =======
/// Periodically, you can call Defragment() to backfill indices that have been
/// freed with the largest indices. This minimizes the length of the array, and
/// more importantly makes the array data contiguous.
///
/// During Defragment() when an index is moved, a callback
/// CallbackInterface::MoveIndex() is called so that the user can move the
/// corresponding data.
///
/// Whenever the array size is increased (durring Alloc()) or decreased (during
/// Defragment()), a callback CallbackInterface::SetNumIndices() is called so
/// that the user can grow or shrink the corresponding data.
template<class Index>
class IndexAllocator {
 public:
  class CallbackInterface {
   public:
    virtual ~CallbackInterface() {}
    virtual void SetNumIndices(Index num_indices) = 0;
    virtual void MoveIndex(Index old_index, Index new_index) = 0;
  };

  /// Create an empty IndexAllocator that uses the specified callback
  /// interface.
  explicit IndexAllocator(CallbackInterface& callbacks) :
      callbacks_(&callbacks),
      num_indices_(0) {
  }

  /// If a previously-freed index can be recycled, allocates that index.
  /// Otherwise, increases the number of indices by one, and returns the
  /// last index. When the number of indices is increased, the SetNumIndices()
  /// callback is called.
  Index Alloc() {
    // Recycle an unused index, if one exists.
    if (!unused_indices_.empty()) {
      const Index unused_index = unused_indices_.back();
      unused_indices_.pop_back();
      return unused_index;
    }

    // Allocate a new index.
    const Index new_index = num_indices_;
    num_indices_++;
    callbacks_->SetNumIndices(num_indices_);
    return new_index;
  }

  /// Recycle 'index'. It will be used in the next allocation, or backfilled in
  /// the next call to Defragment().
  /// @param index Index to be freed. Must be in the range
  ///              [0, num_indices_ - 1].
  void Free(Index index) {
    assert(0 <= index && index < num_indices_);
    unused_indices_.push_back(index);
  }

  /// Backfill all unused indices with the largest indices by calling
  /// callbacks_->MoveIndex(). This reduces the total number of indices,
  /// and keeps memory contiguous. Contiguous memory is important to mimimize
  /// cache misses.
  ///
  /// Note that we could eliminate Defragment() function by calling MoveIndex()
  /// from Free(). The code would be simpler. We move the indices lazily,
  /// however, for performance: Defragment() is something that can happen on a
  /// background thread.
  ///
  /// This function is fairly cheap. If there are N holes, then there will be
  /// **at most** N calls to MoveIndex(). We assume that moving an index is
  /// cheaper than processing data for an index. So, you should Defragment()
  /// right before you process data, for optimal performance.
  ///
  /// Note that the number of indices shrinks or stays the same in this
  /// function, so the final call to SetNumIndices() will never result in a
  /// reallocation of the underlying array (which would be slow).
  ///
  void Defragment() {
    // Quick check is an optimization.
    if (unused_indices_.size() == 0)
      return;

    // We check if unused index is the last index, so must be in sorted order.
    std::sort(unused_indices_.begin(), unused_indices_.end());

    // Plug every unused index by moving the last index on top of it.
    while (unused_indices_.size() > 0 && num_indices_ > 0) {
      // Recycle the largest unused undex.
      const Index unused_index = unused_indices_.back();
      unused_indices_.pop_back();

      // Move the last index into 'unused_index'. Delete the last index.
      num_indices_--;

      // Only perform move if source and destination are different.
      if (unused_index != num_indices_) {
        // Move last element into last unused index.
        callbacks_->MoveIndex(num_indices_, unused_index);
      }
    }

    // All unused indices have been filled in.
    unused_indices_.clear();

    // The index array has shrunk. Notify with a callback. Note that since
    // we're shrinking the array, this will not have to result in a realloc.
    callbacks_->SetNumIndices(num_indices_);
  }

  /// Returns true if there are no indices allocated.
  bool Empty() const {
    return static_cast<size_t>(num_indices_) == unused_indices_.size();
  }

  /// Returns the size of the array that  number of contiguous indices.
  /// This includes all the indices that have been free.
  Index num_indices() const { return num_indices_; }

 private:
  // When indices are moved or the number of inidices changes, we notify the
  // caller via these callbacks.
  CallbackInterface* callbacks_;

  // Total length of array. One greater than the current largest index.
  Index num_indices_;

  // When an index is freed, we keep track of it here. When an index is
  // allocated, we use one off this array, if one exists.
  // When Defragment() is called, we empty this array by filling all the
  // unused indices with the highest allocated indices. This reduces the total
  // size of the data arrays.
  std::vector<Index> unused_indices_;
};

} // namespace fpl


#endif // FPLUTIL_INDEX_ALLOCATOR_H
