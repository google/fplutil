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
#include <assert.h>
#include <cstring>
#include <type_traits>

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
template <class Index, class Count>
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
  explicit IndexAllocator(CallbackInterface& callbacks)
      : callbacks_(&callbacks) {
    static_assert(std::is_signed<Count>::value, "Count must be a signed type");
  }

  /// If a previously-freed index can be recycled, allocates that index.
  /// Otherwise, increases the total number of indices by `count`, and return
  /// the first new index. When the number of indices is increased,
  /// the SetNumIndices() callback is called.
  /// @param count The number of indices in this allocation. Each block of
  ///              allocated indices is kept contiguous during Defragment()
  ///              calls. The index returned is the first index in the block.
  Index Alloc(Count count) {
    // Recycle an unused index, if one exists and has the correct count.
    typename std::vector<Index>::iterator least_excess_it = unused_indices_.end();
    Count least_excess = std::numeric_limits<Count>::max();
    for (auto it = unused_indices_.begin(); it != unused_indices_.end(); ++it) {
      const Index unused_index = *it;
      const Count excess = CountForIndex(unused_index) - count;

      // Not big enough.
      if (excess < 0)
        continue;

      // Perfect size. Remove from `unused_indices_` pool.
      if (excess == 0) {
        unused_indices_.erase(it);
        return unused_index;
      }

      // Too big. We'll return the one with the least excess size.
      if (excess < least_excess) {
        least_excess = excess;
        least_excess_it = it;
      }
    }

    // The unused index has a count that's too high.
    if (least_excess_it != unused_indices_.end()) {
      // Return the first `count` indices.
      const Index excess_index = *least_excess_it;

      // Put the remainder in the `unused_indices_` pool.
      const Index remainder_index = excess_index + count;
      InitializeIndex(remainder_index, least_excess);
      *least_excess_it = remainder_index;

      return excess_index;
    }

    // Allocate a new index.
    const Index new_index = num_indices();
    SetNumIndices(new_index + count);
    InitializeIndex(new_index, count);
    return new_index;
  }

  /// Recycle 'index'. It will be used in the next allocation, or backfilled in
  /// the next call to Defragment().
  /// @param index Index to be freed. Must be in the range
  ///              [0, num_indices_ - 1].
  void Free(Index index) {
    assert(ValidIndex(index));
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
    if (unused_indices_.size() == 0) return;

    // We check if unused index is the last index, so must be in sorted order.
    std::sort(unused_indices_.begin(), unused_indices_.end());

    // Plug every unused index.
    Index new_num_indices = num_indices();
    while (unused_indices_.size() > 0) {

      // Recycle the largest unused undex.
      const Index unused_index = unused_indices_.back();
      unused_indices_.pop_back();

      // Search from the back for an index that fills the hole.
      const Count count = CountForIndex(unused_index);
      const Index fill_index = LastIndexMatchingCount(unused_index);

      // Only perform move if source and destination are different.
      if (fill_index != unused_index) {
        // Move fill element into unused index.
        callbacks_->MoveIndex(fill_index, unused_index);
      }

      // Shift all items after fill_index forward, to fill the new hole.
      // The hope is that this won't have to move very many, since this is slow.
      // TODO OPT: We can do better than this by finding indices of smaller
      //           size and using those to fill the hole. The assumption is
      //           that most of the time the allocation sizes will be pretty
      //           uniform, so this function will almost always be a no-op.
      //           But in pathological cases, this assumption can be very wrong.
      MoveAllLaterIndices(fill_index);

      // Remember how many indices we've defragged.
      new_num_indices -= count;
    }

    // All unused indices have been filled in.
    unused_indices_.clear();

    // The index array has shrunk. Notify with a callback. Note that since
    // we're shrinking the array, this will not have to result in a realloc.
    SetNumIndices(new_num_indices);
  }

  /// Returns true if there are no indices allocated.
  bool Empty() const {
    return num_indices() == NumUnusedIndices();
  }

  /// Returns true if the index is current allocated.
  bool ValidIndex(Index index) const {
    if (index < 0 || index >= num_indices())
      return false;

    if (counts_[index] == 0)
      return false;

    for (ConstIndexIterator it = unused_indices_.begin();
         it != unused_indices_.end(); ++it) {
      if (index == *it) return false;
    }

    return true;
  }

  /// Returns the number of wasted indices. These holes will be plugged when
  /// Degragment() is called.
  Index NumUnusedIndices() const {
    Count count = 0;
    for (size_t i = 0; i < unused_indices_.size(); ++i) {
      count += CountForIndex(unused_indices_[i]);
    }
    return count;
  }

  /// Returns the `count` value specified in Alloc. That is, the number of
  /// consecutive indices associated with `index`.
  Count CountForIndex(Index index) const {
    assert(counts_[index] > 0);
    return counts_[index];
  }

  /// Returns the size of the array that  number of contiguous indices.
  /// This includes all the indices that have been free.
  Index num_indices() const { return static_cast<Index>(counts_.size()); }

 private:
  typedef typename std::vector<Index>::const_iterator ConstIndexIterator;
  static const Index kInvalidIndex = static_cast<Index>(-1);

  /// Returns the next allocated index. Skips over all indices associated
  /// with `index`.
  Index NextIndex(Index index) const {
    assert(index < num_indices() && counts_[index] > 0);
    return index + counts_[index];
  }

  /// Returns the previous allocated index. Skips over all indices associated
  /// with `index` - 1.
  Index PrevIndex(Index index) const {
    assert(0 < index && index <= num_indices() &&
           (index == num_indices() ||
            counts_[index - 1] == 1 || counts_[index - 1] < 0));
    const Count prev_count = counts_[index - 1];
    return prev_count > 0 ? index - 1 : index - 1 + prev_count;
  }

  /// Set up the `counts_` array to hold the size of `index`. Only the value
  /// at `counts_[index]` really matters. The others are initialized for
  /// debugging, and to make traversal of the `counts_` array easier.
  void InitializeIndex(Index index, Count count) {
    // Initialize the count for this index.
    counts_[index] = count;
    for (int i = 1; i < count; ++i) {
      counts_[index + i] = -i;
    }
  }

  /// Adjust internal state to match the new index size, and notify the
  /// callback that size has changed.
  void SetNumIndices(Index new_num_indices) {
    // Increase (or decrease) the count logger.
    counts_.resize(new_num_indices, 0);

    // Report size change.
    callbacks_->SetNumIndices(new_num_indices);
  }

  /// Returns allocation closest to the end of the array that has the matching
  /// size of `search_index`.
  Index LastIndexMatchingCount(Index search_index) const {
    const Count count = CountForIndex(search_index);
    Index index = num_indices();
    for (;;) {
      index = PrevIndex(index);
      if (index == search_index)
        break;

      if (CountForIndex(index) == count)
        break;
    }
    assert(ValidIndex(index));
    return index;
  }

  /// Shift all indices after `index` to the left to fill the space occupied
  /// by `index`.
  void MoveAllLaterIndices(Index index) {
    // Notify callback.
    const Index next_index = NextIndex(index);
    const Index num_deleted_indices = next_index - index;
    for (Index i = next_index; i < num_indices(); i = NextIndex(i)) {
      callbacks_->MoveIndex(i, i - num_deleted_indices);
    }

    // Update counts_ to fill hole.
    std::memmove(&counts_[index], &counts_[next_index], counts_.size() - next_index);
  }

  // When indices are moved or the number of inidices changes, we notify the
  // caller via these callbacks.
  CallbackInterface* callbacks_;

  // For every valid index, the number of indices
  // associated with that index. For intermediate indices, negative number
  // representing the offset to the actual index.
  //
  //              valid indices
  //               |   |      |            |   |
  //               v   v      v            v   v
  // For example:  1 | 2 -1 | 4 -1 -2 -3 | 1 | 1
  //                      ^      ^  ^  ^
  //                      |      |  |  |
  //                     offset to the actual index
  std::vector<Count> counts_;

  // When an index is freed, we keep track of it here. When an index is
  // allocated, we use one off this array, if one exists.
  // When Defragment() is called, we empty this array by filling all the
  // unused indices with the highest allocated indices. This reduces the total
  // size of the data arrays.
  std::vector<Index> unused_indices_;
};

}  // namespace fpl

#endif  // FPLUTIL_INDEX_ALLOCATOR_H
