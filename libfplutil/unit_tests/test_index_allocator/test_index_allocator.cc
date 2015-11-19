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

#include <stdint.h>
#include "gtest/gtest.h"
#include "fplutil/index_allocator.h"

using fplutil::IndexAllocator;

#define TEST_ALL_SIZES_F(MY_TEST)                \
  TEST_F(IndexAllocatorTests, MY_TEST##_int8) {  \
    MY_TEST##_Test<int8_t>(1);                   \
    MY_TEST##_Test<int8_t>(2);                   \
    MY_TEST##_Test<int8_t>(3);                   \
  }                                              \
  TEST_F(IndexAllocatorTests, MY_TEST##_int16) { \
    MY_TEST##_Test<int16_t>(1);                  \
    MY_TEST##_Test<int16_t>(2);                  \
    MY_TEST##_Test<int16_t>(4);                  \
  }                                              \
  TEST_F(IndexAllocatorTests, MY_TEST##_int32) { \
    MY_TEST##_Test<int32_t>(1);                  \
    MY_TEST##_Test<int32_t>(2);                  \
    MY_TEST##_Test<int32_t>(5);                  \
  }

class IndexAllocatorTests : public ::testing::Test {
protected:
  virtual void SetUp() {}
  virtual void TearDown() {}
};

template <class Index>
class Callbacks : public IndexAllocator<Index>::CallbackInterface {
  typedef IndexAllocator<Index> IndexAlloc;
  typedef typename IndexAlloc::IndexRange IndexRange;
  typedef typename IndexAlloc::Count Count;

 public:
  static const Index kInvalidIndex = static_cast<Index>(-1);
  static const Count kInvalidCount = static_cast<Count>(0);

  Callbacks() : num_indices_(0) {}

  // Implement virtuals from CallbackInterface.
  virtual void SetNumIndices(Index num_indices) { num_indices_ = num_indices; }
  virtual void MoveIndexRange(const IndexRange& source, Index target) {
    moves_.push_back(Move(source, target));
  }

  // Return true if ith callback matches parameters.
  bool Check(size_t i, Index source, Index target, Count count) const {
    if (i >= moves_.size()) return false;

    const Move& m = moves_[i];
    return m.source.start() == source && m.target == target &&
           m.source.Length() == count;
  }
  int NumMoves() const { return static_cast<int>(moves_.size()); }
  Index num_indices() const { return num_indices_; }

 private:
  struct Move {
    IndexRange source;
    Index target;
    Move() : source(kInvalidIndex, 0), target(kInvalidIndex) {}
    Move(IndexRange source, Index target) : source(source), target(target) {}
  };

  Index num_indices_;
  std::vector<Move> moves_;
};

// Test allocating and freeing one index.
template <class Index>
void AllocAndFree_OneIndex_Test(Index count) {
  Callbacks<Index> callbacks;
  IndexAllocator<Index> alloc(callbacks);

  EXPECT_TRUE(alloc.Empty());
  const Index index1 = alloc.Alloc(count);
  EXPECT_FALSE(alloc.Empty());
  alloc.Free(index1);
  EXPECT_TRUE(alloc.Empty());
}
TEST_ALL_SIZES_F(AllocAndFree_OneIndex)

// Test allocating two indices, then freeing them in most-recent to
// first-allocated.
template <class Index>
void AllocAndFree_TwoIndicesInOrder_Test(Index count) {
  Callbacks<Index> callbacks;
  IndexAllocator<Index> alloc(callbacks);

  EXPECT_TRUE(alloc.Empty());
  const Index index1 = alloc.Alloc(count);
  const Index index2 = alloc.Alloc(count);
  EXPECT_FALSE(alloc.Empty());
  EXPECT_NE(index1, index2);
  alloc.Free(index2);
  alloc.Free(index1);
  EXPECT_TRUE(alloc.Empty());
}
TEST_ALL_SIZES_F(AllocAndFree_TwoIndicesInOrder)

// Test allocating two indices, then freeing them in first-allocated to
// most-recent.
template <class Index>
void AllocAndFree_TwoIndicesReverseOrder_Test(Index count) {
  Callbacks<Index> callbacks;
  IndexAllocator<Index> alloc(callbacks);

  EXPECT_TRUE(alloc.Empty());
  const Index index1 = alloc.Alloc(count);
  const Index index2 = alloc.Alloc(count);
  EXPECT_FALSE(alloc.Empty());
  EXPECT_NE(index1, index2);
  alloc.Free(index1);
  alloc.Free(index2);
  EXPECT_TRUE(alloc.Empty());
}
TEST_ALL_SIZES_F(AllocAndFree_TwoIndicesReverseOrder)

// Test allocating three indices, then freeing them in a scattered order.
template <class Index>
void AllocAndFree_ThreeIndicesScatteredOrder_Test(Index count) {
  Callbacks<Index> callbacks;
  IndexAllocator<Index> alloc(callbacks);

  EXPECT_TRUE(alloc.Empty());
  const Index index1 = alloc.Alloc(count);
  const Index index2 = alloc.Alloc(count);
  const Index index3 = alloc.Alloc(count);
  EXPECT_FALSE(alloc.Empty());
  EXPECT_NE(index1, index2);
  EXPECT_NE(index2, index3);
  alloc.Free(index2);
  alloc.Free(index1);
  alloc.Free(index3);
  EXPECT_TRUE(alloc.Empty());
}
TEST_ALL_SIZES_F(AllocAndFree_ThreeIndicesScatteredOrder)

// Test that the number of indices increases when Alloc(count) is called, and
// only decreases when Defragment() is called.
template <class Index>
void Callbacks_SetNumIndices_Test(Index count) {
  Callbacks<Index> callbacks;
  IndexAllocator<Index> alloc(callbacks);

  EXPECT_EQ(callbacks.num_indices(), static_cast<Index>(0));
  const Index index1 = alloc.Alloc(count);
  EXPECT_EQ(callbacks.num_indices(), static_cast<Index>(count));
  alloc.Free(index1);
  EXPECT_EQ(callbacks.num_indices(), static_cast<Index>(count));
  alloc.Defragment();
  EXPECT_EQ(callbacks.num_indices(), static_cast<Index>(0));
  EXPECT_EQ(callbacks.NumMoves(), 0);
}
TEST_ALL_SIZES_F(Callbacks_SetNumIndices)

// Test that index 1 gets backfilled into index 0 after index 0 is freed.
template <class Index>
void Callbacks_Defragment_Test(Index count) {
  Callbacks<Index> callbacks;
  IndexAllocator<Index> alloc(callbacks);

  const Index index0 = alloc.Alloc(count);
  alloc.Alloc(count);
  alloc.Free(index0);
  alloc.Defragment();
  EXPECT_TRUE(callbacks.Check(0, count, 0, count));
  EXPECT_EQ(alloc.CountForIndex(index0), count);
}
TEST_ALL_SIZES_F(Callbacks_Defragment)

// Test Defragment() when only the last index has been freed.
template <class Index>
void Callbacks_DefragmentAtEnd_Test(Index count) {
  typedef Callbacks<Index> CallB;
  CallB callbacks;
  IndexAllocator<Index> alloc(callbacks);

  alloc.Alloc(count);
  alloc.Alloc(count);
  const Index index = alloc.Alloc(count);
  alloc.Free(index);
  alloc.Defragment();
  EXPECT_EQ(callbacks.NumMoves(), 0);
  EXPECT_EQ(callbacks.num_indices(), static_cast<Index>(2 * count));
}
TEST_ALL_SIZES_F(Callbacks_DefragmentAtEnd)

// Call Alloc() and Free() on several indices and then Defragment().
// Ensure we end up with number of Allocs() - number of Frees() as the
// number of indices.
template <class Index>
void Callbacks_DefragmentStartMiddleEnd_Test(Index count) {
  Callbacks<Index> callbacks;
  IndexAllocator<Index> alloc(callbacks);

  const Index index_start = alloc.Alloc(count);
  alloc.Alloc(count);
  const Index index_middle0 = alloc.Alloc(count);
  const Index index_middle1 = alloc.Alloc(count);
  alloc.Alloc(count);
  const Index index_end = alloc.Alloc(count);

  alloc.Free(index_middle1);
  alloc.Free(index_middle0);
  alloc.Free(index_end);
  alloc.Free(index_start);

  alloc.Defragment();
  EXPECT_EQ(callbacks.num_indices(), static_cast<Index>(2 * count));
}
TEST_ALL_SIZES_F(Callbacks_DefragmentStartMiddleEnd)

// Call Alloc() and Free() and Alloc() of a slightly smaller size.
// Tests recycling of indices that are smaller. We shouldn't grow the number
// of indices.
template <class Index>
void Callbacks_Recycling_Test(Index count) {
  Callbacks<Index> callbacks;
  IndexAllocator<Index> alloc(callbacks);

  // Allocating a big chuck should result in exactly that big chuck's worth
  // of indices total.
  const Index index_big = alloc.Alloc(2 * count);
  alloc.Free(index_big);
  EXPECT_EQ(callbacks.num_indices(), static_cast<Index>(2 * count));

  // Allocating a big index of the same size should result in recycling.
  const Index index_big_again = alloc.Alloc(2 * count);
  alloc.Free(index_big_again);
  EXPECT_EQ(index_big, index_big_again);
  EXPECT_EQ(callbacks.num_indices(), static_cast<Index>(2 * count));

  // Next Alloc of smaller size should recycle the original big index.
  // No new indices should be allocated.
  const Index index_med = alloc.Alloc(count);
  EXPECT_EQ(index_big, index_med);
  EXPECT_EQ(callbacks.num_indices(), static_cast<Index>(2 * count));

  // Next Alloc of smaller size should be half-way to the original.
  // No new indices should be allocated.
  const Index index_med_again = alloc.Alloc(count);
  EXPECT_EQ(index_big + count, index_med_again);
  EXPECT_EQ(callbacks.num_indices(), static_cast<Index>(2 * count));
}
TEST_ALL_SIZES_F(Callbacks_Recycling)

template <class Index>
void Alloc_DisparateSizes_Test(Index count) {
  Callbacks<Index> callbacks;
  IndexAllocator<Index> alloc(callbacks);

  const Index index_1 = alloc.Alloc(count);
  const Index index_2 = alloc.Alloc(count + 1);

  // Freeing index_1 should shift index_2 over.
  alloc.Free(index_1);
  alloc.Defragment();
  EXPECT_TRUE(callbacks.Check(0, index_2, index_1, count + 1));
  EXPECT_EQ(callbacks.NumMoves(), 1);
}
TEST_ALL_SIZES_F(Alloc_DisparateSizes)

template <class Index>
void Defrag_GrowingFreeMiddle_Test(Index count) {
  Callbacks<Index> callbacks;
  IndexAllocator<Index> alloc(callbacks);

  const Index index_1 = alloc.Alloc(1);
  const Index index_2 = alloc.Alloc(2);
  const Index index_3 = alloc.Alloc(3);
  const Index index_4 = alloc.Alloc(4 + count);
  (void)index_1;
  (void)index_2;

  // Freeing index_3 should shift index_4 over.
  alloc.Free(index_3);
  alloc.Defragment();
  EXPECT_TRUE(callbacks.Check(0, index_4, index_3, 4 + count));
  EXPECT_EQ(callbacks.NumMoves(), 1);
}
TEST_ALL_SIZES_F(Defrag_GrowingFreeMiddle)

template <class Index>
void Defrag_GrowingFreeSmallest_Test(Index count) {
  Callbacks<Index> callbacks;
  IndexAllocator<Index> alloc(callbacks);

  const Index index_1 = alloc.Alloc(1);
  const Index index_2 = alloc.Alloc(2);
  const Index index_3 = alloc.Alloc(3);
  const Index index_4 = alloc.Alloc(4 + count);
  (void)index_3;
  (void)index_4;

  // Freeing index_1 should shift index_2, index_3, and index_4 over.
  // Since they are contiguous, all three should be shifted in one call.
  alloc.Free(index_1);
  alloc.Defragment();
  EXPECT_TRUE(callbacks.Check(0, index_2, index_1, 2 + 3 + 4 + count));
  EXPECT_EQ(callbacks.NumMoves(), 1);
}
TEST_ALL_SIZES_F(Defrag_GrowingFreeSmallest)

template <class Index>
void Defrag_ShrinkingFreeLargestOneBlock_Test(Index count) {
  Callbacks<Index> callbacks;
  IndexAllocator<Index> alloc(callbacks);

  const Index index_4 = alloc.Alloc(6 + count);
  const Index index_3 = alloc.Alloc(3);
  const Index index_2 = alloc.Alloc(2 + count);
  const Index index_1 = alloc.Alloc(1);
  (void)index_2;
  (void)index_1;

  // Freeing index_4 should shift index_3, index_2, and index_1 over.
  // Since they're all contiguous, they should move in one chunk.
  alloc.Free(index_4);
  alloc.Defragment();
  EXPECT_TRUE(callbacks.Check(0, index_3, index_4, 3 + 2 + 1 + count));
  EXPECT_EQ(callbacks.NumMoves(), 1);
}
TEST_ALL_SIZES_F(Defrag_ShrinkingFreeLargestOneBlock)

template <class Index>
void Defrag_ShrinkingFreeLargestTwoBlocks_Test(Index count) {
  Callbacks<Index> callbacks;
  IndexAllocator<Index> alloc(callbacks);

  const Index index_4 = alloc.Alloc(5 + count);
  const Index index_3 = alloc.Alloc(3);
  const Index index_2 = alloc.Alloc(2 + count);
  const Index index_1 = alloc.Alloc(1);
  (void)index_2;
  (void)index_1;

  // Freeing index_4 should shift index_2, and index_1 over.
  // Then, there'll still be an unfilled hole of size 2, so index_3 should be
  // shifted over two to fill it.
  alloc.Free(index_4);
  alloc.Defragment();
  EXPECT_TRUE(callbacks.Check(0, index_2, index_4, 2 + 1 + count));
  EXPECT_TRUE(callbacks.Check(1, index_3, index_3 - 2, 3));
  EXPECT_EQ(callbacks.NumMoves(), 2);
}
TEST_ALL_SIZES_F(Defrag_ShrinkingFreeLargestTwoBlocks)

template <class Index>
void Defrag_ShrinkingFreeMiddleOneBlock_Test(Index count) {
  Callbacks<Index> callbacks;
  IndexAllocator<Index> alloc(callbacks);

  const Index index_4 = alloc.Alloc(4 + count);
  const Index index_3 = alloc.Alloc(3 + count);
  const Index index_2 = alloc.Alloc(2 + count);
  const Index index_1 = alloc.Alloc(1);
  (void)index_4;
  (void)index_1;

  // Freeing index_3 should shift index_2 and index_1 over.
  // Since their consecutive, they should be shifted in one call.
  alloc.Free(index_3);
  alloc.Defragment();
  EXPECT_TRUE(callbacks.Check(0, index_2, index_3, 3 + count));
  EXPECT_EQ(callbacks.NumMoves(), 1);
}
TEST_ALL_SIZES_F(Defrag_ShrinkingFreeMiddleOneBlock)

template <class Index>
void Defrag_ShrinkingFreeMiddleTwoBlocks_Test(Index count) {
  Callbacks<Index> callbacks;
  IndexAllocator<Index> alloc(callbacks);

  const Index index_4 = alloc.Alloc(4 + count);
  const Index index_3 = alloc.Alloc(3 + count);
  const Index index_2 = alloc.Alloc(3 + count);
  const Index index_1 = alloc.Alloc(1);
  (void)index_4;
  (void)index_1;

  // Freeing index_3 should shift index_1 over.
  // Then there will still be a big gap left, since index_1 is so small, so
  // we'll need to shift index_2 over too.
  alloc.Free(index_3);
  alloc.Defragment();
  EXPECT_TRUE(callbacks.Check(0, index_1, index_3, 1));
  EXPECT_TRUE(callbacks.Check(1, index_2, index_3 + 1, 3 + count));
  EXPECT_EQ(callbacks.NumMoves(), 2);
}
TEST_ALL_SIZES_F(Defrag_ShrinkingFreeMiddleTwoBlocks)

template <class Index>
void Defrag_ShrinkingFreeSmallest_Test(Index count) {
  typedef Callbacks<Index> CallB;
  CallB callbacks;
  IndexAllocator<Index> alloc(callbacks);

  const Index index_4 = alloc.Alloc(4 + count);
  const Index index_3 = alloc.Alloc(3);
  const Index index_2 = alloc.Alloc(2);
  const Index index_1 = alloc.Alloc(1);
  (void)index_2;
  (void)index_3;
  (void)index_4;

  // Freeing index_1 should shift nothing, since it's at the end.
  alloc.Free(index_1);
  alloc.Defragment();
  EXPECT_EQ(callbacks.NumMoves(), 0);
}
TEST_ALL_SIZES_F(Defrag_ShrinkingFreeSmallest)

template <class Index>
void Defrag_FillMiddle_Test(Index count) {
  Callbacks<Index> callbacks;
  IndexAllocator<Index> alloc(callbacks);

  const Index index_1 = alloc.Alloc(2);
  const Index index_2 = alloc.Alloc(count);
  const Index index_3 = alloc.Alloc(1);
  const Index index_4 = alloc.Alloc(count);
  (void)index_1;
  (void)index_3;

  // Freeing index_2 should shift index_4 into it.
  alloc.Free(index_2);
  alloc.Defragment();
  EXPECT_TRUE(callbacks.Check(0, index_4, index_2, count));
  EXPECT_EQ(callbacks.NumMoves(), 1);
}
TEST_ALL_SIZES_F(Defrag_FillMiddle)

template <class Index>
void Defrag_FillMiddleMiddle_Test(Index count) {
  Callbacks<Index> callbacks;
  IndexAllocator<Index> alloc(callbacks);

  const Index index_1 = alloc.Alloc(8);
  const Index index_2 = alloc.Alloc(count);
  const Index index_3 = alloc.Alloc(9);
  const Index index_4 = alloc.Alloc(count);
  const Index index_5 = alloc.Alloc(10);
  (void)index_1;
  (void)index_3;

  // Freeing index_2 should shift index_4 into it, then index_5 into index_4.
  alloc.Free(index_2);
  alloc.Defragment();
  EXPECT_TRUE(callbacks.Check(0, index_4, index_2, count));
  EXPECT_TRUE(callbacks.Check(1, index_5, index_4, 10));
  EXPECT_EQ(callbacks.NumMoves(), 2);
}
TEST_ALL_SIZES_F(Defrag_FillMiddleMiddle)

template <class Index>
void Defrag_FillStartMiddle_Test(Index count) {
  Callbacks<Index> callbacks;
  IndexAllocator<Index> alloc(callbacks);

  const Index index_1 = alloc.Alloc(count);
  const Index index_2 = alloc.Alloc(8);
  const Index index_3 = alloc.Alloc(count);
  const Index index_4 = alloc.Alloc(9);
  (void)index_2;

  // Freeing index_1 should shift index_3 into it, then index_4 into index_3.
  alloc.Free(index_1);
  alloc.Defragment();
  EXPECT_TRUE(callbacks.Check(0, index_3, index_1, count));
  EXPECT_TRUE(callbacks.Check(1, index_4, index_3, 9));
  EXPECT_EQ(callbacks.NumMoves(), 2);
}
TEST_ALL_SIZES_F(Defrag_FillStartMiddle)

template <class Index>
void Defrag_FillMiddleEnd_Test(Index count) {
  Callbacks<Index> callbacks;
  IndexAllocator<Index> alloc(callbacks);

  const Index index_1 = alloc.Alloc(8);
  const Index index_2 = alloc.Alloc(count);
  const Index index_3 = alloc.Alloc(9);
  const Index index_4 = alloc.Alloc(count);
  (void)index_1;
  (void)index_3;

  // Freeing index_2 should shift index_4 into it.
  alloc.Free(index_2);
  alloc.Defragment();
  EXPECT_TRUE(callbacks.Check(0, index_4, index_2, count));
  EXPECT_EQ(callbacks.NumMoves(), 1);
}
TEST_ALL_SIZES_F(Defrag_FillMiddleEnd)

template <class Index>
void Defrag_FillStartEnd_Test(Index count) {
  Callbacks<Index> callbacks;
  IndexAllocator<Index> alloc(callbacks);

  const Index index_1 = alloc.Alloc(count);
  const Index index_2 = alloc.Alloc(8);
  const Index index_3 = alloc.Alloc(9);
  const Index index_4 = alloc.Alloc(count);
  EXPECT_EQ(index_1, static_cast<Index>(0));
  EXPECT_EQ(index_2, static_cast<Index>(count));
  EXPECT_EQ(index_3, static_cast<Index>(8 + count));
  EXPECT_EQ(index_4, static_cast<Index>(17 + count));

  // Freeing index_1 should shift index_4 into it.
  alloc.Free(index_1);
  alloc.Defragment();
  EXPECT_TRUE(callbacks.Check(0, index_4, index_1, count));
  EXPECT_EQ(callbacks.NumMoves(), 1);
}
TEST_ALL_SIZES_F(Defrag_FillStartEnd)

template <class Index>
void Defrag_TwoTogether_Test(Index count) {
  Callbacks<Index> callbacks;
  IndexAllocator<Index> alloc(callbacks);

  const Index index_1 = alloc.Alloc(20);
  const Index index_2 = alloc.Alloc(8);
  const Index index_3 = alloc.Alloc(9);
  const Index index_4 = alloc.Alloc(21 + count);
  (void)index_3;

  // Freeing index_1 should shift index_2 and index_3 into it,
  // then shift index_4 over.
  alloc.Free(index_1);
  alloc.Defragment();
  EXPECT_TRUE(callbacks.Check(0, index_2, index_1, 17));
  EXPECT_TRUE(callbacks.Check(1, index_4, index_4 - 20, 21 + count));
  EXPECT_EQ(callbacks.NumMoves(), 2);
  EXPECT_EQ(alloc.CountForIndex(0), 8);
  EXPECT_EQ(alloc.CountForIndex(8), 9);
}
TEST_ALL_SIZES_F(Defrag_TwoTogether)

template <class Index>
void Defrag_BigAssortment_Test(Index count) {
  Callbacks<Index> callbacks;
  IndexAllocator<Index> alloc(callbacks);

  const Index index_1 = alloc.Alloc(count);
  const Index index_2 = alloc.Alloc(8);
  const Index index_3 = alloc.Alloc(9);
  const Index index_4 = alloc.Alloc(6);

  // Create a hole of size 8. Only allocations <8 should be able to claim the
  // hole.
  alloc.Free(index_2);
  const Index index_5 = alloc.Alloc(9);
  EXPECT_NE(index_5, index_2);
  const Index index_6 = alloc.Alloc(7);
  EXPECT_EQ(index_6, index_2);

  // The hole is now of size 1, so we should only be able to claim it with
  // allocations of size 1.
  const Index index_7 = alloc.Alloc(2);
  EXPECT_NE(index_7, index_2 + 7);
  const Index index_8 = alloc.Alloc(1);
  EXPECT_EQ(index_8, index_2 + 7);

  // Allocate a bunch more to test defrag.
  const Index index_9 = alloc.Alloc(13);

  EXPECT_EQ(index_1, static_cast<Index>(0));           // size: count
  EXPECT_EQ(index_6, static_cast<Index>(count));       // size: 7 **
  EXPECT_EQ(index_8, static_cast<Index>(7 + count));   // size: 1
  EXPECT_EQ(index_3, static_cast<Index>(8 + count));   // size: 9 **
  EXPECT_EQ(index_4, static_cast<Index>(17 + count));  // size: 6
  EXPECT_EQ(index_5, static_cast<Index>(23 + count));  // size: 9 **
  EXPECT_EQ(index_7, static_cast<Index>(32 + count));  // size: 2
  EXPECT_EQ(index_9, static_cast<Index>(34 + count));  // size: 13

  // Freeing index_3, index_5, and index_6 results in the following moves:
  // index_7 --> index_6  (new hole size is 5)
  // index_8 --> index_6 + 2 (new hole size is 4 + 9 = 13)
  // index_9 --> index_6 + 3
  // index_4 --> index_4 - 1 (shift over one)
  alloc.Free(index_3);
  alloc.Free(index_5);
  alloc.Free(index_6);
  alloc.Defragment();
  EXPECT_TRUE(callbacks.Check(0, index_7, index_6, 2));
  EXPECT_TRUE(callbacks.Check(1, index_8, index_6 + 2, 1));
  EXPECT_TRUE(callbacks.Check(2, index_9, index_6 + 3, 13));
  EXPECT_TRUE(callbacks.Check(3, index_4, index_4 - 1, 6));
  EXPECT_EQ(callbacks.NumMoves(), 4);
  EXPECT_EQ(alloc.CountForIndex(index_1), count);
  EXPECT_EQ(alloc.CountForIndex(index_6), 2);
  EXPECT_EQ(alloc.CountForIndex(index_6 + 2), 1);
  EXPECT_EQ(alloc.CountForIndex(index_6 + 3), 13);
  EXPECT_EQ(alloc.CountForIndex(index_4 - 1), 6);
}
TEST_ALL_SIZES_F(Defrag_BigAssortment)

int main(int argc, char **argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}

