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

"""This file updates code snippets in docs from code in test files.

To use put the following in your md file where you would like the code to be:
<!-- @doxysnippetstart NAME -->
<!-- @doxysnippetend -->

In the CPP (or CC) file include the following wrapped around the code:
/// @doxysnippetstart DocFile.md NAME
/// @doxysnippetend
"""

import argparse
import os
import re
import shutil
import sys
import tempfile

DOXYSNIPPETEND_RE = re.compile(r'.*\@doxysnippetend.*')
CPPDOXYSNIPPETSTART_RE = re.compile(
  r'.*\@doxysnippetstart\s+(?P<md_file>\S+)\s+(?P<token>\S+).*')
MDDOXYSNIPPETSTART_RE = re.compile(r'.*\@doxysnippetstart\s+(?P<token>\S+).*')


def find_file(name, path):
  """File the first file within a given path.

  Args:
    name: Name of the file to search for.
    path: Root of the path to search in.

  Returns:
    Full path of the given filename or None if not found.
  """
  for root, dirs, files in os.walk(path):
    if name in files:
      return os.path.join(root, name)
  return None


def parse_cpp_files(test_directory):
  """Parse cpp files looking for snippet marks.

  Args:
    test_directory: Directory to look for cpp files in.

  Returns:
    Tuple of file_list and snippet_list where file_list is a list of files that need to be
    updated with documentation and snippet_list is a dictionary of lists
    indexed by string tokens / identifiers.  The lists in the snippet_list dictionary
    contain lines of code snippets to be inserted at points identified by the
    token that indexes the set of lines.
  """
  file_list = []
  snippet_list = {}
  for path, dirs, files in os.walk(test_directory):
    for cpp_file in files:
      if not re.match(r'.*\.c(pp|c)$', cpp_file): continue
      parse_lines = False
      snippet_lines = []
      token = ''
      md_file = ''
      cpp_file_path = os.path.join(path, cpp_file)
      try:
        with open(cpp_file_path, 'r') as ccfile:
          for line in ccfile:
            match = CPPDOXYSNIPPETSTART_RE.match(line)
            if match:
              parse_lines = True
              group_dict = match.groupdict()
              md_file = group_dict['md_file']
              token = group_dict['token']
              if md_file not in file_list:
                file_list.append(md_file)
            elif DOXYSNIPPETEND_RE.match(line):
              parse_lines = False
              snippet_list[token] = snippet_lines
            elif parse_lines:
              snippet_lines.append(line)
      except IOError as e:
        print 'ERROR: Failed to open file %s: %s' % (cpp_file, e.strerror)
      if parse_lines is True:
        print 'WARNING: Count not find end of %s. Skipping.' % (token)
  return (file_list, snippet_list)


def update_md_files(md_directory, file_list, snippet_list):
  """Update md files from snippets.

  Args:
    md_directory: Directory to look for md files in.
    snippet_list: Array of snippets to put into the md files.
  """
  for md_file in file_list:
    path = find_file(md_file, md_directory)
    if not path:
      print >> sys.stderr, 'WARNING: Cannot find %s, skipping.' % md_file
      continue
    new_file_handle = tempfile.NamedTemporaryFile(delete=False)
    temp_file_name = new_file_handle.name
    write_lines = True
    try:
      with open(path, 'r') as mdfile:
        for line in mdfile:
          match = MDDOXYSNIPPETSTART_RE.match(line)
          if match:
            token = match.groupdict()['token']
            new_file_handle.write(line)
            if snippet_list.has_key(token):
              write_lines = False
              for snippet_line in snippet_list[token]:
                new_file_handle.write(snippet_line)
          elif DOXYSNIPPETEND_RE.match(line):
            write_lines = True
            new_file_handle.write(line)
          elif write_lines:
            new_file_handle.write(line)
    except IOError as e:
      print >> sys.stderr, (
        'ERROR: Failed to open file %s: %s' % (md_file, e.strerror))
      os.remove(path)
      continue
    if write_lines is False:
      print >> sys.stderr, 'WARNING: Count not find end of %s.' % (token)
    new_file_handle.close()
    os.remove(path)
    shutil.move(temp_file_name, path)


def main():
  parser = argparse.ArgumentParser(
      description=('Update code snippet docs.'))
  parser.add_argument(
      '-t', '--test-directory', required=True,
      help='Source directory for the test files.')
  parser.add_argument(
      '-m', '--md-directory', required=True,
      help='Source directory for the doxygen files.')

  args = parser.parse_known_args()[0]

  update_md_files(args.md_directory, *parse_cpp_files(args.test_directory))

if __name__ == '__main__':
  sys.exit(main())
