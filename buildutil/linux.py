# Copyright 2014 Google Inc. All Rights Reserved.
#
# This software is provided 'as-is', without any express or implied
# warranty.  In no event will the authors be held liable for any damages
# arising from the use of this software.
# Permission is granted to anyone to use this software for any purpose,
# including commercial applications, and to alter it and redistribute it
# freely, subject to the following restrictions:
# 1. The origin of this software must not be misrepresented; you must not
# claim that you wrote the original software. If you use this software
# in a product, an acknowledgment in the product documentation would be
# appreciated but is not required.
# 2. Altered source versions must be plainly marked as such, and must not be
# misrepresented as being the original software.
# 3. This notice may not be removed or altered from any source distribution.
#

_CMAKE_PATH = 'cmake_path'
_CMAKE_FLAGS = 'cmake_flags'

def build_defaults():
  """Helper function to set build defaults.

  Returns:
    A dict containing appropriate defaults for a build.
  """
  args[_CMAKE_PATH] = (os.getenv(_CMAKE_PATH_ENV_VAR) or
                       distutils.spawn.find_executable('cmake'))
  args[_CMAKE_FLAGS] = os.getenv(_CMAKE_FLAGS_ENV_VAR)

  return args


def add_arguments(parser):
  """Add module-specific command line arguments to an argparse parser.

  This will take an argument parser and add arguments appropriate for this
  module. It will also set appropriate default values.

  Args:
    parser: The argparse.ArgumentParser instance to use.
  """
  defaults = build_defaults()

  parser.add_argument('-c', '--' + _CMAKE_PATH,
                      help='Path to CMake binary', dest=_CMAKE_PATH,
                      default=defaults[_CMAKE_PATH])
  parser.add_argument(
      '-F', '--' + _CMAKE_FLAGS, help='Flags to use to override CMake flags',
      dest=_CMAKE_FLAGS, default=defaults[_CMAKE_FLAGS])


class BuildEnvironment(object):

  def __init__(self, arguments):
    """Constructs the BuildEnvironment with basic information needed to build.

    The build properties as set by argument parsing are also available
    to be modified by code using this object after construction.

    It is required to call this function with a valid arguments object,
    obtained either by calling argparse.ArgumentParser.parse_args() after
    adding this modules arguments via buildutils.add_arguments(), or by passing
    in an object returned from buildutils.build_defaults().

    Args:
      arguments: The argument object returned from ArgumentParser.parse_args().
    """

    if type(arguments) is dict:
      args = arguments
    else:
      args = vars(arguments)


    self.cmake_path = args[_CMAKE_PATH]
    self.cmake_flags = args[_CMAKE_FLAGS]


  def run_cmake(self, gen='Unix Makefiles'):
    """Run cmake based on the specified build environment.

    This will execute cmake using the configured environment, passing it the
    flags specified in the cmake_flags property.

    Args:
      gen: Optional argument to specify CMake project generator (defaults to
        Unix Makefiles)

    Raises:
      SubCommandError: CMake invocation failed or returned an error.
      ToolPathError: CMake not found in configured build environment or $PATH.
    """

    _check_binary('cmake', self.cmake_path)

    args = [self.cmake_path, '-G', gen]
    if self.cmake_flags:
      args += shlex.split(self.cmake_flags, posix=self._posix)
    args.append(self.project_directory)

    self.run_subprocess(args, cwd=self.project_directory)
