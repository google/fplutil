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
import distutils.dir_util
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
## Directory copied from the source docs dir to the output directory.
HTML_OVERLAY_DIRECTORY = 'html_overlay'


class LinkLintError(Exception):
  """Raised if linklint finds errors."""
  pass


class DoxyfileError(Exception):
  """Raised if there is a problem parsing the doxygen configuration file."""
  pass


class PyFilterNotFoundError(Exception):
  """Raised if py_filter isn't found."""
  pass


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

def copy_overlay(overlay_dir, output_dir):
  """Copy overlay_dir into the output_dir if overlay_dir exists.

  Args:
    overlay_dir: Directory to copy files from.
    output_dir: Directory to copy files from overlay_dir to.
  """
  if os.path.exists(overlay_dir):
    distutils.dir_util.copy_tree(overlay_dir, output_dir)

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
    subprocess.check_call(
        [linklint, '-no_anchors', '-orphan', '-root',
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
    try:
      import doxypypy.doxypypy
    except Exception:
      raise PyFilterNotFoundError(
        'Doxpy not found, install https://github.com/Feneric/doxypypy')


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
  parser.add_argument('--project-dir', help=(
      'Root of the project containing documentation. Filenames are generated '
      'from paths to files relative to this directory.'), default=os.getcwd())
  parser.add_argument('--use-common-overlay', help=(
      'Whether the ${SHARED_DOCS_PATH}/html_overlay directory should be copied'
      'to the output html directory in addition to the html_overlay directory '
      'in the same directory as doxyfile'),
      default=True)
  args = parser.parse_args()

  this_dir = os.path.realpath(os.path.dirname(__file__))

  # Import this module to get its' path
  import generate_docs as gen_docs_path
  generate_docs_dir = os.path.realpath(os.path.dirname(gen_docs_path.__file__))

  # Process the arguments.
  linklint_dir = os.path.realpath(
      args.linklint_dir if args.linklint_dir else this_dir)
  source_dir = os.path.realpath(
      args.source_dir if args.source_dir else os.path.join(this_dir, 'src'))

  # Add this module's directory to the path so that doxygen will find the
  # py_filter scripts.
  os.environ['PATH'] = os.pathsep.join([this_dir, os.getenv('PATH')])

  shared_docs_path = os.environ.get('SHARED_DOCS_PATH',
                                    os.path.join(generate_docs_dir, 'src'))
  os.environ['SHARED_DOCS_PATH'] = shared_docs_path

  # Get the documentation output directory.
  output_dir = doxyfile_get_output_dir(source_dir)
  # If py_filter is referenced by doxyfile, verify py_filter is installed.
  doxyfile_check_py_filter(source_dir)

  # Clean the output directory.
  if os.path.exists(output_dir):
    shutil.rmtree(output_dir)

  # Change into the common directory for the docs so that doxygen doesn't
  # embed the complete path into generated filenames.
  cwd = os.getcwd()
  os.chdir(args.project_dir)

  try:
    subprocess.check_call(['doxygen'], shell=True, cwd=source_dir)
    clean_index(output_dir)
    copy_overlay(os.path.join(source_dir, HTML_OVERLAY_DIRECTORY), output_dir)
    if args.use_common_overlay:
      copy_overlay(os.path.join(shared_docs_path, HTML_OVERLAY_DIRECTORY),
                   output_dir)
    link_lint(output_dir, os.path.join(linklint_dir, 'linklint_results'))
  except subprocess.CalledProcessError as e:
    print >> sys.stderr, 'Error %d while running %s' % (e.returncode, e.cmd)
    return 'You must have "doxygen" installed to run "generate_docs.py".'
  except LinkLintError, e:
    print >> sys.stderr, 'Error %s' % str(e)
    return 1
  finally:
    os.chdir(cwd)

  return 0


if __name__ == '__main__':
  sys.exit(main())
