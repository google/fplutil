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

#include <algorithm>
#include <stddef.h>
#include <stdint.h>
#include "gtest/gtest.h"
#include "fplutil/variable_size.h"

using fplutil::VariableSizeCalculator;
using fplutil::VariableSizeBuilder;

class VariableSizeTests : public ::testing::Test {
protected:
  virtual void SetUp() {}
  virtual void TearDown() {}
};

template<class T>
static inline size_t Calculator_OneType() {
  VariableSizeCalculator s(0);
  const size_t start_offset = s.Type<T>();
  // The first offset that gets returned should always be 0.
  EXPECT_EQ(start_offset, 0u);
  return s.size();
}

// Basic types should return the correct size.
TEST_F(VariableSizeTests, Calculator_OneType_Test) {
  EXPECT_EQ(Calculator_OneType<uint8_t>(), sizeof(uint8_t));
  EXPECT_EQ(Calculator_OneType<int8_t>(), sizeof(int8_t));
  EXPECT_EQ(Calculator_OneType<int16_t>(), sizeof(int16_t));
  EXPECT_EQ(Calculator_OneType<int>(), sizeof(int));
  EXPECT_EQ(Calculator_OneType<int64_t>(), sizeof(int64_t));
  EXPECT_EQ(Calculator_OneType<char*>(), sizeof(char*));
}

template<class T>
static inline size_t Calculator_OneArray(size_t count) {
  VariableSizeCalculator s(0);
  const size_t start_offset = s.Array<T>(count);
  // The first offset that gets returned should always be 0.
  EXPECT_EQ(start_offset, 0u);
  return s.size();
}

// Arrays of basic types should return the correct size.
TEST_F(VariableSizeTests, Calculator_OneArray_Test) {
  EXPECT_EQ(Calculator_OneArray<uint8_t>(10), 10 * sizeof(uint8_t));
  EXPECT_EQ(Calculator_OneArray<int8_t>(12), 12 * sizeof(int8_t));
  EXPECT_EQ(Calculator_OneArray<int16_t>(7), 7 * sizeof(int16_t));
  EXPECT_EQ(Calculator_OneArray<int>(16), 16 * sizeof(int));
  EXPECT_EQ(Calculator_OneArray<int64_t>(1001), 1001 * sizeof(int64_t));
  EXPECT_EQ(Calculator_OneArray<char*>(1), 1 * sizeof(char*));
  EXPECT_EQ(Calculator_OneArray<char*>(11), 11 * sizeof(char*));
}

template<class T0, class T1>
static inline void Calculator_TypeAlignment_Test() {
  VariableSizeCalculator s(0);

  // The first offset that gets returned should always be 0.
  const size_t offset0 = s.Type<T0>();
  EXPECT_EQ(offset0, 0u);

  // The second offset is at least as big as T0 since it comes after T0,
  // and is aligned to T1, which should be the same size as T1 for simple types.
  const size_t offset1 = s.Type<T1>();
  EXPECT_EQ(offset1, std::max(sizeof(T0), sizeof(T1)));
}

// Test alignment of a bigger type following a smaller type.
TEST_F(VariableSizeTests, Calculator_TypeAlignment_SmallToBig_Test) {
  Calculator_TypeAlignment_Test<uint8_t, int16_t>();
  Calculator_TypeAlignment_Test<uint8_t, int32_t>();
  Calculator_TypeAlignment_Test<uint8_t, int64_t>();
  Calculator_TypeAlignment_Test<uint16_t, int32_t>();
  Calculator_TypeAlignment_Test<uint16_t, int64_t>();
  Calculator_TypeAlignment_Test<uint32_t, int64_t>();
  Calculator_TypeAlignment_Test<char, char*>();
}

// Test alignment of a smaller type following a bigger type.
TEST_F(VariableSizeTests, Calculator_TypeAlignment_BigToSmall_Test) {
  Calculator_TypeAlignment_Test<int16_t, uint8_t>();
  Calculator_TypeAlignment_Test<int32_t, uint8_t>();
  Calculator_TypeAlignment_Test<int64_t, uint8_t>();
  Calculator_TypeAlignment_Test<int32_t, uint16_t>();
  Calculator_TypeAlignment_Test<int64_t, uint16_t>();
  Calculator_TypeAlignment_Test<int64_t, uint32_t>();
  Calculator_TypeAlignment_Test<char*, char>();
}

template<class T0, class T1>
static inline void Calculator_ArrayAlignment_Test() {
  static const size_t kCount0 = 5;
  VariableSizeCalculator s(0);

  // The first offset that gets returned should always be 0.
  const size_t offset0 = s.Array<T0>(kCount0);
  EXPECT_EQ(offset0, 0);

  // The second offset is at least as big as T0 since it comes after T0,
  // and is aligned to T1, which should be the same size as T1 for simple types.
  const size_t offset1 = s.Type<T1>(3);
  EXPECT_EQ(offset1, (kCount0 * sizeof(T0) + sizeof(T1) - 1) & ~(sizeof(T1) - 1));
}

// Test alignment of a an array of bigger types following an array of smaller types.
TEST_F(VariableSizeTests, Calculator_ArrayAlignment_SmallToBig_Test) {
  Calculator_TypeAlignment_Test<uint8_t, int16_t>();
  Calculator_TypeAlignment_Test<uint8_t, int32_t>();
  Calculator_TypeAlignment_Test<uint8_t, int64_t>();
  Calculator_TypeAlignment_Test<uint16_t, int32_t>();
  Calculator_TypeAlignment_Test<uint16_t, int64_t>();
  Calculator_TypeAlignment_Test<uint32_t, int64_t>();
}

// Test alignment of a an array of smaller types following an array of bigger types.
TEST_F(VariableSizeTests, Calculator_ArrayAlignment_BigToSmall_Test) {
  Calculator_TypeAlignment_Test<int16_t, uint8_t>();
  Calculator_TypeAlignment_Test<int32_t, uint8_t>();
  Calculator_TypeAlignment_Test<int64_t, uint8_t>();
  Calculator_TypeAlignment_Test<int32_t, uint16_t>();
  Calculator_TypeAlignment_Test<int64_t, uint16_t>();
  Calculator_TypeAlignment_Test<int64_t, uint32_t>();
}

// Test raw allocations.
TEST_F(VariableSizeTests, Calculator_Raw) {
  VariableSizeCalculator s(0);

  const size_t offset0 = s.Raw(101, 8);
  EXPECT_EQ(offset0, 0u);

  const size_t offset1 = s.Raw(10, 4);
  EXPECT_EQ(offset1, 104u);

  const size_t offset2 = s.Raw(6, 2);
  EXPECT_EQ(offset2, 114u);

  const size_t offset3 = s.Raw(16, 16);
  EXPECT_EQ(offset3, 128u);

  const size_t offset4 = s.Raw(128, 128);
  EXPECT_EQ(offset4, 256u);

  const size_t offset5 = s.Raw(1, 1);
  EXPECT_EQ(offset5, 384u);

  const size_t offset6 = s.Raw(32, 16);
  EXPECT_EQ(offset6, 400u);

  EXPECT_EQ(s.size(), 432u);
}

// Test builder.
TEST_F(VariableSizeTests, Builder) {
  struct VariableClass {
    static size_t Size(size_t count0, size_t count1, size_t count2) {
      VariableSizeCalculator c(sizeof(VariableClass));
      c.Array<char>(count0);
      c.Array<uint32_t>(count1);
      c.Array<void*>(count2);
      return c.size();
    }

    static VariableClass* CreateInPlace(size_t count0, size_t count1, size_t count2, void* buffer, size_t buffer_size) {
      VariableClass* p = new(buffer) VariableClass();

      VariableSizeBuilder b(p, sizeof(*p));
      p->a0 = b.Array<char>(count0);
      p->a1 = b.Array<uint32_t>(count1);
      p->a2 = b.Array<void*>(count2);
      EXPECT_LE(b.size(), buffer_size);
      return p;
    }

   private:
    VariableClass() {}

   public:                     // offset   size
    int32_t m0;               // 0        4
    int8_t m1;                // 4        1
    int16_t m2[4];            // 6        8
    char* a0;                 // 16       s (s = sizeof(pointer))
    uint32_t* a1;             // 16+s     s
    uint16_t m3;              // 16+2s    2
    void** a2;                // 16+3s    s
  };                          // 16+4s <== total size of base class
  EXPECT_EQ(sizeof(VariableClass), 16u + 4u * sizeof(void*));

                                     // item  array   padding
                                     // size   size    size
  static const size_t kLength0 = 5;  //  x1   = 5       3
  static const size_t kLength1 = 10; //  x4   = 40      0
  static const size_t kLength2 = 15; //  xs   = 15s     0
                                     //         48 + 15s <-- total size of variable arrays

  // Test calculator.
  EXPECT_EQ(VariableClass::Size(kLength0, kLength1, kLength2),
            64u + 19u * sizeof(void*)); // = 16+4s + 48+15s

  // Test builder.
  uint8_t buffer[256];
  VariableClass* p = VariableClass::CreateInPlace(kLength0, kLength1, kLength2, buffer, sizeof(buffer));
  EXPECT_EQ(reinterpret_cast<uint8_t*>(p->a0), buffer + sizeof(VariableClass));
  EXPECT_EQ(reinterpret_cast<uint8_t*>(p->a1), buffer + sizeof(VariableClass) + 8);
  EXPECT_EQ(reinterpret_cast<uint8_t*>(p->a2), buffer + sizeof(VariableClass) + 48);
}

int main(int argc, char **argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}

