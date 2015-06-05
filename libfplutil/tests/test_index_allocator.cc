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

#include "gtest/gtest.h"
#include "fplutil/index_allocator.h"

using fpl::IndexAllocator;


#define TEST_ALL_SIZES_F(MY_TEST) \
  TEST_F(IndexAllocatorTests, MY_TEST##_int8) { \
    MY_TEST##_Test<int8_t, int8_t>(1); \
    MY_TEST##_Test<int8_t, int8_t>(2); \
  } \
  TEST_F(IndexAllocatorTests, MY_TEST##_uint8) { \
    MY_TEST##_Test<uint8_t, int8_t>(1); \
    MY_TEST##_Test<uint8_t, int8_t>(2); \
  } \
  TEST_F(IndexAllocatorTests, MY_TEST##_int16) { \
    MY_TEST##_Test<int16_t, int16_t>(1); \
    MY_TEST##_Test<int16_t, int16_t>(2); \
  } \
  TEST_F(IndexAllocatorTests, MY_TEST##_uint16) { \
    MY_TEST##_Test<uint16_t, int16_t>(1); \
    MY_TEST##_Test<uint16_t, int16_t>(2); \
  } \
  TEST_F(IndexAllocatorTests, MY_TEST##_int32) { \
    MY_TEST##_Test<int32_t, int32_t>(1); \
    MY_TEST##_Test<int32_t, int32_t>(2); \
  } \
  TEST_F(IndexAllocatorTests, MY_TEST##_uint32) { \
    MY_TEST##_Test<uint32_t, int32_t>(1); \
    MY_TEST##_Test<uint32_t, int32_t>(2); \
    MY_TEST##_Test<uint32_t, int32_t>(5); \
    MY_TEST##_Test<uint32_t, int8_t>(5); \
  }


class IndexAllocatorTests : public ::testing::Test {
protected:
  virtual void SetUp() {}
  virtual void TearDown() {}
};

template<class Index, class Count>
class Callbacks : public IndexAllocator<Index, Count>::CallbackInterface {
  static const Index kInvalidIndex = static_cast<Index>(-1);
  static const Count kInvalidCount = static_cast<Count>(0);

 public:
  Callbacks() :
      num_indices_(0),
      old_index_(kInvalidIndex),
      new_index_(kInvalidIndex),
      num_moves_(0) {
  }
  virtual void SetNumIndices(Index num_indices) { num_indices_ = num_indices; }
  virtual void MoveIndex(Index old_index, Index new_index) {
    old_index_ = old_index;
    new_index_ = new_index;
    num_moves_++;
  }

  Index num_indices() const { return num_indices_; }
  Index old_index() const { return old_index_; }
  Index new_index() const { return new_index_; }
  int num_moves() const { return num_moves_; }

  static Index InvalidIndex() { return kInvalidIndex; }
  static Count InvalidCount() { return kInvalidCount; }

 private:
  Index num_indices_;
  Index old_index_;
  Index new_index_;
  int num_moves_;
};

// Test allocating and freeing one index.
template<class Index, class Count>
void AllocAndFree_OneIndex_Test(Count count) {
  Callbacks<Index, Count> callbacks;
  IndexAllocator<Index, Count> alloc(callbacks);

  EXPECT_TRUE(alloc.Empty());
  const Index index1 = alloc.Alloc(count);
  EXPECT_FALSE(alloc.Empty());
  alloc.Free(index1);
  EXPECT_TRUE(alloc.Empty());
}
TEST_ALL_SIZES_F(AllocAndFree_OneIndex)

// Test allocating two indices, then freeing them in most-recent to
// first-allocated.
template<class Index, class Count>
void AllocAndFree_TwoIndicesInOrder_Test(Count count) {
  Callbacks<Index, Count> callbacks;
  IndexAllocator<Index, Count> alloc(callbacks);

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
template<class Index, class Count>
void AllocAndFree_TwoIndicesReverseOrder_Test(Count count) {
  Callbacks<Index, Count> callbacks;
  IndexAllocator<Index, Count> alloc(callbacks);

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
template<class Index, class Count>
void AllocAndFree_ThreeIndicesScatteredOrder_Test(Count count) {
  Callbacks<Index, Count> callbacks;
  IndexAllocator<Index, Count> alloc(callbacks);

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
template<class Index, class Count>
void Callbacks_SetNumIndices_Test(Count count) {
  Callbacks<Index, Count> callbacks;
  IndexAllocator<Index, Count> alloc(callbacks);

  EXPECT_EQ(callbacks.num_indices(), static_cast<Index>(0));
  const Index index1 = alloc.Alloc(count);
  EXPECT_EQ(callbacks.num_indices(), static_cast<Index>(count));
  alloc.Free(index1);
  EXPECT_EQ(callbacks.num_indices(), static_cast<Index>(count));
  alloc.Defragment();
  EXPECT_EQ(callbacks.num_indices(), static_cast<Index>(0));
}
TEST_ALL_SIZES_F(Callbacks_SetNumIndices)

// Test that index 1 gets backfilled into index 0 after index 0 is freed.
template<class Index, class Count>
void Callbacks_Defragment_Test(Count count) {
  Callbacks<Index, Count> callbacks;
  IndexAllocator<Index, Count> alloc(callbacks);

  const Index index0 = alloc.Alloc(count);
  alloc.Alloc(count);
  alloc.Free(index0);
  alloc.Defragment();
  EXPECT_EQ(callbacks.old_index(), static_cast<Index>(count));
  EXPECT_EQ(callbacks.new_index(), static_cast<Index>(0));
}
TEST_ALL_SIZES_F(Callbacks_Defragment)

// Test Defragment() when only the last index has been freed.
template<class Index, class Count>
void Callbacks_DefragmentAtEnd_Test(Count count) {
  typedef Callbacks<Index, Count> CallB;
  CallB callbacks;
  IndexAllocator<Index, Count> alloc(callbacks);

  alloc.Alloc(count);
  alloc.Alloc(count);
  const Index index = alloc.Alloc(count);
  alloc.Free(index);
  alloc.Defragment();
  EXPECT_EQ(callbacks.old_index(), CallB::InvalidIndex());
  EXPECT_EQ(callbacks.new_index(), CallB::InvalidIndex());
  EXPECT_EQ(callbacks.num_indices(), static_cast<Index>(2 * count));
}
TEST_ALL_SIZES_F(Callbacks_DefragmentAtEnd)

// Call Alloc() and Free() on several indices and then Defragment().
// Ensure we end up with number of Allocs() - number of Frees() as the
// number of indices.
template<class Index, class Count>
void Callbacks_DefragmentStartMiddleEnd_Test(Count count) {
  Callbacks<Index, Count> callbacks;
  IndexAllocator<Index, Count> alloc(callbacks);

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
template<class Index, class Count>
void Callbacks_Recycling_Test(Count count) {
  Callbacks<Index, Count> callbacks;
  IndexAllocator<Index, Count> alloc(callbacks);

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

template<class Index, class Count>
void Callbacks_GrowingFreeMiddle_Test(Count count) {
  Callbacks<Index, Count> callbacks;
  IndexAllocator<Index, Count> alloc(callbacks);

  const Index index_1 = alloc.Alloc(1);
  const Index index_2 = alloc.Alloc(2);
  const Index index_3 = alloc.Alloc(3);
  const Index index_4 = alloc.Alloc(4 + count);
  EXPECT_EQ(index_1, static_cast<Index>(0));
  EXPECT_EQ(index_2, static_cast<Index>(1));
  EXPECT_EQ(index_3, static_cast<Index>(3));
  EXPECT_EQ(index_4, static_cast<Index>(6));

  // Freeing index_3 should shift index_4 over.
  alloc.Free(index_3);
  alloc.Defragment();
  EXPECT_EQ(callbacks.old_index(), static_cast<Index>(6));
  EXPECT_EQ(callbacks.new_index(), static_cast<Index>(3));
  EXPECT_EQ(callbacks.num_moves(), 1);
}
TEST_ALL_SIZES_F(Callbacks_GrowingFreeMiddle)

template<class Index, class Count>
void Callbacks_GrowingFreeSmallest_Test(Count count) {
  Callbacks<Index, Count> callbacks;
  IndexAllocator<Index, Count> alloc(callbacks);

  const Index index_1 = alloc.Alloc(1);
  const Index index_2 = alloc.Alloc(2);
  const Index index_3 = alloc.Alloc(3);
  const Index index_4 = alloc.Alloc(4 + count);
  EXPECT_EQ(index_1, static_cast<Index>(0));
  EXPECT_EQ(index_2, static_cast<Index>(1));
  EXPECT_EQ(index_3, static_cast<Index>(3));
  EXPECT_EQ(index_4, static_cast<Index>(6));

  // Freeing index_1 should shift index_2, index_3, and index_4 over.
  // Callbacks only lets us check index_4 though.
  alloc.Free(index_1);
  alloc.Defragment();
  EXPECT_EQ(callbacks.old_index(), static_cast<Index>(6));
  EXPECT_EQ(callbacks.new_index(), static_cast<Index>(5));
  EXPECT_EQ(callbacks.num_moves(), 3);
}
TEST_ALL_SIZES_F(Callbacks_GrowingFreeSmallest)

template<class Index, class Count>
void Callbacks_ShrinkingFreeLargest_Test(Count count) {
  Callbacks<Index, Count> callbacks;
  IndexAllocator<Index, Count> alloc(callbacks);

  const Index index_4 = alloc.Alloc(4 + count);
  const Index index_3 = alloc.Alloc(3);
  const Index index_2 = alloc.Alloc(2);
  const Index index_1 = alloc.Alloc(1);
  EXPECT_EQ(index_4, static_cast<Index>(0));
  EXPECT_EQ(index_3, static_cast<Index>(4 + count));
  EXPECT_EQ(index_2, static_cast<Index>(7 + count));
  EXPECT_EQ(index_1, static_cast<Index>(9 + count));

  // Freeing index_4 should shift index_3, index_2, and index_1 over.
  alloc.Free(index_4);
  alloc.Defragment();
  EXPECT_EQ(callbacks.old_index(), static_cast<Index>(9 + count));
  EXPECT_EQ(callbacks.new_index(), static_cast<Index>(5));
  EXPECT_EQ(callbacks.num_moves(), 3);
}
TEST_ALL_SIZES_F(Callbacks_ShrinkingFreeLargest)

template<class Index, class Count>
void Callbacks_ShrinkingFreeMiddle_Test(Count count) {
  Callbacks<Index, Count> callbacks;
  IndexAllocator<Index, Count> alloc(callbacks);

  const Index index_4 = alloc.Alloc(4 + count);
  const Index index_3 = alloc.Alloc(3);
  const Index index_2 = alloc.Alloc(2);
  const Index index_1 = alloc.Alloc(1);
  EXPECT_EQ(index_4, static_cast<Index>(0));
  EXPECT_EQ(index_3, static_cast<Index>(4 + count));
  EXPECT_EQ(index_2, static_cast<Index>(7 + count));
  EXPECT_EQ(index_1, static_cast<Index>(9 + count));

  // Freeing index_3 should shift index_2 and index_1 over.
  alloc.Free(index_3);
  alloc.Defragment();
  EXPECT_EQ(callbacks.old_index(), static_cast<Index>(9 + count));
  EXPECT_EQ(callbacks.new_index(), static_cast<Index>(6 + count));
  EXPECT_EQ(callbacks.num_moves(), 2);
}
TEST_ALL_SIZES_F(Callbacks_ShrinkingFreeMiddle)

template<class Index, class Count>
void Callbacks_ShrinkingFreeSmallest_Test(Count count) {
  typedef Callbacks<Index, Count> CallB;
  CallB callbacks;
  IndexAllocator<Index, Count> alloc(callbacks);

  const Index index_4 = alloc.Alloc(4 + count);
  const Index index_3 = alloc.Alloc(3);
  const Index index_2 = alloc.Alloc(2);
  const Index index_1 = alloc.Alloc(1);
  EXPECT_EQ(index_4, static_cast<Index>(0));
  EXPECT_EQ(index_3, static_cast<Index>(4 + count));
  EXPECT_EQ(index_2, static_cast<Index>(7 + count));
  EXPECT_EQ(index_1, static_cast<Index>(9 + count));

  // Freeing index_1 should shift nothing, since it's at the end.
  alloc.Free(index_1);
  alloc.Defragment();
  EXPECT_EQ(callbacks.old_index(), CallB::InvalidIndex());
  EXPECT_EQ(callbacks.new_index(), CallB::InvalidIndex());
  EXPECT_EQ(callbacks.num_moves(), 0);
}
TEST_ALL_SIZES_F(Callbacks_ShrinkingFreeSmallest)

template<class Index, class Count>
void Callbacks_FillMiddle_Test(Count count) {
  Callbacks<Index, Count> callbacks;
  IndexAllocator<Index, Count> alloc(callbacks);

  const Index index_1 = alloc.Alloc(2);
  const Index index_2 = alloc.Alloc(count);
  const Index index_3 = alloc.Alloc(1);
  const Index index_4 = alloc.Alloc(count);
  EXPECT_EQ(index_1, static_cast<Index>(0));
  EXPECT_EQ(index_2, static_cast<Index>(2));
  EXPECT_EQ(index_3, static_cast<Index>(2 + count));
  EXPECT_EQ(index_4, static_cast<Index>(3 + count));

  // Freeing index_2 should shift index_4 into it.
  alloc.Free(index_2);
  alloc.Defragment();
  EXPECT_EQ(callbacks.old_index(), index_4);
  EXPECT_EQ(callbacks.new_index(), index_2);
  EXPECT_EQ(callbacks.num_moves(), 1);
}
TEST_ALL_SIZES_F(Callbacks_FillMiddle)

template<class Index, class Count>
void Callbacks_FillMiddleMiddle_Test(Count count) {
  Callbacks<Index, Count> callbacks;
  IndexAllocator<Index, Count> alloc(callbacks);

  const Index index_1 = alloc.Alloc(8);
  const Index index_2 = alloc.Alloc(count);
  const Index index_3 = alloc.Alloc(9);
  const Index index_4 = alloc.Alloc(count);
  const Index index_5 = alloc.Alloc(10);
  EXPECT_EQ(index_1, static_cast<Index>(0));
  EXPECT_EQ(index_2, static_cast<Index>(8));
  EXPECT_EQ(index_3, static_cast<Index>(8 + count));
  EXPECT_EQ(index_4, static_cast<Index>(17 + count));
  EXPECT_EQ(index_5, static_cast<Index>(17 + 2 * count));

  // Freeing index_2 should shift index_4 into it, then index_5 into index_4.
  alloc.Free(index_2);
  alloc.Defragment();
  EXPECT_EQ(callbacks.old_index(), index_5);
  EXPECT_EQ(callbacks.new_index(), index_4);
  EXPECT_EQ(callbacks.num_moves(), 2);
}
TEST_ALL_SIZES_F(Callbacks_FillMiddleMiddle)

template<class Index, class Count>
void Callbacks_FillStartMiddle_Test(Count count) {
  Callbacks<Index, Count> callbacks;
  IndexAllocator<Index, Count> alloc(callbacks);

  const Index index_1 = alloc.Alloc(count);
  const Index index_2 = alloc.Alloc(8);
  const Index index_3 = alloc.Alloc(count);
  const Index index_4 = alloc.Alloc(9);
  EXPECT_EQ(index_1, static_cast<Index>(0));
  EXPECT_EQ(index_2, static_cast<Index>(count));
  EXPECT_EQ(index_3, static_cast<Index>(8 + count));
  EXPECT_EQ(index_4, static_cast<Index>(8 + 2 * count));

  // Freeing index_1 should shift index_3 into it, then index_4 into index_3.
  alloc.Free(index_1);
  alloc.Defragment();
  EXPECT_EQ(callbacks.old_index(), index_4);
  EXPECT_EQ(callbacks.new_index(), index_3);
  EXPECT_EQ(callbacks.num_moves(), 2);
}
TEST_ALL_SIZES_F(Callbacks_FillStartMiddle)

template<class Index, class Count>
void Callbacks_FillMiddleEnd_Test(Count count) {
  Callbacks<Index, Count> callbacks;
  IndexAllocator<Index, Count> alloc(callbacks);

  const Index index_1 = alloc.Alloc(8);
  const Index index_2 = alloc.Alloc(count);
  const Index index_3 = alloc.Alloc(9);
  const Index index_4 = alloc.Alloc(count);
  EXPECT_EQ(index_1, static_cast<Index>(0));
  EXPECT_EQ(index_2, static_cast<Index>(8));
  EXPECT_EQ(index_3, static_cast<Index>(8 + count));
  EXPECT_EQ(index_4, static_cast<Index>(17 + count));

  // Freeing index_2 should shift index_4 into it.
  alloc.Free(index_2);
  alloc.Defragment();
  EXPECT_EQ(callbacks.old_index(), index_4);
  EXPECT_EQ(callbacks.new_index(), index_2);
  EXPECT_EQ(callbacks.num_moves(), 1);
}
TEST_ALL_SIZES_F(Callbacks_FillMiddleEnd)

template<class Index, class Count>
void Callbacks_FillStartEnd_Test(Count count) {
  Callbacks<Index, Count> callbacks;
  IndexAllocator<Index, Count> alloc(callbacks);

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
  EXPECT_EQ(callbacks.old_index(), index_4);
  EXPECT_EQ(callbacks.new_index(), index_1);
  EXPECT_EQ(callbacks.num_moves(), 1);
}
TEST_ALL_SIZES_F(Callbacks_FillStartEnd)

#if !defined(__ANDROID__)
int main(int argc, char **argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
#endif // !defined(__ANDROID__)
