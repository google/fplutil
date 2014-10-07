// Copyright 2014 Google Inc. All rights reserved.
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

/// @file main.c Example application built by buildutil.
#include <stdio.h>

// Very simple linux build example. MESSAGE is defined on the make command line
// based on the cmake_flags set in the build.py.
int main(int argc, char **argv)
{
  printf("%s\n", MESSAGE);
  return 0;
}
