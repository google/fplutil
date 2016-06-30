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

#ifndef FPLUTIL_FBX_SDK_NO_WARNINGS
#define FPLUTIL_FBX_SDK_NO_WARNINGS

// Suppress warnings in external header.
#ifdef _MSC_VER
#pragma warning(push)            // for Visual Studio
#pragma warning(disable : 4068)  // "unknown pragma" -- for Visual Studio
#endif                           // _MSC_VER
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wignored-qualifiers"
#pragma GCC diagnostic ignored "-Wunused-parameter"
#pragma GCC diagnostic ignored "-Wpedantic"
#pragma GCC diagnostic ignored "-Wunused-value"
#pragma GCC diagnostic ignored "-Wmissing-field-initializers"

#include <fbxsdk.h>

#pragma GCC diagnostic pop
#ifdef _MSC_VER
#pragma warning(pop)
#endif  // _MSC_VER

#endif  // FPLUTIL_FBX_SDK_NO_WARNINGS
