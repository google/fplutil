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

#ifndef FPLUTIL_INTRUSIVE_LIST_H_
#define FPLUTIL_INTRUSIVE_LIST_H_

#include <cassert>
#include <cstddef>
#include <functional>

#if defined(_MSC_FULL_VER)
#pragma warning(push)
#pragma warning(disable : 4127)  // conditional expression is constant.
#pragma warning(disable : 4355)  // 'this' used in base member initializer list.
#endif

// Only use noexcept if the compiler supports it.
#if !defined FPLUTIL_NOEXCEPT
#if defined(__clang__)
#if __has_feature(cxx_noexcept)
#define FPLUTIL_NOEXCEPT noexcept
#endif
#elif defined(__GXX_EXPERIMENTAL_CXX0X__)
#if __GNUC__ * 10 + __GNUC_MINOR__ >= 46
#define FPLUTIL_NOEXCEPT noexcept
#endif
#elif defined(_MSC_FULL_VER)
#if _MSC_VER >= 1900  // MSVC++ 14.0 (Visual Studio 2015)
#define FPLUTIL_NOEXCEPT noexcept
#endif
#endif
#ifndef FPLUTIL_NOEXCEPT
#define FPLUTIL_NOEXCEPT
#endif
#endif

namespace fplutil {

class intrusive_list_node;

template <typename T>
class intrusive_list;

// An intrusive_list_node is a class that must be included as a member variable
// on a type in order to store an object of that type in an intrusive_list. It
// is possible to include more than one intrusive_list_node to allow an object
// to be in multiple lists simultaneously.
//
// The intrusive_list_node class supports move contructors but not copy
// contructors.
//
// A simple example:
//
// struct ExampleStruct {
//   int value;
//   fplutil::intrusive_list_node node;
// };
//
// Or if you want the object to be present in multiple lists at once:
//
// struct ExampleStruct {
//   int value;
//   fplutil::intrusive_list_node node_a;
//   fplutil::intrusive_list_node node_b;
// };
class intrusive_list_node {
 public:
  // Initialize an intrusive_list_node.
  intrusive_list_node() : next_(this), previous_(this) {}
  ~intrusive_list_node() { remove(); }

  // Move contructor.
  intrusive_list_node(intrusive_list_node&& other) FPLUTIL_NOEXCEPT {
    move(other);
  }

  // Move assignment operator.
  intrusive_list_node& operator=(intrusive_list_node&& other) FPLUTIL_NOEXCEPT {
    next_->previous_ = previous_;
    previous_->next_ = next_;
    move(other);
    return *this;
  }

#if defined(_MSC_VER)
  // Copy contructor.
  intrusive_list_node(intrusive_list_node& other) { move(other); }
  // Copy assignment operator.
  intrusive_list_node& operator=(intrusive_list_node& other) {
    next_->previous_ = previous_;
    previous_->next_ = next_;
    move(other);
    return *this;
  }
#endif  // defined(_MSC_VER)

  // Retuns true if this node is in a list.
  bool in_list() const { return next_ != this; }

  // Removes this node from the list it is in.
  intrusive_list_node* remove() {
    next_->previous_ = previous_;
    previous_->next_ = next_;
    clear();
    return this;
  }

 private:
  intrusive_list_node(intrusive_list_node* next, intrusive_list_node* previous)
      : next_(next), previous_(previous) {}

  inline void move(intrusive_list_node& other) FPLUTIL_NOEXCEPT {
    if (other.in_list()) {
      next_ = other.next_;
      previous_ = other.previous_;
      other.next_->previous_ = this;
      other.previous_->next_ = this;
      other.clear();
    } else {
      // If the other node was not in a list, this node should not be in a list
      // too.
      next_ = this;
      previous_ = this;
    }
  }

  inline void clear() {
    next_ = this;
    previous_ = this;
  }

  inline void insert_before(intrusive_list_node* node) {
    previous_->next_ = node;
    node->previous_ = previous_;
    node->next_ = this;
    previous_ = node;
  }

  inline void insert_after(intrusive_list_node* node) {
    next_->previous_ = node;
    node->next_ = next_;
    node->previous_ = this;
    next_ = node;
  }

  intrusive_list_node* next_;
  intrusive_list_node* previous_;

  template <typename T>
  friend class intrusive_list;
  template <typename T, bool is_const>
  friend class intrusive_list_iterator;

#if !defined(_MSC_VER)
  // Disallow copying.
  intrusive_list_node(intrusive_list_node&);
  intrusive_list_node& operator=(intrusive_list_node&);
#endif  // !defined(_MSC_VER)
};

// intrusive_list is a container that supports constant time insertion and
// removal of elements from anywhere in the container. Fast random access is not
// supported. Elements of the list must contain an intrusive_list_node as a
// member, and may include more than one intrusive_list_node if they want to
// reside in multiple lists simultaneously. An intrusive list will never
// allocate memory to store elements; elements are linked together by the
// specified intrusive_list_node on the object.
template <typename T>
class intrusive_list {
 private:
  // An intrusive_list_iterator which satisfies all the requirements of a
  // standard bidirectional iterator.
  template <bool is_const>
  class intrusive_list_iterator;

 public:
  typedef intrusive_list<T> this_type;
  typedef T value_type;
  typedef std::size_t size_type;
  typedef std::ptrdiff_t difference_type;
  typedef T& reference;
  typedef const T& const_reference;
  typedef T* pointer;
  typedef const T* const_pointer;
  typedef intrusive_list_iterator<false> iterator;
  typedef intrusive_list_iterator<true> const_iterator;
  typedef std::reverse_iterator<iterator> reverse_iterator;
  typedef std::reverse_iterator<const_iterator> const_reverse_iterator;
  typedef intrusive_list_node node_type;

  explicit intrusive_list(size_t node_offset)
      : data_(&data_, &data_), node_offset_(node_offset) {}

  explicit intrusive_list(intrusive_list_node T::*node_member)
      : data_(&data_, &data_), node_offset_(offset_of_node(node_member)) {}

  intrusive_list(this_type&& other) { *this = std::move(other); }

  intrusive_list& operator=(this_type&& other) {
    data_ = std::move(other.data_);
    node_offset_ = std::move(other.node_offset_);
    return *this;
  }

#if defined(_MSC_VER)
  // Normally we need to disallow copying. Ideally we'd put this in the
  // `private` section so that copying will generate a compiler error. We can't
  // do that (explained below), so we leave off the impelmentation to generate a
  // linker error instead.
  //
  // Visual Studio aggressively generates copy constructors. For example, if an
  // intrusive_list is used in an std::pair<> (as it would be when part of an
  // std::map<>), then the copy constructor is generated, even though it really
  // should be using the move constructor for operations in the map.
  //
  // TODO: Find a better way around this limitation.
  intrusive_list(intrusive_list<value_type>& other) { *this = other; }
  intrusive_list& operator=(this_type& other) {
    data_ = other.data_;
    node_offset_ = other.node_offset_;
    return *this;
  }
#else
  intrusive_list(const intrusive_list<value_type>&) { assert(false); }
  intrusive_list& operator=(const this_type&) { assert(false); }
#endif  // defined(_MSC_VER)

  template <class InputIt>
  intrusive_list(InputIt first, InputIt last) : data_(&data_, &data_) {
    insert(begin(), first, last);
  }

  iterator begin() { return iterator(data_.next_, node_offset_); }

  const_iterator begin() const {
    return const_iterator(data_.next_, node_offset_);
  }

  const_iterator cbegin() const {
    return const_iterator(data_.next_, node_offset_);
  }

  reverse_iterator rbegin() { return reverse_iterator(end()); }

  const_reverse_iterator rbegin() const {
    return const_reverse_iterator(end());
  }

  const_reverse_iterator crbegin() const {
    return const_reverse_iterator(cend());
  }

  iterator end() { return iterator(&data_, node_offset_); }

  const_iterator end() const { return const_iterator(&data_, node_offset_); }

  const_iterator cend() const { return const_iterator(&data_, node_offset_); }

  reverse_iterator rend() { return reverse_iterator(begin()); }

  const reverse_iterator rend() const { return reverse_iterator(begin()); }

  const_reverse_iterator crend() const {
    return const_reverse_iterator(cbegin());
  }

  void push_front(reference value) {
    node_type* value_node = node_from_object(value, node_offset_);
    assert(!value_node->in_list());
    data_.insert_after(value_node);
  }

  void pop_front() { data_.next_->remove(); }

  void push_back(reference value) {
    node_type* value_node = node_from_object(value, node_offset_);
    assert(!value_node->in_list());
    data_.insert_before(value_node);
  }

  void pop_back() { data_.previous_->remove(); }

  void clear() {
    for (iterator iter = begin(); iter != end();) {
      iterator current = iter++;
      node_from_object(*current, node_offset_)->clear();
    }
    data_.clear();
  }

  iterator insert(iterator pos, reference value) {
    insert_before(*pos, value, node_offset_);
    return iterator(node_from_object(value, node_offset_), node_offset_);
  }

  iterator insert_after(iterator pos, reference value) {
    insert_after(*pos, value);
    return iterator(node_from_object(value, node_offset_));
  }

  template <class InputIt>
  iterator insert(iterator pos, InputIt first, InputIt last) {
    iterator return_value = pos;
    for (InputIt iter = first; iter != last; ++iter) {
      insert(pos, *iter);
    }
    return return_value;
  }

  template <intrusive_list_node T::*node_member>
  static void insert_before(reference value, reference other) {
    insert_before(value, other, node_member);
  }

  static void insert_before(reference value, reference other,
                            intrusive_list_node T::*node_member) {
    insert_before(value, other, offset_of_node(node_member));
  }

  static void insert_before(reference value, reference other, size_t offset) {
    node_type* value_node = node_from_object(value, offset);
    node_type* other_node = node_from_object(other, offset);
    value_node->insert_before(other_node);
  }

  template <intrusive_list_node T::*node_member>
  static void insert_after(reference value, reference other) {
    insert_after(value, other, node_member);
  }

  static void insert_after(reference value, reference other,
                           intrusive_list_node T::*node_member) {
    insert_after(value, other, offset_of_node(node_member));
  }

  static void insert_after(reference value, reference other, size_t offset) {
    node_type* value_node = node_from_object(value, offset);
    node_type* other_node = node_from_object(other, offset);
    value_node->insert_after(other_node);
  }

  bool empty() const { return !data_.in_list(); }

  size_type size() const { return std::distance(cbegin(), cend()); }

  reference front() { return *object_from_node(data_.next_, node_offset_); }

  const_reference front() const {
    return *object_from_node(data_.next_, node_offset_);
  }

  reference back() { return *object_from_node(data_.previous_, node_offset_); }

  const_reference back() const {
    return *object_from_node(data_.previous_, node_offset_);
  }

  iterator erase(iterator pos) {
    node_type* next = pos.node_->next_;
    pos.node_->remove();
    return next;
  }

  iterator erase(iterator first, iterator last) {
    node_type* before_first = first.node_->previous_;
    node_type* after_last = last.node_->next_;
    after_last->previous_ = before_first;
    before_first->next_ = after_last;

    iterator iter = first;
    while (iter != last) {
      iterator current = iter++;
      current.node_->clear();
    }
    return iter;
  }

  void swap(this_type& other) {
    std::swap(data_.next_, other.data_.next_);
    std::swap(data_.previous_, other.data_.previous_);
    std::swap(data_.next_->previous_, other.data_.next_->previous_);
    std::swap(data_.previous_->next_, other.data_.previous_->next_);
  }

  template <intrusive_list_node T::*node_member>
  static reference remove(reference value) {
    return remove(value, node_member);
  }

  static reference remove(reference value,
                          intrusive_list_node T::*node_member) {
    return remove(value, offset_of_node(node_member));
  }

  static reference remove(reference value, size_t node_offset_) {
    node_from_object(value, node_offset_)->remove();
    return value;
  }

  void splice(iterator pos, reference other) { insert(pos, remove(other)); }

  void splice(iterator pos, this_type& other) {
    splice(pos, other.begin(), other.end());
  }

  void splice(iterator pos, iterator iter) {
    splice(pos, iter, std::next(iter));
  }

  void splice(iterator pos, iterator first, iterator last) {
    if (first == last) {
      return;
    }
    node_type* before_pos_node = pos.value_->previous_;
    node_type* before_first_node = first.value_->previous_;
    node_type* before_last_node = last.value_->previous_;

    before_pos_node->next_ = first.value_;
    before_first_node->next_ = last.value_;
    before_last_node->next_ = pos.value_;

    pos.value_->previous_ = before_last_node;
    first.value_->previous_ = before_pos_node;
    last.value_->previous_ = before_first_node;
  }

  template <typename Compare>
  void merge(this_type& other, Compare compare = Compare()) {
    iterator this_iter = begin();
    iterator other_iter = other.begin();
    while (true) {
      if (this_iter == end()) {
        splice(end(), other_iter, other.end());
        return;
      } else if (other_iter == other.end()) {
        return;
      } else if (compare(*this_iter, *other_iter)) {
        ++this_iter;
      } else {
        iterator to_be_removed = other_iter++;
        insert(this_iter, remove(*to_be_removed, node_offset_));
      }
    }
  }

  void merge(this_type& other,
             std::less<value_type> compare = std::less<value_type>()) {
    merge<std::less<value_type>>(other, compare);
  }

  template <typename BinaryPredicate>
  void unique(BinaryPredicate pred = BinaryPredicate()) {
    if (empty()) {
      return;
    }
    iterator iter = begin();
    while (iter != std::prev(end())) {
      iterator next_iter = std::next(iter);
      if (pred(*iter, *next_iter)) {
        remove(*next_iter, node_offset_);
      } else {
        ++iter;
      }
    }
  }

  void unique(std::equal_to<value_type> pred = std::equal_to<value_type>()) {
    unique<std::equal_to<value_type>>(pred);
  }

  template <typename Compare>
  void sort(Compare compare = Compare()) {
    // Sort using insertion sort.
    // http://en.wikipedia.org/wiki/Insertion_sort
    iterator next;
    for (iterator i = begin(); i != end(); i = next) {
      // Cache the `next` node because `i` might move.
      next = std::next(i);
      iterator j = i;
      while (j != begin() && compare(*i, *std::prev(j))) {
        --j;
      }
      if (i != j) {
        pointer object = &*i;
        insert(j, remove(*object, node_offset_));
      }
    }
  }

  void sort(std::less<value_type> compare = std::less<value_type>()) {
    sort<std::less<value_type>>(compare);
  }

 private:
  node_type data_;
  // Node offset is the position of the intrusive_list_node in the structure. It
  // is necessary for the pointer arithmetic to convert between objects and the
  // nodes on those objects.
  size_t node_offset_;

  // An intrusive_list_iterator meets all the requirements of a standard
  // bidirectional iterator. That is, you can iterate through a list with one
  // forward or backward (with ++ and --) but you can not perform random access.
  // For example, if you have an intrusive list 'my_list', you can iterator over
  // it like so:
  //
  //     for (auto iter = my_list.begin(); iter != my_list.end(); ++iter) {
  //     auto& element = *iter; // ...  }
  //
  // or like so:
  //
  //     for (auto& element : my_list) { // ...  }
  template <bool is_const>
  class intrusive_list_iterator {
   public:
    // Standard type_trait typedefs. All standard containers define a set of
    // typedefs (value_type, difference_type, reference, pointer, and
    // iteractor_category) so that it is possible to write generic algorithms in
    // terms of iterators. We additionally define node_type which is either
    // intrusive_list_node or const intrusive_list_nodeu
    typedef intrusive_list_iterator<is_const> this_type;
    typedef T value_type;
    typedef std::ptrdiff_t difference_type;
    typedef typename std::conditional<is_const, const T&, T&>::type reference;
    typedef typename std::conditional<is_const, const T*, T*>::type pointer;
    typedef std::bidirectional_iterator_tag iterator_category;
    typedef typename std::conditional<is_const, const intrusive_list_node,
                                      intrusive_list_node>::type node_type;

    intrusive_list_iterator() : value_(nullptr) {}

    bool operator==(const this_type& other) const {
      return value_ == other.value_;
    }

    bool operator!=(const this_type& other) const {
      return !this->operator==(other);
    }

    reference operator*() { return *object_from_node(value_, node_offset_); }
    const_reference operator*() const {
      return *object_from_node(value_, node_offset_);
    }

    pointer operator->() { return object_from_node(value_, node_offset_); }
    const_pointer operator->() const {
      return object_from_node(value_, node_offset_);
    }

    this_type& operator++() {
      value_ = value_->next_;
      return *this;
    }

    this_type operator++(int) {
      node_type* old_value = value_;
      value_ = value_->next_;
      return this_type(old_value, node_offset_);
    }

    this_type& operator--() {
      value_ = value_->previous_;
      return *this;
    }

    this_type operator--(int) {
      node_type* old_value = value_;
      value_ = value_->previous_;
      return this_type(old_value);
    }

   private:
    intrusive_list_iterator(node_type* value, size_t node_offset)
        : value_(value), node_offset_(node_offset) {}
    intrusive_list_iterator(reference value, size_t node_offset)
        : value_(*node_from_object(value)), node_offset_(node_offset) {}
    friend class intrusive_list<value_type>;
    node_type* value_;
    // Node offset is the position of the intrusive_list_node in the structure.
    // It is necessary for the pointer arithmetic to convert between objects and
    // the nodes on those objects.
    size_t node_offset_;
  };

  // This is a convenience function to get the node off of an object. Operator
  // precedence often makes getting the node inconvenient.
  static inline node_type* node_from_object(reference value, size_t offset) {
    return reinterpret_cast<node_type*>(reinterpret_cast<char*>(&value) +
                                        offset);
  }

  // Return the offset of the node in the class or structure.
  static std::size_t offset_of_node(intrusive_list_node T::*node_member) {
    return reinterpret_cast<char*>(
               &(static_cast<pointer>(nullptr)->*node_member)) -
           static_cast<char*>(nullptr);
  }

  // Return a pointer to object of type value_type that owns the given member
  // variable node in the class or structure.
  static pointer object_from_node(node_type* node, size_t offset) {
    return reinterpret_cast<pointer>(reinterpret_cast<char*>(node) -
                                     reinterpret_cast<char*>(offset));
  }

  // Return a pointer to object of type value_type that owns the given member
  // variable node in the class or structure.
  static const_pointer object_from_node(const node_type* node, size_t offset) {
    return reinterpret_cast<pointer>(reinterpret_cast<const char*>(node) -
                                     reinterpret_cast<const char*>(offset));
  }
};

}  // namespace fplutil

#if defined(_MSC_VER)
#pragma warning(pop)
#endif  // defined(_MSC_VER)

#endif  // FPLUTIL_INTRUSIVE_LIST_H_
