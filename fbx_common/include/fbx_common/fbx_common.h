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

#ifndef FPLUTIL_FBX_COMMON_H
#define FPLUTIL_FBX_COMMON_H

#include "fbx_common/fbx_sdk_no_warnings.h"

namespace fplutil {

// Enumeration of all possible orientations of 3D orthonormal axis-systems.
enum AxisSystem {
  kInvalidAxisSystem = -2,
  kUnspecifiedAxisSystem = -1,

  kXUp_PositiveYFront_PositiveZLeft = 0,
  kXUp_PositiveYFront_NegativeZLeft,
  kXUp_NegativeYFront_PositiveZLeft,
  kXUp_NegativeYFront_NegativeZLeft,
  kXUp_PositiveZFront_PositiveYLeft,
  kXUp_PositiveZFront_NegativeYLeft,
  kXUp_NegativeZFront_PositiveYLeft,
  kXUp_NegativeZFront_NegativeYLeft,
  kLastXUpAxisSystem,

  kYUp_PositiveXFront_PositiveZLeft = kLastXUpAxisSystem,
  kYUp_PositiveXFront_NegativeZLeft,
  kYUp_NegativeXFront_PositiveZLeft,
  kYUp_NegativeXFront_NegativeZLeft,
  kYUp_PositiveZFront_PositiveXLeft,
  kYUp_PositiveZFront_NegativeXLeft,
  kYUp_NegativeZFront_PositiveXLeft,
  kYUp_NegativeZFront_NegativeXLeft,
  kLastYUpAxisSystem,

  kZUp_PositiveXFront_PositiveYLeft = kLastYUpAxisSystem,
  kZUp_PositiveXFront_NegativeYLeft,
  kZUp_NegativeXFront_PositiveYLeft,
  kZUp_NegativeXFront_NegativeYLeft,
  kZUp_PositiveYFront_PositiveXLeft,
  kZUp_PositiveYFront_NegativeXLeft,
  kZUp_NegativeYFront_PositiveXLeft,
  kZUp_NegativeYFront_NegativeXLeft,
  kLastZUpAxisSystem,

  kNumAxisSystems = kLastZUpAxisSystem
};

// Each log message is given a level of importance.
// We only output messages that have level >= our current logging level.
enum LogLevel {
  kLogVerbose,
  kLogInfo,
  kLogImportant,
  kLogWarning,
  kLogError,
  kNumLogLevels
};

/// @class Logger
/// @brief Output log messages if they are above an adjustable threshold.
///
/// A rudimentary logging system.
class Logger {
 public:
  Logger() : level_(kLogImportant) {}

  void set_level(LogLevel level) { level_ = level; }
  LogLevel level() const { return level_; }

  /// Output a printf-style message if our current logging level is
  /// >= `level`.
  void Log(LogLevel level, const char* format, ...) const;

 private:
  LogLevel level_;
};

/// @brief Returns a nullptr-terminated array of human-readable names for
///        AxisSystem.
/// @return Array of length kNumAxisSystems + 1, where the plus one is for
///         the nullptr at the end.
const char* const* AxisSystemNames();

/// @brief Given a name in the format of AxisSystemNames(), return the
///        corresponding AxisSystem enumeration value.
AxisSystem AxisSystemFromName(const char* name);

/// @brief Convert `scene` to the specified axis system.
///
/// This will most likely just modify the root transform to swap axes as
/// appropriate.
void ConvertFbxAxes(AxisSystem axis_system, FbxScene* scene, Logger* log);

/// @brief Convert from FBX's axis-system class to our AxisSystem enumeration.
AxisSystem FbxAxisSystemToAxisSystem(const FbxAxisSystem& axis);

/// @brief Convert from our AxisSystem enumeration to FBX's axis-system class.
FbxAxisSystem AxisSystemToFbxAxisSystem(AxisSystem system);

/// @brief Returns a nullptr-terminated array of human-readable names for
///        the distance units that we have values for.
const char* const* DistanceUnitNames();

/// @brief Given a name in the format of DistanceUnitNames(), return the unit's
///        length in centimeters.
///
/// For example, DistanceUnitFromName("inches") returns 2.54f.
float DistanceUnitFromName(const char* name);

/// @brief Convert `scene` to the specified distance unit.
///
/// Here, `distance_unit` is the length of the target unit, in centimeters.
/// So to convert the scene so that a single unit is one inch, `distance_unit`
/// should be 2.54f.
///
/// Note that FBX scenes always have a unit associated with them. The unit
/// can be specified when the FBX scene is exported, and one person might
/// export in a different unit than another. This function allows units to be
/// normalized across all FBX assets in the pipeline.
void ConvertFbxScale(float distance_unit, FbxScene* scene, Logger* log);

/// @brief Returns true if `node` or any of its children has a mesh.
///
/// Often we want to ignore any nodes that show nothing on screen.
bool NodeHasMesh(FbxNode* node);

/// @brief Log the local transform breakdown for each node in the hierarchy.
///
/// For debugging. Very useful to output the local transform matrices (and
/// component values) at a given time of the animation. We can compare these
/// to the runtime values, if something doesn't match up.
void LogFbxScene(const FbxScene* scene, int time_in_ms, LogLevel level,
                 Logger* log);

/// @brief Log one option per line, prepended by `indent`.
///
/// Utility function for logging.
void LogOptions(const char* indent, const char* const* array_of_options,
                Logger* log);

/// @brief Returns index of `name` in `array_of_names`, or -1 if `name` is not
///        found.
///
/// `array_of_names` is a null-terminated array of char* strings.
int IndexOfName(const char* name, const char* const* array_of_names);

}  // namespace fplutil

#endif  // FPLUTIL_FBX_COMMON_H
