#!/usr/bin/python
# Copyright 2014 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Generate html documentation from markdown and doxygen comments."""

import argparse
import distutils.spawn
import os
import re
import shutil
import subprocess
import sys

## Matches output directory statement in doxyfile.
DOXYFILE_OUTPUT_DIRECTORY_RE = re.compile(r'OUTPUT_DIRECTORY *= *(.*)')
## Determines whether py_filter is being used.
DOXYFILE_FILTER_PATTERNS = re.compile(r'FILTER_PATTERNS *= *\*.py=py_filter')


class CommandFailedError(Exception):
  """Error raised when a command returns a non-zero error code.

  Attributes:
    command: Command that failed.
    status: Error code.
  """

  def __init__(self, command, status):
    """Initialize this instance.

    Args:
      command: Command that failed.
      status: Error code.
    """
    super(CommandFailedError, self).__init__(command)
    self.command = command
    self.status = status


class LinkLintError(Exception):
  """Raised if linklint finds errors."""
  pass


class DoxyfileError(Exception):
  """Raised if there is a problem parsing the doxygen configuration file."""
  pass


class PyFilterNotFoundError(Exception):
  """Raised if py_filter isn't found."""
  pass


def run_command(*popenargs, **kwargs):
  """Run a command, raising CommandFailedError if it fails.

  Args:
    *popenargs: Non-keyword arguments passed to subprocess.Popen().
    **kwargs: Keyword arguments passed to subprocess.Popen().

  Raises:
    CommandFailedError: If the command returns a non-zero error code.
  """
  ret = subprocess.call(*popenargs, **kwargs)
  if ret != 0:
    raise CommandFailedError(repr(popenargs), ret)


def clean_index(output_dir):
  """Clean up the generated index.html.

  Args:
    output_dir: Docs output directory.
  """
  index_html = os.path.join(output_dir, 'index.html')
  lines = []
  with open(index_html) as f:
    for l in f:
      if ' Documentation</div>' in l:
        l = l.replace(' Documentation</div>', '</div>')
      lines.append(l)

  f = open(index_html, 'w')
  f.write('\n'.join(lines))
  f.close()


def link_lint(output_dir, results_dir):
  """Run linklint if it's found in the PATH.

  Get this from http://www.linklint.org/.

  Args:
    output_dir: Directory to run linklint in.
    results_dir: Directory to store linklink results.

  Raises:
    LinkLintError: If linklint finds a problem.
  """
  linklint = distutils.spawn.find_executable('linklint')
  if linklint:
    run_command([linklint, '-no_anchors', '-orphan', '-root',
                 output_dir, '/@', '-doc', results_dir], cwd=output_dir)
    with open(os.path.join(results_dir, 'index.html')) as f:
      lines = f.readlines()
      if [l for l in lines if 'ERROR' in l]:
        raise LinkLintError('linklint detected errors, results are available '
                            'for inspection in\n%s' % results_dir)
      if [l for l in lines if 'https' in l]:
        raise LinkLintError('linklint detected https links, github does not '
                            'support https')
  else:
    print >>sys.stderr, 'WARNING: linklint not found.'


def doxyfile_check_py_filter(source_dir):
  """Verify py_filter is installed if it's used in the doxygen config file.

  Args:
    source_dir: Directory which contains the doxyfile.

  Raises:
    PyFilterNotFoundError: If py_filter isn't found in the PATH.
  """
  doxyfile = os.path.join(source_dir, 'doxyfile')
  using_py_filter = False
  with open(doxyfile) as f:
    using_py_filter = [l for l in f.readlines() if
                       DOXYFILE_FILTER_PATTERNS.match(l)]
  if using_py_filter:
    if not distutils.spawn.find_executable('py_filter'):
      raise PyFilterNotFoundError()


def doxyfile_get_output_dir(source_dir):
  """Get the output directory from a doxygen configuration file.

  Args:
    source_dir: Directory which contains the doxyfile.

  Returns:
    Doxygen output_directory.

  Raises:
    DoxyfileError: If the output directory isn't found.
  """
  doxyfile = os.path.join(source_dir, 'doxyfile')
  with open(doxyfile) as f:
    for l in f:
      m = DOXYFILE_OUTPUT_DIRECTORY_RE.match(l)
      if m:
        value = m.groups()[0]
        if value.startswith('"'):
          value = value[1:-1]
        return os.path.realpath(os.path.join(source_dir, value, 'html'))
  raise DoxyfileError('OUTPUT_DIRECTORY not found in %s.' % doxyfile)


def main():
  """Generate html documentation from markdown and doxygen comments.

  This requires:
  * doxygen version 1.8.5 or above.
  * doxypypy (see https://github.com/Feneric/doxypypy)
    - git clone https://github.com/Feneric/doxypypy
    - cd doxypypy
    - python -m setup install
  * linklink (optional)

  Returns:
    0 if successful, non-zero otherwise.
  """
  parser = argparse.ArgumentParser()
  parser.add_argument('--linklint-dir', help=(
      'Directory where the results of linklint are stored.  If this isn\'t '
      'specified it defaults to the directory containing this script.'))
  parser.add_argument('--source-dir', help=(
      'Doxygen documentation source directory.  If this isn\'t specified '
      'it defaults to the src/ directory under the directory containing this '
      'script.'))
  args = parser.parse_args()

  this_dir = os.path.realpath(os.path.dirname(__file__))

  # Process the arguments.
  linklint_dir = os.path.realpath(
      args.linklint_dir if args.linklint_dir else this_dir)
  source_dir = os.path.realpath(
      args.source_dir if args.source_dir else os.path.join(this_dir, 'src'))

  # Add this module's directory to the path so that doxygen will find the
  # py_filter scripts.
  os.environ['PATH'] = os.pathsep.join([this_dir, os.getenv('PATH')])

  # Get the documentation output directory.
  output_dir = doxyfile_get_output_dir(source_dir)
  # If py_filter is referenced by doxyfile, verify py_filter is installed.
  doxyfile_check_py_filter(source_dir)

  # Clean the output directory.
  if os.path.exists(output_dir):
    shutil.rmtree(output_dir)

  try:
    run_command('doxygen', shell=True, cwd=source_dir)
    clean_index(output_dir)
    link_lint(output_dir, os.path.join(linklint_dir, 'linklint_results'))
  except CommandFailedError, e:
    print >> sys.stderr, 'Error %d while running %s' % (e.status, e.command)
    return e.status
  except LinkLintError, e:
    print >> sys.stderr, 'Error %s' % str(e)
    return 1

  return 0


if __name__ == '__main__':
  sys.exit(main())
