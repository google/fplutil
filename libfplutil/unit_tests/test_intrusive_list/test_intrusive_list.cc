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

#include <algorithm>
#include <functional>
#include "gtest/gtest.h"
#include "fplutil/intrusive_list.h"

// EXPECT_DEATH tests don't work on Android or Windows.
#if defined(__ANDROID__) || defined(_MSC_VER)
#define NO_DEATH_TESTS
#endif  // __ANDROID__

class IntegerListNode {
 public:
  IntegerListNode(int value) : node(), value_(value) {}
  // Older versions of Visual Studio don't generate move constructors or move
  // assignment operators.
  IntegerListNode(IntegerListNode&& other) { *this = std::move(other); }
  IntegerListNode& operator=(IntegerListNode&& other) {
    value_ = other.value_;
    node = std::move(other.node);
    return *this;
  }

  int value() const { return value_; }
  fplutil::intrusive_list_node node;

 private:
  int value_;

  // Disallow copying.
  IntegerListNode(IntegerListNode&);
  IntegerListNode& operator=(IntegerListNode&);
};

bool IntegerListNodeComparitor(const IntegerListNode& a,
                               const IntegerListNode& b) {
  return a.value() < b.value();
}

bool operator<(const IntegerListNode& a, const IntegerListNode& b) {
  return a.value() < b.value();
}

bool operator==(const IntegerListNode& a, const IntegerListNode& b) {
  return a.value() == b.value();
}

class intrusive_list_test : public testing::Test {
 protected:
  intrusive_list_test()
      : list_(&IntegerListNode::node),
        one_(1),
        two_(2),
        three_(3),
        four_(4),
        five_(5),
        six_(6),
        seven_(7),
        eight_(8),
        nine_(9),
        ten_(10),
        twenty_(20),
        thirty_(30),
        fourty_(40),
        fifty_(50) {}

  fplutil::intrusive_list<IntegerListNode> list_;
  IntegerListNode one_;
  IntegerListNode two_;
  IntegerListNode three_;
  IntegerListNode four_;
  IntegerListNode five_;
  IntegerListNode six_;
  IntegerListNode seven_;
  IntegerListNode eight_;
  IntegerListNode nine_;
  IntegerListNode ten_;
  IntegerListNode twenty_;
  IntegerListNode thirty_;
  IntegerListNode fourty_;
  IntegerListNode fifty_;
};

TEST_F(intrusive_list_test, push_back) {
  EXPECT_TRUE(!one_.node.in_list());
  EXPECT_TRUE(!two_.node.in_list());
  EXPECT_TRUE(!three_.node.in_list());
  EXPECT_TRUE(!four_.node.in_list());
  EXPECT_TRUE(!five_.node.in_list());

  list_.push_back(one_);
  list_.push_back(two_);
  list_.push_back(three_);
  list_.push_back(four_);
  list_.push_back(five_);

  EXPECT_TRUE(one_.node.in_list());
  EXPECT_TRUE(two_.node.in_list());
  EXPECT_TRUE(three_.node.in_list());
  EXPECT_TRUE(four_.node.in_list());
  EXPECT_TRUE(five_.node.in_list());

  auto iter = list_.begin();
  EXPECT_EQ(1, iter->value());
  ++iter;
  EXPECT_EQ(2, iter->value());
  ++iter;
  EXPECT_EQ(3, iter->value());
  ++iter;
  EXPECT_EQ(4, iter->value());
  ++iter;
  EXPECT_EQ(5, iter->value());
  ++iter;
  EXPECT_EQ(list_.end(), iter);

  EXPECT_EQ(1, list_.front().value());
  EXPECT_EQ(5, list_.back().value());
}

#ifndef NO_DEATH_TESTS
TEST_F(intrusive_list_test, push_back_failure) {
  list_.push_back(one_);
  list_.push_back(two_);
  list_.push_back(three_);
  list_.push_back(four_);
  list_.push_back(five_);
  EXPECT_DEATH(list_.push_back(five_), ".");
}
#endif  // NO_DEATH_TESTS

TEST_F(intrusive_list_test, pop_back) {
  list_.push_back(one_);
  list_.push_back(two_);
  list_.push_back(three_);
  list_.push_back(four_);
  list_.push_back(five_);

  EXPECT_EQ(5, list_.back().value());
  list_.pop_back();
  EXPECT_EQ(4, list_.back().value());
  list_.pop_back();
  EXPECT_EQ(3, list_.back().value());
  list_.pop_back();
  list_.push_back(four_);
  EXPECT_EQ(4, list_.back().value());
}

TEST_F(intrusive_list_test, push_front) {
  list_.push_front(one_);
  list_.push_front(two_);
  list_.push_front(three_);
  list_.push_front(four_);
  list_.push_front(five_);

  auto iter = list_.begin();
  EXPECT_EQ(5, iter->value());
  ++iter;
  EXPECT_EQ(4, iter->value());
  ++iter;
  EXPECT_EQ(3, iter->value());
  ++iter;
  EXPECT_EQ(2, iter->value());
  ++iter;
  EXPECT_EQ(1, iter->value());
  ++iter;
  EXPECT_EQ(list_.end(), iter);

  EXPECT_EQ(5, list_.front().value());
  EXPECT_EQ(1, list_.back().value());
}

#ifndef NO_DEATH_TESTS
TEST_F(intrusive_list_test, push_front_failure) {
  list_.push_front(five_);
  list_.push_front(four_);
  list_.push_front(three_);
  list_.push_front(two_);
  list_.push_front(one_);
  EXPECT_DEATH(list_.push_front(one_), ".");
}
#endif  // NO_DEATH_TESTS

TEST_F(intrusive_list_test, destructor) {
  list_.push_back(one_);
  list_.push_back(two_);
  {
    // These should remove themselves when they go out of scope.
    IntegerListNode one_hundred(100);
    IntegerListNode two_hundred(200);
    list_.push_back(one_hundred);
    list_.push_back(two_hundred);
  }
  list_.push_back(three_);
  list_.push_back(four_);
  list_.push_back(five_);

  auto iter = list_.begin();
  EXPECT_EQ(1, iter->value());
  ++iter;
  EXPECT_EQ(2, iter->value());
  ++iter;
  EXPECT_EQ(3, iter->value());
  ++iter;
  EXPECT_EQ(4, iter->value());
  ++iter;
  EXPECT_EQ(5, iter->value());
  ++iter;
  EXPECT_EQ(list_.end(), iter);

  EXPECT_EQ(1, list_.front().value());
  EXPECT_EQ(5, list_.back().value());
}

TEST_F(intrusive_list_test, move_node) {
  list_.push_back(one_);
  list_.push_back(two_);
  list_.push_back(three_);
  list_.push_back(four_);
  list_.push_back(five_);

  // Generally, when moving something it would be done implicitly when the
  // object holding it moves. This is just to demonstrate that it moves the
  // pointers around correctly when it does move.
  //
  // two_.node has four_.node's location in the list moved into it. four_.node
  // is left in a valid but unspecified state.
  two_.node = std::move(four_.node);

  auto iter = list_.begin();
  EXPECT_EQ(1, iter->value());
  ++iter;
  EXPECT_EQ(3, iter->value());
  ++iter;
  EXPECT_EQ(2, iter->value());
  ++iter;
  EXPECT_EQ(5, iter->value());
  ++iter;
  EXPECT_EQ(list_.end(), iter);
}

TEST_F(intrusive_list_test, rbegin_rend) {
  list_.push_back(one_);
  list_.push_back(two_);
  list_.push_back(three_);
  list_.push_back(four_);
  list_.push_back(five_);

  auto iter = list_.rbegin();
  EXPECT_EQ(5, iter->value());
  ++iter;
  EXPECT_EQ(4, iter->value());
  ++iter;
  EXPECT_EQ(3, iter->value());
  ++iter;
  EXPECT_EQ(2, iter->value());
  ++iter;
  EXPECT_EQ(1, iter->value());
  ++iter;
  EXPECT_EQ(list_.rend(), iter);
}

TEST_F(intrusive_list_test, crbegin_crend) {
  list_.push_back(one_);
  list_.push_back(two_);
  list_.push_back(three_);
  list_.push_back(four_);
  list_.push_back(five_);

  auto iter = list_.crbegin();
  EXPECT_EQ(5, iter->value());
  ++iter;
  EXPECT_EQ(4, iter->value());
  ++iter;
  EXPECT_EQ(3, iter->value());
  ++iter;
  EXPECT_EQ(2, iter->value());
  ++iter;
  EXPECT_EQ(1, iter->value());
  ++iter;
  EXPECT_EQ(list_.crend(), iter);
}

TEST_F(intrusive_list_test, clear) {
  EXPECT_TRUE(list_.empty());

  list_.push_back(one_);
  list_.push_back(two_);
  list_.push_back(three_);
  list_.push_back(four_);
  list_.push_back(five_);
  EXPECT_FALSE(list_.empty());

  list_.clear();
  EXPECT_TRUE(list_.empty());
}

TEST_F(intrusive_list_test, insert) {
  list_.push_back(one_);
  list_.push_back(two_);
  list_.push_back(three_);
  list_.push_back(four_);
  list_.push_back(five_);

  auto iter = list_.begin();
  ++iter;
  ++iter;
  list_.insert(iter, ten_);

  iter = list_.begin();
  EXPECT_EQ(1, iter->value());
  ++iter;
  EXPECT_EQ(2, iter->value());
  ++iter;
  EXPECT_EQ(10, iter->value());
  ++iter;
  EXPECT_EQ(3, iter->value());
  ++iter;
  EXPECT_EQ(4, iter->value());
  ++iter;
  EXPECT_EQ(5, iter->value());
  ++iter;
  EXPECT_EQ(list_.end(), iter);
}

TEST_F(intrusive_list_test, insert_before) {
  list_.push_back(one_);
  list_.push_back(two_);
  list_.push_back(three_);
  list_.push_back(four_);
  list_.push_back(five_);

  auto iter = list_.begin();
  ++iter;
  ++iter;
  fplutil::intrusive_list<IntegerListNode>::insert_before<&IntegerListNode::node>(
      *iter, ten_);

  iter = list_.begin();
  EXPECT_EQ(1, iter->value());
  ++iter;
  EXPECT_EQ(2, iter->value());
  ++iter;
  EXPECT_EQ(10, iter->value());
  ++iter;
  EXPECT_EQ(3, iter->value());
  ++iter;
  EXPECT_EQ(4, iter->value());
  ++iter;
  EXPECT_EQ(5, iter->value());
  ++iter;
  EXPECT_EQ(list_.end(), iter);
}

TEST_F(intrusive_list_test, insert_after) {
  list_.push_back(one_);
  list_.push_back(two_);
  list_.push_back(three_);
  list_.push_back(four_);
  list_.push_back(five_);

  auto iter = list_.begin();
  ++iter;
  fplutil::intrusive_list<IntegerListNode>::insert_after<&IntegerListNode::node>(
      *iter, ten_);

  iter = list_.begin();
  EXPECT_EQ(1, iter->value());
  ++iter;
  EXPECT_EQ(2, iter->value());
  ++iter;
  EXPECT_EQ(10, iter->value());
  ++iter;
  EXPECT_EQ(3, iter->value());
  ++iter;
  EXPECT_EQ(4, iter->value());
  ++iter;
  EXPECT_EQ(5, iter->value());
  ++iter;
  EXPECT_EQ(list_.end(), iter);
}

TEST_F(intrusive_list_test, insert_begin) {
  list_.push_back(one_);
  list_.push_back(two_);
  list_.push_back(three_);
  list_.push_back(four_);
  list_.push_back(five_);

  auto iter = list_.begin();
  list_.insert(iter, ten_);

  iter = list_.begin();
  EXPECT_EQ(10, iter->value());
  ++iter;
  EXPECT_EQ(1, iter->value());
  ++iter;
  EXPECT_EQ(2, iter->value());
  ++iter;
  EXPECT_EQ(3, iter->value());
  ++iter;
  EXPECT_EQ(4, iter->value());
  ++iter;
  EXPECT_EQ(5, iter->value());
  ++iter;
  EXPECT_EQ(list_.end(), iter);
}

TEST_F(intrusive_list_test, insert_end) {
  list_.push_back(one_);
  list_.push_back(two_);
  list_.push_back(three_);
  list_.push_back(four_);
  list_.push_back(five_);

  auto iter = list_.begin();
  ++iter;
  ++iter;
  ++iter;
  ++iter;
  ++iter;
  list_.insert(iter, ten_);

  iter = list_.begin();
  EXPECT_EQ(1, iter->value());
  ++iter;
  EXPECT_EQ(2, iter->value());
  ++iter;
  EXPECT_EQ(3, iter->value());
  ++iter;
  EXPECT_EQ(4, iter->value());
  ++iter;
  EXPECT_EQ(5, iter->value());
  ++iter;
  EXPECT_EQ(10, iter->value());
  ++iter;
  EXPECT_EQ(list_.end(), iter);
}

TEST_F(intrusive_list_test, insert_iter) {
  list_.push_back(one_);
  list_.push_back(two_);
  list_.push_back(three_);
  list_.push_back(four_);
  list_.push_back(five_);

  std::vector<IntegerListNode> list_nodes;
  list_nodes.push_back(IntegerListNode(100));
  list_nodes.push_back(IntegerListNode(200));
  list_nodes.push_back(IntegerListNode(300));

  auto iter = list_.begin();
  ++iter;
  ++iter;
  list_.insert(iter, list_nodes.begin(), list_nodes.end());

  iter = list_.begin();
  EXPECT_EQ(1, iter->value());
  ++iter;
  EXPECT_EQ(2, iter->value());
  ++iter;
  EXPECT_EQ(100, iter->value());
  ++iter;
  EXPECT_EQ(200, iter->value());
  ++iter;
  EXPECT_EQ(300, iter->value());
  ++iter;
  EXPECT_EQ(3, iter->value());
  ++iter;
  EXPECT_EQ(4, iter->value());
  ++iter;
  EXPECT_EQ(5, iter->value());
  ++iter;
  EXPECT_EQ(list_.end(), iter);
}

TEST_F(intrusive_list_test, size) {
  EXPECT_EQ(0u, list_.size());
  EXPECT_TRUE(list_.empty());
  list_.push_back(one_);
  EXPECT_EQ(1u, list_.size());
  EXPECT_FALSE(list_.empty());
  list_.push_back(two_);
  EXPECT_EQ(2u, list_.size());
  EXPECT_FALSE(list_.empty());
  list_.push_front(three_);
  EXPECT_EQ(3u, list_.size());
  EXPECT_FALSE(list_.empty());
  list_.push_back(four_);
  EXPECT_EQ(4u, list_.size());
  EXPECT_FALSE(list_.empty());
  list_.push_front(five_);
  EXPECT_EQ(5u, list_.size());
  EXPECT_FALSE(list_.empty());
  list_.pop_front();
  EXPECT_EQ(4u, list_.size());
  EXPECT_FALSE(list_.empty());
  list_.pop_back();
  EXPECT_EQ(3u, list_.size());
  EXPECT_FALSE(list_.empty());
  list_.pop_front();
  EXPECT_EQ(2u, list_.size());
  EXPECT_FALSE(list_.empty());
  list_.pop_back();
  EXPECT_EQ(1u, list_.size());
  EXPECT_FALSE(list_.empty());
  list_.pop_front();
  EXPECT_EQ(0u, list_.size());
  EXPECT_TRUE(list_.empty());
}

TEST_F(intrusive_list_test, unique) {
  IntegerListNode another_one(1);
  IntegerListNode another_three(3);
  IntegerListNode another_five(5);
  IntegerListNode another_five_again(5);

  list_.push_back(one_);
  list_.push_back(another_one);
  list_.push_back(two_);
  list_.push_back(three_);
  list_.push_back(another_three);
  list_.push_back(four_);
  list_.push_back(five_);
  list_.push_back(another_five);
  list_.push_back(another_five_again);

  list_.unique();

  auto iter = list_.begin();
  EXPECT_EQ(1, iter->value());
  ++iter;
  EXPECT_EQ(2, iter->value());
  ++iter;
  EXPECT_EQ(3, iter->value());
  ++iter;
  EXPECT_EQ(4, iter->value());
  ++iter;
  EXPECT_EQ(5, iter->value());
  ++iter;
  EXPECT_EQ(list_.end(), iter);

  EXPECT_TRUE(one_.node.in_list());
  EXPECT_TRUE(two_.node.in_list());
  EXPECT_TRUE(three_.node.in_list());
  EXPECT_TRUE(four_.node.in_list());
  EXPECT_TRUE(five_.node.in_list());
  EXPECT_TRUE(!another_one.node.in_list());
  EXPECT_TRUE(!another_three.node.in_list());
  EXPECT_TRUE(!another_five.node.in_list());
  EXPECT_TRUE(!another_five_again.node.in_list());
}

TEST_F(intrusive_list_test, unique_predicate) {
  IntegerListNode another_one(1);
  IntegerListNode another_three(3);
  IntegerListNode another_five(5);
  IntegerListNode another_five_again(5);

  list_.push_back(one_);
  list_.push_back(another_one);
  list_.push_back(two_);
  list_.push_back(three_);
  list_.push_back(another_three);
  list_.push_back(four_);
  list_.push_back(five_);
  list_.push_back(another_five);
  list_.push_back(another_five_again);

  list_.unique(std::equal_to<IntegerListNode>());

  auto iter = list_.begin();
  EXPECT_EQ(1, iter->value());
  ++iter;
  EXPECT_EQ(2, iter->value());
  ++iter;
  EXPECT_EQ(3, iter->value());
  ++iter;
  EXPECT_EQ(4, iter->value());
  ++iter;
  EXPECT_EQ(5, iter->value());
  ++iter;
  EXPECT_EQ(list_.end(), iter);

  EXPECT_TRUE(one_.node.in_list());
  EXPECT_TRUE(two_.node.in_list());
  EXPECT_TRUE(three_.node.in_list());
  EXPECT_TRUE(four_.node.in_list());
  EXPECT_TRUE(five_.node.in_list());
  EXPECT_TRUE(!another_one.node.in_list());
  EXPECT_TRUE(!another_three.node.in_list());
  EXPECT_TRUE(!another_five.node.in_list());
  EXPECT_TRUE(!another_five_again.node.in_list());
}

TEST_F(intrusive_list_test, sort_in_order) {
  list_.push_back(one_);
  list_.push_back(two_);
  list_.push_back(three_);
  list_.push_back(four_);
  list_.push_back(five_);

  list_.sort();

  auto iter = list_.begin();
  EXPECT_EQ(1, iter->value());
  ++iter;
  EXPECT_EQ(2, iter->value());
  ++iter;
  EXPECT_EQ(3, iter->value());
  ++iter;
  EXPECT_EQ(4, iter->value());
  ++iter;
  EXPECT_EQ(5, iter->value());
  ++iter;
  EXPECT_EQ(list_.end(), iter);
}

TEST_F(intrusive_list_test, sort_reverse_order) {
  list_.push_back(five_);
  list_.push_back(four_);
  list_.push_back(three_);
  list_.push_back(two_);
  list_.push_back(one_);

  list_.sort();

  auto iter = list_.begin();
  EXPECT_EQ(1, iter->value());
  ++iter;
  EXPECT_EQ(2, iter->value());
  ++iter;
  EXPECT_EQ(3, iter->value());
  ++iter;
  EXPECT_EQ(4, iter->value());
  ++iter;
  EXPECT_EQ(5, iter->value());
  ++iter;
  EXPECT_EQ(list_.end(), iter);
}

TEST_F(intrusive_list_test, sort_random_order) {
  list_.push_back(two_);
  list_.push_back(four_);
  list_.push_back(five_);
  list_.push_back(one_);
  list_.push_back(three_);

  list_.sort();

  auto iter = list_.begin();
  EXPECT_EQ(1, iter->value());
  ++iter;
  EXPECT_EQ(2, iter->value());
  ++iter;
  EXPECT_EQ(3, iter->value());
  ++iter;
  EXPECT_EQ(4, iter->value());
  ++iter;
  EXPECT_EQ(5, iter->value());
  ++iter;
  EXPECT_EQ(list_.end(), iter);
}

TEST_F(intrusive_list_test, sort_short_list) {
  list_.push_back(two_);
  list_.push_back(one_);

  list_.sort();

  auto iter = list_.begin();
  EXPECT_EQ(1, iter->value());
  ++iter;
  EXPECT_EQ(2, iter->value());
  ++iter;
  EXPECT_EQ(list_.end(), iter);
}

TEST_F(intrusive_list_test, splice_empty) {
  list_.push_back(one_);
  list_.push_back(two_);
  list_.push_back(three_);
  list_.push_back(four_);
  list_.push_back(five_);

  fplutil::intrusive_list<IntegerListNode> other_list(&IntegerListNode::node);

  list_.splice(list_.begin(), other_list);

  auto iter = list_.begin();
  EXPECT_EQ(1, iter->value());
  ++iter;
  EXPECT_EQ(2, iter->value());
  ++iter;
  EXPECT_EQ(3, iter->value());
  ++iter;
  EXPECT_EQ(4, iter->value());
  ++iter;
  EXPECT_EQ(5, iter->value());
  ++iter;
  EXPECT_EQ(list_.end(), iter);

  iter = other_list.begin();
  EXPECT_EQ(other_list.end(), iter);
}

TEST_F(intrusive_list_test, splice_other_at_beginning) {
  list_.push_back(one_);
  list_.push_back(two_);
  list_.push_back(three_);
  list_.push_back(four_);
  list_.push_back(five_);

  fplutil::intrusive_list<IntegerListNode> other_list(&IntegerListNode::node);
  other_list.push_back(ten_);
  other_list.push_back(twenty_);
  other_list.push_back(thirty_);
  other_list.push_back(fourty_);
  other_list.push_back(fifty_);

  list_.splice(list_.begin(), other_list);

  auto iter = list_.begin();
  EXPECT_EQ(10, iter->value());
  ++iter;
  EXPECT_EQ(20, iter->value());
  ++iter;
  EXPECT_EQ(30, iter->value());
  ++iter;
  EXPECT_EQ(40, iter->value());
  ++iter;
  EXPECT_EQ(50, iter->value());
  ++iter;
  EXPECT_EQ(1, iter->value());
  ++iter;
  EXPECT_EQ(2, iter->value());
  ++iter;
  EXPECT_EQ(3, iter->value());
  ++iter;
  EXPECT_EQ(4, iter->value());
  ++iter;
  EXPECT_EQ(5, iter->value());
  ++iter;
  EXPECT_EQ(list_.end(), iter);

  iter = other_list.begin();
  EXPECT_EQ(other_list.end(), iter);
}

TEST_F(intrusive_list_test, splice_other_at_end) {
  list_.push_back(one_);
  list_.push_back(two_);
  list_.push_back(three_);
  list_.push_back(four_);
  list_.push_back(five_);

  fplutil::intrusive_list<IntegerListNode> other_list(&IntegerListNode::node);
  other_list.push_back(ten_);
  other_list.push_back(twenty_);
  other_list.push_back(thirty_);
  other_list.push_back(fourty_);
  other_list.push_back(fifty_);

  list_.splice(list_.end(), other_list);

  auto iter = list_.begin();
  EXPECT_EQ(1, iter->value());
  ++iter;
  EXPECT_EQ(2, iter->value());
  ++iter;
  EXPECT_EQ(3, iter->value());
  ++iter;
  EXPECT_EQ(4, iter->value());
  ++iter;
  EXPECT_EQ(5, iter->value());
  ++iter;
  EXPECT_EQ(10, iter->value());
  ++iter;
  EXPECT_EQ(20, iter->value());
  ++iter;
  EXPECT_EQ(30, iter->value());
  ++iter;
  EXPECT_EQ(40, iter->value());
  ++iter;
  EXPECT_EQ(50, iter->value());
  ++iter;
  EXPECT_EQ(list_.end(), iter);

  iter = other_list.begin();
  EXPECT_EQ(other_list.end(), iter);
}

TEST_F(intrusive_list_test, splice_other_at_middle) {
  list_.push_back(one_);
  list_.push_back(two_);
  list_.push_back(three_);
  list_.push_back(four_);
  list_.push_back(five_);

  fplutil::intrusive_list<IntegerListNode> other_list(&IntegerListNode::node);
  other_list.push_back(ten_);
  other_list.push_back(twenty_);
  other_list.push_back(thirty_);
  other_list.push_back(fourty_);
  other_list.push_back(fifty_);

  auto iter = list_.begin();
  ++iter;
  ++iter;
  ++iter;
  list_.splice(iter, other_list);

  iter = list_.begin();
  EXPECT_EQ(1, iter->value());
  ++iter;
  EXPECT_EQ(2, iter->value());
  ++iter;
  EXPECT_EQ(3, iter->value());
  ++iter;
  EXPECT_EQ(10, iter->value());
  ++iter;
  EXPECT_EQ(20, iter->value());
  ++iter;
  EXPECT_EQ(30, iter->value());
  ++iter;
  EXPECT_EQ(40, iter->value());
  ++iter;
  EXPECT_EQ(50, iter->value());
  ++iter;
  EXPECT_EQ(4, iter->value());
  ++iter;
  EXPECT_EQ(5, iter->value());
  ++iter;
  EXPECT_EQ(list_.end(), iter);

  iter = other_list.begin();
  EXPECT_EQ(other_list.end(), iter);
}

TEST_F(intrusive_list_test, merge_alternating) {
  list_.push_back(one_);
  list_.push_back(three_);
  list_.push_back(five_);
  list_.push_back(seven_);
  list_.push_back(nine_);

  fplutil::intrusive_list<IntegerListNode> other_list(&IntegerListNode::node);
  other_list.push_back(two_);
  other_list.push_back(four_);
  other_list.push_back(six_);
  other_list.push_back(eight_);
  other_list.push_back(ten_);

  list_.merge(other_list);

  auto iter = list_.begin();
  EXPECT_EQ(1, iter->value());
  ++iter;
  EXPECT_EQ(2, iter->value());
  ++iter;
  EXPECT_EQ(3, iter->value());
  ++iter;
  EXPECT_EQ(4, iter->value());
  ++iter;
  EXPECT_EQ(5, iter->value());
  ++iter;
  EXPECT_EQ(6, iter->value());
  ++iter;
  EXPECT_EQ(7, iter->value());
  ++iter;
  EXPECT_EQ(8, iter->value());
  ++iter;
  EXPECT_EQ(9, iter->value());
  ++iter;
  EXPECT_EQ(10, iter->value());
  ++iter;
  EXPECT_EQ(list_.end(), iter);

  iter = other_list.begin();
  EXPECT_EQ(other_list.end(), iter);
}

TEST_F(intrusive_list_test, merge_alternating2) {
  list_.push_back(one_);
  list_.push_back(two_);
  list_.push_back(five_);
  list_.push_back(six_);
  list_.push_back(nine_);
  list_.push_back(ten_);

  fplutil::intrusive_list<IntegerListNode> other_list(&IntegerListNode::node);
  other_list.push_back(three_);
  other_list.push_back(four_);
  other_list.push_back(seven_);
  other_list.push_back(eight_);

  list_.merge(other_list);

  auto iter = list_.begin();
  EXPECT_EQ(1, iter->value());
  ++iter;
  EXPECT_EQ(2, iter->value());
  ++iter;
  EXPECT_EQ(3, iter->value());
  ++iter;
  EXPECT_EQ(4, iter->value());
  ++iter;
  EXPECT_EQ(5, iter->value());
  ++iter;
  EXPECT_EQ(6, iter->value());
  ++iter;
  EXPECT_EQ(7, iter->value());
  ++iter;
  EXPECT_EQ(8, iter->value());
  ++iter;
  EXPECT_EQ(9, iter->value());
  ++iter;
  EXPECT_EQ(10, iter->value());
  ++iter;
  EXPECT_EQ(list_.end(), iter);

  iter = other_list.begin();
  EXPECT_EQ(other_list.end(), iter);
}

TEST_F(intrusive_list_test, merge_this_other) {
  list_.push_back(one_);
  list_.push_back(two_);
  list_.push_back(three_);
  list_.push_back(four_);
  list_.push_back(five_);

  fplutil::intrusive_list<IntegerListNode> other_list(&IntegerListNode::node);
  other_list.push_back(six_);
  other_list.push_back(seven_);
  other_list.push_back(eight_);
  other_list.push_back(nine_);
  other_list.push_back(ten_);

  list_.merge(other_list);

  auto iter = list_.begin();
  EXPECT_EQ(1, iter->value());
  ++iter;
  EXPECT_EQ(2, iter->value());
  ++iter;
  EXPECT_EQ(3, iter->value());
  ++iter;
  EXPECT_EQ(4, iter->value());
  ++iter;
  EXPECT_EQ(5, iter->value());
  ++iter;
  EXPECT_EQ(6, iter->value());
  ++iter;
  EXPECT_EQ(7, iter->value());
  ++iter;
  EXPECT_EQ(8, iter->value());
  ++iter;
  EXPECT_EQ(9, iter->value());
  ++iter;
  EXPECT_EQ(10, iter->value());
  ++iter;
  EXPECT_EQ(list_.end(), iter);

  iter = other_list.begin();
  EXPECT_EQ(other_list.end(), iter);
}

TEST_F(intrusive_list_test, merge_other_this) {
  list_.push_back(six_);
  list_.push_back(seven_);
  list_.push_back(eight_);
  list_.push_back(nine_);
  list_.push_back(ten_);

  fplutil::intrusive_list<IntegerListNode> other_list(&IntegerListNode::node);
  other_list.push_back(one_);
  other_list.push_back(two_);
  other_list.push_back(three_);
  other_list.push_back(four_);
  other_list.push_back(five_);

  list_.merge(other_list);

  auto iter = list_.begin();
  EXPECT_EQ(1, iter->value());
  ++iter;
  EXPECT_EQ(2, iter->value());
  ++iter;
  EXPECT_EQ(3, iter->value());
  ++iter;
  EXPECT_EQ(4, iter->value());
  ++iter;
  EXPECT_EQ(5, iter->value());
  ++iter;
  EXPECT_EQ(6, iter->value());
  ++iter;
  EXPECT_EQ(7, iter->value());
  ++iter;
  EXPECT_EQ(8, iter->value());
  ++iter;
  EXPECT_EQ(9, iter->value());
  ++iter;
  EXPECT_EQ(10, iter->value());
  ++iter;
  EXPECT_EQ(list_.end(), iter);

  iter = other_list.begin();
  EXPECT_EQ(other_list.end(), iter);
}

TEST_F(intrusive_list_test, move_constructor) {
  list_.push_back(one_);
  list_.push_back(two_);
  list_.push_back(three_);
  list_.push_back(four_);
  list_.push_back(five_);

  fplutil::intrusive_list<IntegerListNode> other(std::move(list_));

  EXPECT_TRUE(one_.node.in_list());
  EXPECT_TRUE(two_.node.in_list());
  EXPECT_TRUE(three_.node.in_list());
  EXPECT_TRUE(four_.node.in_list());
  EXPECT_TRUE(five_.node.in_list());

  auto iter = other.begin();
  EXPECT_EQ(1, iter->value());
  ++iter;
  EXPECT_EQ(2, iter->value());
  ++iter;
  EXPECT_EQ(3, iter->value());
  ++iter;
  EXPECT_EQ(4, iter->value());
  ++iter;
  EXPECT_EQ(5, iter->value());
  ++iter;
  EXPECT_EQ(other.end(), iter);
}

TEST_F(intrusive_list_test, move_assignment) {
  list_.push_back(one_);
  list_.push_back(two_);
  list_.push_back(three_);
  list_.push_back(four_);
  list_.push_back(five_);

  fplutil::intrusive_list<IntegerListNode> other(&IntegerListNode::node);
  other = std::move(list_);

  EXPECT_TRUE(one_.node.in_list());
  EXPECT_TRUE(two_.node.in_list());
  EXPECT_TRUE(three_.node.in_list());
  EXPECT_TRUE(four_.node.in_list());
  EXPECT_TRUE(five_.node.in_list());

  auto iter = other.begin();
  EXPECT_EQ(1, iter->value());
  ++iter;
  EXPECT_EQ(2, iter->value());
  ++iter;
  EXPECT_EQ(3, iter->value());
  ++iter;
  EXPECT_EQ(4, iter->value());
  ++iter;
  EXPECT_EQ(5, iter->value());
  ++iter;
  EXPECT_EQ(other.end(), iter);
}

TEST_F(intrusive_list_test, swap) {
  list_.push_back(one_);
  list_.push_back(two_);
  list_.push_back(three_);
  list_.push_back(four_);
  list_.push_back(five_);

  fplutil::intrusive_list<IntegerListNode> other(&IntegerListNode::node);
  other.push_back(ten_);
  other.push_back(twenty_);
  other.push_back(thirty_);
  other.push_back(fourty_);
  other.push_back(fifty_);

  list_.swap(other);

  auto iter = list_.begin();
  EXPECT_EQ(10, iter->value());
  ++iter;
  EXPECT_EQ(20, iter->value());
  ++iter;
  EXPECT_EQ(30, iter->value());
  ++iter;
  EXPECT_EQ(40, iter->value());
  ++iter;
  EXPECT_EQ(50, iter->value());
  ++iter;
  EXPECT_EQ(list_.end(), iter);

  iter = other.begin();
  EXPECT_EQ(1, iter->value());
  ++iter;
  EXPECT_EQ(2, iter->value());
  ++iter;
  EXPECT_EQ(3, iter->value());
  ++iter;
  EXPECT_EQ(4, iter->value());
  ++iter;
  EXPECT_EQ(5, iter->value());
  ++iter;
  EXPECT_EQ(other.end(), iter);
}

TEST_F(intrusive_list_test, swap_self) {
  list_.push_back(one_);
  list_.push_back(two_);
  list_.push_back(three_);
  list_.push_back(four_);
  list_.push_back(five_);

  list_.swap(list_);

  auto iter = list_.begin();
  EXPECT_EQ(1, iter->value());
  ++iter;
  EXPECT_EQ(2, iter->value());
  ++iter;
  EXPECT_EQ(3, iter->value());
  ++iter;
  EXPECT_EQ(4, iter->value());
  ++iter;
  EXPECT_EQ(5, iter->value());
  ++iter;
  EXPECT_EQ(list_.end(), iter);
}

int main(int argc, char** argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
