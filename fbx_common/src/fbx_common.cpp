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

#include <assert.h>

#include "fbx_common/fbx_common.h"

namespace fplutil {

static const char* kAxisSystemNames[] = {
    "x+y+z",  // kXUp_PositiveYFront_PositiveZLeft
    "x+y-z",  // kXUp_PositiveYFront_NegativeZLeft
    "x-y+z",  // kXUp_NegativeYFront_PositiveZLeft
    "x-y-z",  // kXUp_NegativeYFront_NegativeZLeft
    "x+z+y",  // kXUp_PositiveZFront_PositiveYLeft
    "x+z-y",  // kXUp_PositiveZFront_NegativeYLeft
    "x-z+y",  // kXUp_NegativeZFront_PositiveYLeft
    "x-z-y",  // kXUp_NegativeZFront_NegativeYLeft
    "y+x+z",  // kYUp_PositiveXFront_PositiveZLeft
    "y+x-z",  // kYUp_PositiveXFront_NegativeZLeft
    "y-x+z",  // kYUp_NegativeXFront_PositiveZLeft
    "y-x-z",  // kYUp_NegativeXFront_NegativeZLeft
    "y+z+x",  // kYUp_PositiveZFront_PositiveXLeft
    "y+z-x",  // kYUp_PositiveZFront_NegativeXLeft
    "y-z+x",  // kYUp_NegativeZFront_PositiveXLeft
    "y-z-x",  // kYUp_NegativeZFront_NegativeXLeft
    "z+x+y",  // kZUp_PositiveXFront_PositiveYLeft
    "z+x-y",  // kZUp_PositiveXFront_NegativeYLeft
    "z-x+y",  // kZUp_NegativeXFront_PositiveYLeft
    "z-x-y",  // kZUp_NegativeXFront_NegativeYLeft
    "z+y+x",  // kZUp_PositiveYFront_PositiveXLeft
    "z+y-x",  // kZUp_PositiveYFront_NegativeXLeft
    "z-y+x",  // kZUp_NegativeYFront_PositiveXLeft
    "z-y-x",  // kZUp_NegativeYFront_NegativeXLeft
    nullptr};
static_assert(sizeof(kAxisSystemNames) / sizeof(kAxisSystemNames[0]) ==
                  kNumAxisSystems + 1,
              "kAxisSystemNames out of sync with enum");

static const char* kDistanceUnitNames[] = {"cm",   "m",     "inches",
                                           "feet", "yards", nullptr};

static const float kDistanceUnitScales[] = {
    1.0f, 100.0f, 2.54f, 30.48f, 91.44f,
};
static_assert(sizeof(kDistanceUnitNames) / sizeof(kDistanceUnitNames[0]) - 1 ==
                  sizeof(kDistanceUnitScales) / sizeof(kDistanceUnitScales[0]),
              "kDistanceUnitNames and kDistanceUnitScales are not in sync.");

// Prefix log messages at this level with this message.
static const char* kLogPrefix[] = {
    "",           // kLogVerbose
    "",           // kLogInfo
    "",           // kLogImportant
    "Warning: ",  // kLogWarning
    "Error: "     // kLogError
};
static_assert(sizeof(kLogPrefix) / sizeof(kLogPrefix[0]) == kNumLogLevels,
              "kLogPrefix length is incorrect");

static const FbxVector4 kFbxZero(0.0, 0.0, 0.0, 0.0);
static const FbxVector4 kFbxOne(1.0, 1.0, 1.0, 1.0);

int IndexOfName(const char* name, const char* const* array_of_names) {
  int i = 0;
  for (const char* const* a = array_of_names; *a != nullptr; ++a) {
    if (strcmp(*a, name) == 0) return i;
    ++i;
  }
  return -1;
}

const char* const* AxisSystemNames() { return kAxisSystemNames; }

AxisSystem AxisSystemFromName(const char* name) {
  const int axis_index = IndexOfName(name, kAxisSystemNames);
  return axis_index >= 0 ? static_cast<AxisSystem>(axis_index)
                         : kInvalidAxisSystem;
}

const char* const* DistanceUnitNames() { return kDistanceUnitNames; }

float DistanceUnitFromName(const char* name) {
  // Check for unit name.
  const int unit_index = IndexOfName(name, kDistanceUnitNames);
  if (unit_index >= 0) return kDistanceUnitScales[unit_index];

  // Otherwise, must be a scale number.
  // On failure, returns 0.0f, which is detected as an error by the command-line
  // parser.
  const float scale = static_cast<float>(atof(name));
  return scale;
}

void ConvertFbxScale(float distance_unit, FbxScene* scene, Logger* log) {
  if (distance_unit <= 0.0f) return;

  const FbxSystemUnit import_unit = scene->GetGlobalSettings().GetSystemUnit();
  const FbxSystemUnit export_unit(distance_unit);

  if (import_unit == export_unit) {
    log->Log(kLogVerbose,
             "Scene's distance unit is already %s. Skipping conversion.\n",
             import_unit.GetScaleFactorAsString().Buffer());
    return;
  }

  log->Log(kLogInfo, "Converting scene's distance unit from %s to %s.\n",
           import_unit.GetScaleFactorAsString().Buffer(),
           export_unit.GetScaleFactorAsString().Buffer());
  export_unit.ConvertScene(scene);
}

void ConvertFbxAxes(AxisSystem axis_system, FbxScene* scene, Logger* log) {
  if (axis_system < 0) return;

  const FbxAxisSystem import_axes = scene->GetGlobalSettings().GetAxisSystem();
  const FbxAxisSystem export_axes = AxisSystemToFbxAxisSystem(axis_system);
  if (import_axes == export_axes) {
    log->Log(kLogVerbose, "Scene's axes are already %s.\n",
             kAxisSystemNames[FbxAxisSystemToAxisSystem(export_axes)]);
    return;
  }

  log->Log(kLogInfo, "Converting scene's axes (%s) to requested axes (%s).\n",
           kAxisSystemNames[FbxAxisSystemToAxisSystem(import_axes)],
           kAxisSystemNames[FbxAxisSystemToAxisSystem(export_axes)]);
  export_axes.ConvertScene(scene);

  // The FBX SDK has a bug. After an axis conversion, the prerotation is not
  // propagated to the PreRotation property. We propagate the values manually.
  // Note that we only propagate to the children of the root, since those are
  // the only nodes affected by axis conversion.
  FbxNode* root = scene->GetRootNode();
  for (int i = 0; i < root->GetChildCount(); i++) {
    FbxNode* node = root->GetChild(i);
    node->PreRotation.Set(node->GetPreRotation(FbxNode::eSourcePivot));
  }
}

AxisSystem FbxAxisSystemToAxisSystem(const FbxAxisSystem& axis) {
  int up_sign = 0;
  int front_sign = 0;
  const FbxAxisSystem::EUpVector up = axis.GetUpVector(up_sign);
  const FbxAxisSystem::EFrontVector front = axis.GetFrontVector(front_sign);
  const FbxAxisSystem::ECoordSystem coord = axis.GetCoorSystem();
  assert(up_sign > 0);

  const int up_idx = up - FbxAxisSystem::eXAxis;
  const int front_idx = front - FbxAxisSystem::eParityEven;
  const int front_sign_idx = front_sign > 0 ? 0 : 1;
  const int coord_idx = coord - FbxAxisSystem::eRightHanded;
  return static_cast<AxisSystem>(8 * up_idx + 4 * front_idx +
                                 2 * front_sign_idx + coord_idx);
}

FbxAxisSystem AxisSystemToFbxAxisSystem(AxisSystem system) {
  const int up_idx = system / 8 + FbxAxisSystem::eXAxis;
  const int front_sign = system % 4 < 2 ? 1 : -1;
  const int front_idx = (system % 8) / 4 + FbxAxisSystem::eParityEven;
  const int coord_idx = system % 2;

  const auto up = static_cast<FbxAxisSystem::EUpVector>(up_idx);
  const auto front =
      static_cast<FbxAxisSystem::EFrontVector>(front_sign * front_idx);
  const auto coord = static_cast<FbxAxisSystem::ECoordSystem>(coord_idx);
  return FbxAxisSystem(up, front, coord);
}

// Return true if `node` or any of its children has a mesh.
bool NodeHasMesh(FbxNode* node) {
  if (node->GetMesh() != nullptr) return true;

  // Recursively traverse each child node.
  for (int i = 0; i < node->GetChildCount(); i++) {
    if (NodeHasMesh(node->GetChild(i))) return true;
  }
  return false;
}

static void LogIfNotEqual(const FbxVector4& v, const FbxVector4& compare,
                          const char* name, LogLevel level, Logger* log) {
  if (v == compare) return;
  log->Log(level, "%s: (%6.2f %6.2f %6.2f)\n", name, v[0], v[1], v[2]);
}

// For each mesh in the tree of nodes under `node`, add a surface to `out`.
static void LogFbxNodeRecursively(FbxNode* node, const FbxTime& time,
                                  LogLevel level, Logger* log) {
  // We're only interested in mesh nodes. If a node and all nodes under it
  // have no meshes, we early out.
  if (node == nullptr || !NodeHasMesh(node)) return;
  log->Log(level, "Node: %s\n", node->GetName());

  // Log local transform. It's an affine transform so is 4x3.
  const FbxAMatrix& local = node->EvaluateLocalTransform(
      time, FbxNode::eSourcePivot, true, true);
  for (int i = 0; i < 3; ++i) {
    const FbxVector4 r = local.GetColumn(i);
    log->Log(level, "  (%6.2f %6.2f %6.2f %6.2f)\n", r[0], r[1], r[2], r[3]);
  }

  // Log the compkFbxOnents of the local transform, but only if they don't
  // match their default values.
  LogIfNotEqual(node->EvaluateLocalTranslation(time), kFbxZero, "translate",
                level, log);
  LogIfNotEqual(node->GetRotationOffset(FbxNode::eSourcePivot), kFbxZero,
                "rotation_offset", level, log);
  LogIfNotEqual(node->GetRotationPivot(FbxNode::eSourcePivot), kFbxZero,
                "rotation_pivot", level, log);
  LogIfNotEqual(node->GetPreRotation(FbxNode::eSourcePivot), kFbxZero,
                "pre_rotation", level, log);
  LogIfNotEqual(node->EvaluateLocalRotation(time), kFbxZero, "rotate", level,
                log);
  LogIfNotEqual(node->GetPostRotation(FbxNode::eSourcePivot), kFbxZero,
                "post_rotation", level, log);
  LogIfNotEqual(node->GetScalingOffset(FbxNode::eSourcePivot), kFbxZero,
                "scaling_offset", level, log);
  LogIfNotEqual(node->GetScalingPivot(FbxNode::eSourcePivot), kFbxZero,
                "scaling_pivot", level, log);
  LogIfNotEqual(node->EvaluateLocalScaling(time), kFbxOne, "scaling", level,
                log);
  LogIfNotEqual(node->GetGeometricTranslation(FbxNode::eSourcePivot), kFbxZero,
                "geometric_translation", level, log);
  LogIfNotEqual(node->GetGeometricRotation(FbxNode::eSourcePivot), kFbxZero,
                "geometric_rotation", level, log);
  LogIfNotEqual(node->GetGeometricScaling(FbxNode::eSourcePivot), kFbxOne,
                "geometric_scaling", level, log);
  log->Log(level, "\n");

  // Recursively traverse each node in the scene
  for (int i = 0; i < node->GetChildCount(); i++) {
    LogFbxNodeRecursively(node->GetChild(i), time, level, log);
  }
}

void LogFbxScene(const FbxScene* scene, int time_in_ms, LogLevel level,
                 Logger* log) {
  if (log->level() > level) return;

  FbxTime time;
  time.SetMilliSeconds(time_in_ms);
  LogFbxNodeRecursively(scene->GetRootNode(), time, level, log);
}

void LogOptions(const char* indent, const char* const* array_of_options,
                Logger* log) {
  for (const char* const* option = array_of_options; *option != nullptr;
       ++option) {
    log->Log(kLogImportant, "%s%s\n", indent, *option);
  }
}

void Logger::Log(LogLevel level, const char* format, ...) const {
  if (level < level_) return;

  // Prefix message with log level, if required.
  const char* prefix = kLogPrefix[level];
  if (prefix[0] != '\0') {
    printf("%s", prefix);
  }

  // Redirect output to stdout.
  va_list args;
  va_start(args, format);
  vprintf(format, args);
  va_end(args);
}

}  // namespace fplutil
