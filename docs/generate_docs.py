#!/usr/bin/python
# Copyright 2014 Google Inc. All rights reserved.
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

import distutils.spawn
import os
import re
import shutil
import subprocess
import sys

# Matches output directory statement in doxyfile.
DOXYFILE_OUTPUT_DIRECTORY_RE = re.compile('OUTPUT_DIRECTORY *= *(.*)')
# Determines whether py_filter is being used.
DOXYFILE_FILTER_PATTERNS = re.compile('FILTER_PATTENS *= *\*.py=py_filter')


class CommandFailedError(Exception):
  """Error raised when a command returns a non-zero error code.

  Attributes:
    command: Command that failed.
    status: Error code.
  """

  def __init__(command, status):
    """Initialize this instance.

    Args:
      command: Command that failed.
      status: Error code.
    """
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
    for l in f.readlines():
      if ' Documentation</div>' in l:
        l = l.replace(' Documentation</div>', '</div>')
      lines.append(l)

  f = open(index_html, 'w')
  f.write('\n'.join(lines))
  f.close()


def link_lint(output_dir, results_dir):
  """Run linklint if it's found in the PATH.

  Args:
    output_dir: Directory to run linklint in.
    results_dir: Directory to store linklink results.
  """
  linklint = distutils.spawn.find_executable('linklint')
  if linklint:
    run_command([linklint, '-no_anchors', '-orphan',  '-root',
                 output_dir, '/@', '-doc', results_dir], cwd=output_dir)
    with open(os.path.join(results_dir, 'index.html')) as f:
      lines = f.readlines()
      if [l for l in lines if 'ERROR' in l]:
        raise LinkLintError('linklint detected errors, results are available '
                            'for inspection in\n%s' % results_dir)
      if [l for l in lines if 'https' in l]:
        raise LinkLintError('linklint detected https links, github does not '
                            'support https')

def doxyfile_check_py_filter(source_dir):
  """If py_filter is used in the doxygen configuration file.

  Args:
    source_dir: Directory which contains the doxyfile.

  Raises:
    PyFilterNotFoundError if py_filter isn't found in the PATH.
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
    DoxyfileError if the output directory isn't found.
  """
  doxyfile = os.path.join(source_dir, 'doxyfile')
  with open(doxyfile) as f:
    for l in f.readlines():
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
  """
  this_dir = os.path.realpath(os.path.dirname(__file__))
  project_root = os.path.realpath(os.path.join(this_dir, os.pardir))
  docs_dir = os.path.join(project_root, 'docs')
  source_dir = os.path.join(docs_dir, 'src')
  output_dir = doxyfile_get_output_dir(source_dir)
  doxyfile_check_py_filter(source_dir)

  # Add this module's directory to the path so that doxygen will find the
  # py_filter scripts.
  os.putenv('PATH', os.pathsep.join([this_dir, os.getenv('PATH')]))

  # Clean the output directory.
  if os.path.exists(output_dir):
    shutil.rmtree(output_dir)

  try:
    run_command('doxygen', shell=True, cwd=source_dir)
    clean_index(output_dir)
    link_lint(output_dir, os.path.join(docs_dir, 'linklint_results'))
  except CommandFailedError, e:
    print >> sys.stderr,  'Error %d while running %s' % (e.status, e.command)
    return e.status
  except LinkLintError, e:
    print >> sys.stderr,  'Error %s' % str(e)
    return 1

  return 0


if __name__ == '__main__':
  sys.exit(main())
