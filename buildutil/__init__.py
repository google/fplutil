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

"""Build utilities for use in automated build scripts and tools.

This module is a set of functions that can be used to help implement tools
to perform typical build tasks. The main focus is to enable turnkey building
both for users and also for continuous integration builds and tests.

Simple usage example:

  import buildutil.linux

  def main():
    env = buildutil.linux.BuildEnvironment(buildutil.linux.build_defaults())

    env.run_make()
    env.make_archive(['bin', 'lib', 'include'], 'output.zip')


Please see examples/buildutil/* for more comprehensive uses.
"""
