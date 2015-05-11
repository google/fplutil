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
    MY_TEST##_Test<int8_t>(); \
  } \
  TEST_F(IndexAllocatorTests, MY_TEST##_uint8) { \
    MY_TEST##_Test<uint8_t>(); \
  } \
  TEST_F(IndexAllocatorTests, MY_TEST##_int16) { \
    MY_TEST##_Test<int16_t>(); \
  } \
  TEST_F(IndexAllocatorTests, MY_TEST##_uint16) { \
    MY_TEST##_Test<uint16_t>(); \
  } \
  TEST_F(IndexAllocatorTests, MY_TEST##_int32) { \
    MY_TEST##_Test<int32_t>(); \
  } \
  TEST_F(IndexAllocatorTests, MY_TEST##_uint32) { \
    MY_TEST##_Test<uint32_t>(); \
  }


class IndexAllocatorTests : public ::testing::Test {
protected:
  virtual void SetUp() {}
  virtual void TearDown() {}
};

template<class Index>
class Callbacks : public IndexAllocator<Index>::CallbackInterface {
  static const Index kInvalidIndex = static_cast<Index>(-1);

 public:
  Callbacks() :
      num_indices_(0),
      old_index_(kInvalidIndex),
      new_index_(kInvalidIndex) {
  }
  virtual void SetNumIndices(Index num_indices) { num_indices_ = num_indices; }
  virtual void MoveIndex(Index old_index, Index new_index) {
    old_index_ = old_index;
    new_index_ = new_index;
  }

  Index num_indices() const { return num_indices_; }
  Index old_index() const { return old_index_; }
  Index new_index() const { return new_index_; }

  static Index InvalidIndex() { return kInvalidIndex; }

 private:
  Index num_indices_;
  Index old_index_;
  Index new_index_;
};

// Test allocating and freeing one index.
template<class Index>
void AllocAndFree_OneIndex_Test() {
  Callbacks<Index> callbacks;
  IndexAllocator<Index> alloc(callbacks);

  EXPECT_TRUE(alloc.Empty());
  const Index index1 = alloc.Alloc();
  EXPECT_FALSE(alloc.Empty());
  alloc.Free(index1);
  EXPECT_TRUE(alloc.Empty());
}
TEST_ALL_SIZES_F(AllocAndFree_OneIndex)

// Test allocating two indices, then freeing them in most-recent to
// first-allocated.
template<class Index>
void AllocAndFree_TwoIndicesInOrder_Test() {
  Callbacks<Index> callbacks;
  IndexAllocator<Index> alloc(callbacks);

  EXPECT_TRUE(alloc.Empty());
  const Index index1 = alloc.Alloc();
  const Index index2 = alloc.Alloc();
  EXPECT_FALSE(alloc.Empty());
  EXPECT_NE(index1, index2);
  alloc.Free(index2);
  alloc.Free(index1);
  EXPECT_TRUE(alloc.Empty());
}
TEST_ALL_SIZES_F(AllocAndFree_TwoIndicesInOrder)

// Test allocating two indices, then freeing them in first-allocated to
// most-recent.
template<class Index>
void AllocAndFree_TwoIndicesReverseOrder_Test() {
  Callbacks<Index> callbacks;
  IndexAllocator<Index> alloc(callbacks);

  EXPECT_TRUE(alloc.Empty());
  const Index index1 = alloc.Alloc();
  const Index index2 = alloc.Alloc();
  EXPECT_FALSE(alloc.Empty());
  EXPECT_NE(index1, index2);
  alloc.Free(index1);
  alloc.Free(index2);
  EXPECT_TRUE(alloc.Empty());
}
TEST_ALL_SIZES_F(AllocAndFree_TwoIndicesReverseOrder)

// Test allocating three indices, then freeing them in a scattered order.
template<class Index>
void AllocAndFree_ThreeIndicesScatteredOrder_Test() {
  Callbacks<Index> callbacks;
  IndexAllocator<Index> alloc(callbacks);

  EXPECT_TRUE(alloc.Empty());
  const Index index1 = alloc.Alloc();
  const Index index2 = alloc.Alloc();
  const Index index3 = alloc.Alloc();
  EXPECT_FALSE(alloc.Empty());
  EXPECT_NE(index1, index2);
  EXPECT_NE(index2, index3);
  alloc.Free(index2);
  alloc.Free(index1);
  alloc.Free(index3);
  EXPECT_TRUE(alloc.Empty());
}
TEST_ALL_SIZES_F(AllocAndFree_ThreeIndicesScatteredOrder)

// Test that the number of indices increases when Alloc() is called, and
// only decreases when Defragment() is called.
template<class Index>
void Callbacks_SetNumIndices_Test() {
  Callbacks<Index> callbacks;
  IndexAllocator<Index> alloc(callbacks);

  EXPECT_EQ(callbacks.num_indices(), static_cast<Index>(0));
  const Index index1 = alloc.Alloc();
  EXPECT_EQ(callbacks.num_indices(), static_cast<Index>(1));
  alloc.Free(index1);
  EXPECT_EQ(callbacks.num_indices(), static_cast<Index>(1));
  alloc.Defragment();
  EXPECT_EQ(callbacks.num_indices(), static_cast<Index>(0));
}
TEST_ALL_SIZES_F(Callbacks_SetNumIndices)

// Test that index 1 gets backfilled into index 0 after index 0 is freed.
template<class Index>
void Callbacks_Defragment_Test() {
  Callbacks<Index> callbacks;
  IndexAllocator<Index> alloc(callbacks);

  const Index index0 = alloc.Alloc();
  alloc.Alloc();
  alloc.Free(index0);
  alloc.Defragment();
  EXPECT_EQ(callbacks.old_index(), static_cast<Index>(1));
  EXPECT_EQ(callbacks.new_index(), static_cast<Index>(0));
}
TEST_ALL_SIZES_F(Callbacks_Defragment)

// Test Defragment() when only the last index has been freed.
template<class Index>
void Callbacks_DefragmentAtEnd_Test() {
  Callbacks<Index> callbacks;
  IndexAllocator<Index> alloc(callbacks);

  alloc.Alloc();
  alloc.Alloc();
  const Index index = alloc.Alloc();
  alloc.Free(index);
  alloc.Defragment();
  EXPECT_EQ(callbacks.old_index(), Callbacks<Index>::InvalidIndex());
  EXPECT_EQ(callbacks.new_index(), Callbacks<Index>::InvalidIndex());
  EXPECT_EQ(callbacks.num_indices(), static_cast<Index>(2));
}
TEST_ALL_SIZES_F(Callbacks_DefragmentAtEnd)

// Call Alloc() and Free() on several indices and then Defragment().
// Ensure we end up with number of Allocs() - number of Frees() as the
// number of indices.
template<class Index>
void Callbacks_DefragmentStartMiddleEnd_Test() {
  Callbacks<Index> callbacks;
  IndexAllocator<Index> alloc(callbacks);

  const Index index_start = alloc.Alloc();
  alloc.Alloc();
  const Index index_middle0 = alloc.Alloc();
  const Index index_middle1 = alloc.Alloc();
  alloc.Alloc();
  const Index index_end = alloc.Alloc();

  alloc.Free(index_middle1);
  alloc.Free(index_middle0);
  alloc.Free(index_end);
  alloc.Free(index_start);

  alloc.Defragment();
  EXPECT_EQ(callbacks.num_indices(), static_cast<Index>(2));
}
TEST_ALL_SIZES_F(Callbacks_DefragmentStartMiddleEnd)

#if !defined(__ANDROID__)
int main(int argc, char **argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
#endif // !defined(__ANDROID__)
