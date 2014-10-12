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

"""Checkout the Android tree and build perf along with the perfhost tool."""

import argparse
import collections
from HTMLParser import HTMLParser
import multiprocessing
import os
import platform
import re
import shutil
import subprocess
import sys
import urllib2
import xml.etree.ElementTree

## This script's directory.
SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))

## Page which contains the mapping between Android API levels and source tags.
BUILD_NUMBERS_URL = 'http://source.android.com/source/build-numbers.html'

## URL of the repo manifest git project for Android.
ANDROID_REPO_MANIFEST_URL = (
    'https://android.googlesource.com/platform/manifest')
## Repo's current manifest path.
REPO_MANIFEST_PATH = os.path.join('.repo', 'manifest.xml')

## Regular expression which matches the projects that need to be fetched to
## build perf and perfhost.
REPO_PROJECTS_RE = re.compile(
    r'('
    r'^bionic$|'
    r'^build$|'
    r'^external/clang$|'
    r'^external/compiler-rt$|'
    r'^external/elfutils$|'
    r'^external/gcc-demangle$|'
    r'^external/gtest$|'
    r'^external/jemalloc$|'
    r'^external/libcxx$|'
    r'^external/linux-tools-perf$|'
    r'^external/llvm$|'
    r'^external/safe-iop$|'
    r'^external/stlport$|'
    r'^frameworks/native$|'  # Required for AOSP <= 4.1.2_r2.1.
    r'^prebuilts/clang/.*$|'
    r'^prebuilts/ndk$|'
    r'^prebuilts/gcc/.*$|'
    r'^system/core$'
    r')')

## Regular expression which matches the OSX host toolchain projects.
REPO_PROJECTS_DARWIN_HOST_GCC_RE = re.compile(
    r'^prebuilts/gcc/darwin-x86/host/.*')

## Makefile that needs to be patched to disable the installed Java version
## check.
BUILD_CORE_MAIN_MK = os.path.join('build', 'core', 'main.mk')
## Regular expression which matches conditional expressions in
## BUILD_CORE_MAIN_MK that need to be disabled to remove the java version
## check.
MAIN_MK_JAVA_VERSION_RE = re.compile(
    r'[^#]?ifn?eq *\(.*\$\((java_version|java_version_str|javac_version|'
    r'shell java -version .*)\)')

## Regular expression which matches a Android lunch (build tool) option string.
LUNCH_OPTION_RE = re.compile(r'\s*([0-9]+)\.\s*([a-zA-Z0-9_-]+)')

## Project which contains the source for perf and perfhost.
LINUX_TOOLS_PERF_PATH = 'external/linux-tools-perf'

## Build targets that the project in LINUX_TOOLS_PERF_PATH depends upon.
LINUX_TOOLS_PERF_DEPENDENCIES = (
    'bionic/',
    'build/libs/host/',
    'build/tools/acp',
    'external/clang',
    'external/compiler-rt',
    'external/elfutils',
    'external/gcc-demangle',
    'external/gtest/src',
    'external/llvm',
    'external/stlport',
    'system/core/libcutils',
    'system/core/liblog')

## Regular expression which matches API levels in BUILD_NUMBERS_URL.
ANDROID_API_LEVEL_RE = re.compile(r'API level ([0-9]+)($|, NDK ([0-9]+))')

## Regular expression which matches source tags in BUILD_NUMBERS_URL.
ANDROID_SOURCE_TAG_RE = re.compile(r'android-(.*)_r([0-9].*)')

## Number of components in a source tag version number.
ANDROID_SOURCE_TAG_VERSION_COMPONENTS = 3

## Number of components in a source tag revision number.
ANDROID_SOURCE_TAG_REVISION_COMPONENTS = 3


class CommandError(Exception):
  """Exception raised when a shell command fails.

  Attributes:
    error: Error message.
    command: Command that failed.
    returnstatus: Status of the command that failed.
    stdout: Standard output stream of the failed command.
    stderr: Standard error stream of the failed command.
  """

  def __init__(self, error, command, returnstatus, stdout=None, stderr=None):
    """Initialize this instance.

    Args:
      error: Error message.
      command: Command that failed.
      returnstatus: Status of the command that failed.
      stdout: Standard output stream of the failed command.
      stderr: Standard error stream of the failed command.
    """
    super(CommandError, self).__init__(error)
    self.command = command
    self.returnstatus = returnstatus
    self.stdout = stdout
    self.stderr = stderr
    self.error = error

  def __str__(self):
    """Return a string representation of this exception.

    Returns:
      String representation of this exception.
    """
    return '%s: %s (%d) %s%s' % (self.error, self.command, self.returnstatus,
                                 self.stdout if self.stdout else '',
                                 self.stderr if self.stderr else '')


def run_command(command, error_string, cwd=None, verbose=False):
  """Run a command in the shell raising CommandError if it fails.

  Args:
    command: Shell command string to execute.
    error_string: String used to prefix the error message that is attached to
      the raised CommandError exception.
    cwd: Working directory used to run the command.
    verbose: Whether to display the command and the working directory.

  Raises:
    CommandError: If the command returns a non-zero status code.
  """
  if verbose:
    print >> sys.stderr, command, cwd
  # If this is Linux or OSX force the use of the bash shell.
  shell = '/bin/bash' if platform.system() in ('Darwin', 'Linux') else None
  process = subprocess.Popen(command, shell=True, cwd=cwd, executable=shell)
  if process.wait() != 0:
    raise CommandError(error_string, command, process.returncode)


def run_command_get_output(command, error_string, cwd=None, verbose=False,
                           stdin=None):
  """Run a command in the shell raising CommandError if it fails.

  Args:
    command: Shell command string to execute.
    error_string: String used to prefix the error message that is attached to
      the raised CommandError exception.
    cwd: Working directory used to run the command.
    verbose: Whether to display the command and the working directory.
    stdin: String to send to the standard input stream of the command.

  Returns:
    The standard output stream.

  Raises:
    CommandError: If the command returns a non-zero status code.
  """
  if verbose:
    print >> sys.stderr, command, cwd if cwd else ''
  process = subprocess.Popen(command, shell=True, cwd=cwd,
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE)
  stdout, stderr = process.communicate(input=stdin if stdin else '')
  if process.returncode != 0:
    raise CommandError(error_string, command, process.returncode,
                       stdout=stdout, stderr=stderr)
  return stdout


def format_build_command(command):
  """Format a command string so that it runs in the Anroid build environment.

  Args:
    command: Command to format.

  Returns:
    Command modified to run in the Android build environment.
  """
  environment = []
  if platform.system() == 'Darwin':
    environment.append('export BUILD_MAC_SDK_EXPERIMENTAL=1')
  return ' && '.join(environment + ['source ./build/envsetup.sh', command])


def run_build_command(command, error_string, cwd=None, verbose=False):
  """Run a command in the shell with the Android build environment.

  Args:
    command: Shell command string to execute.
    error_string: String used to prefix the error message that is attached to
      the raised CommandError exception.
    cwd: Working directory used to run the command.
    verbose: Whether to display the command and the working directory.

  Raises:
    CommandError: If the command returns a non-zero status code.
  """
  run_command(format_build_command(command), error_string, cwd=cwd,
              verbose=verbose)


def repo_init(url, branch, verbose=False):
  """Initialize a directory to work with repo.

  Args:
    url: URL of the manifest.
    branch: Branch to pull the manifest from in the git project specified by
      the URL.
    verbose: Whether to display verbose output from the command.

  Raises:
    CommandError: If the initialization process fails.
  """
  run_command('repo init -u %s -b %s' % (url, branch),
              'Unable to initialize repo', verbose=verbose)


def extract_project_paths_from_repo_manifest():
  """Parse project paths from the repo manifest in the current directory.

  Returns:
    A list of project paths parsed from the current repo manifest.
  """
  paths = []
  tree = xml.etree.ElementTree.parse(REPO_MANIFEST_PATH)
  for project in tree.getroot().iter('project'):
    path = project.attrib.get('path')
    if path:
      paths.append(path)
  return paths


def repo_sync(projects, verbose=False):
  """Sync a set of projects from the manifest.

  Args:
    projects: List of project paths to sync.  If no paths are specified all
     projects in the manifest are downloaded.
    verbose: Whether to display verbose output from the command.

  Raises:
    CommandError: If the sync fails.
  """
  run_command('repo sync -j%d %s' % (multiprocessing.cpu_count(),
                                     ' '.join(projects)),
              'Unable to sync projects', verbose=verbose)


def reset_git_projects_to_head(search_directory=os.curdir,
                               verbose=False):
  """Reset all git projects in the current directory to the head revision.

  Args:
    search_directory: Directory to search for git projects.
    verbose: Whether to display verbose output from the command.

  Raises:
    CommandError: If git reset fails.
  """
  for dirpath, dirnames, _ in os.walk(search_directory):
    if '.git' in dirnames:
      dirnames = []
      for cmd in ['git reset --hard HEAD', 'git clean -dfx']:
        run_command(cmd, 'Unable to reset git project %s' % dirpath,
                    cwd=dirpath, verbose=verbose)


def patch_checks_in_makefile(filename, ifregexp):
  """Disable environment checks in a makefile.

  Args:
    filename: File to patch.
    ifregexp: Regular expression of if statements to disable.
  """
  output_lines = []
  with open(filename) as f:
    for line in f:
      if ifregexp.match(line):
        line = 'ifeq (0,1) #' + line
      output_lines.append(line)

  with open(filename, 'w') as f:
    f.writelines(output_lines)


def lunch_get_options(verbose=False):
  """Get the set of available build options from the lunch command.

  Args:
    verbose: Whether to display verbose output from the command.

  Returns:
    (option_integer, description_string) tuple where option_integer is the
    value used to select a lunch build option and description_string is a
    string which describes the option.

  Raises:
    CommandError: If the lunch fails to return a selection.
  """
  cmd = format_build_command('lunch')
  try:
    stdout = run_command_get_output(cmd, '', stdin='1' + os.linesep,
                                    verbose=verbose)
  except CommandError as error:
    stdout = error.stdout
  options = []
  for l in stdout.splitlines():
    m = LUNCH_OPTION_RE.match(l)
    if m:
      selection, description = m.groups()
      options.append((int(selection), description))
  if not options:
    raise CommandError('Unable to retrieve selection from lunch: %s' % cmd)
  return options


def build_perf(lunch_option, version, verbose=False):
  """Build Android perf for the architecture specified by the lunch option.

  This also builds perfhost for the host architecture.

  Args:
    lunch_option: Integer which specifies the lunch option used to select the
      target architecture.
    version: Numerical version of the source tree.
    verbose: Whether to display commands during the build process.

  Raises:
    Error: If the build fails.
  """
  showcommands = 'showcommands' if verbose else ''
  # Prior to 4.3.1 the AOSP build environment did not have a command to build
  # a target and its dependencies.
  if version <= version_to_value('4.3.1', True):
    build_command = 'mmm -j%d %s %s %s:perf,perfhost' % (
        multiprocessing.cpu_count(), showcommands,
        ' '.join(LINUX_TOOLS_PERF_DEPENDENCIES), LINUX_TOOLS_PERF_PATH)
  else:
    build_command = 'mmma -j%d %s %s' % (
        multiprocessing.cpu_count(), showcommands, LINUX_TOOLS_PERF_PATH)
  run_build_command(' && '.join(('lunch %d' % lunch_option, build_command)),
                    'Build of %s failed' % LINUX_TOOLS_PERF_PATH,
                    verbose=verbose)


def make_clean(verbose=False):
  """Clean all build targets.

  Args:
    verbose: Whether to display commands during the build process.

  Raises:
    Error: If the clean fails.
  """
  run_build_command('make clean', 'Clean failed', verbose=verbose)


class ApiLevelSourceTagsParser(HTMLParser):
  """Parses API levels and source tags for Android builds.

  Attributes:
    tables: Dictionary of tables where each table contains a dictionary for
      each row indexed by column name.
    header_id: ID of the most recent h2 tag which identifies the table being
      parsed.
    tag: Current tag being parsed.
    table_columns: Current set of columns for the table being parsed.
    table_column_index: Index of the current column being parsed which can be
      used to look up the name of the column in "table_columns".
    table_row: Dictionary of the current row being parsed.

  Class Attributes:
    API_LEVELS_ID: ID of the API levels table in the "tables" attribute.
    SOURCE_TAGS_ID: ID of the source tags table in the "tables" attribute.
  """

  API_LEVELS_ID = 'platform-code-names-versions-api-levels-and-ndk-releases'
  SOURCE_TAGS_ID = 'source-code-tags-and-builds'

  def __init__(self):
    """Initialize this instance."""
    HTMLParser.__init__(self)
    self.tables = collections.defaultdict(list)
    self.reset_parse_state()

  def reset_parse_state(self):
    """Reset the parsing state of this class."""
    self.header_id = ''
    self.tag = ''
    self.table_columns = []
    self.table_column_index = 0
    self.table_row = {}

  def valid_table_header(self):
    """Determine whether the current header is a valid table header.

    Returns:
       True if the table header is in the set of tables recognized by this
       class.
    """
    return self.header_id in (ApiLevelSourceTagsParser.API_LEVELS_ID,
                              ApiLevelSourceTagsParser.SOURCE_TAGS_ID)

  def handle_starttag(self, tag, attrs):
    """Store the current tag and its' id attribute if it's a h2 tag.

    Args:
      tag: Tag to parse.
      attrs: List of attributes to search for an id attribute.
    """
    self.tag = tag
    if tag == 'h2':
      for attr_id, attr_value in attrs:
        if attr_id == 'id':
          self.header_id = attr_value

  def handle_endtag(self, tag):
    """Parse the end of a table row or column.

    If the tag specifies the end of a table row, the currently parsed row is
    added to the active table.  If the tag is the end of a column,
    table_column_index is incremented.  If the tag is the end of a table the
    parse state is reset using reset_parse_state().

    Args:
      tag: End tag to parse.
    """
    if tag == 'table':
      self.reset_parse_state()
    if tag == 'tr':
      self.table_column_index = 0
      if self.valid_table_header() and self.table_row:
        self.tables[self.header_id].append(self.table_row)
        self.table_row = {}
    if tag == 'td':
      self.table_column_index += 1
    self.tag = ''

  def handle_data(self, data):
    """Parse data from the table.

    If the tag a header, the data is added to table_columns.  If the tag is
    data it's added as a column to the row currently being parsed.

    Args:
      data: Data to parse.
    """
    if self.valid_table_header():
      if self.tag == 'th':
        self.table_columns.append(data)
      elif self.tag == 'td':
        column_name = self.table_columns[self.table_column_index]
        self.table_row[column_name] = data


def version_to_value(version, wildcard_min, base=100,
                     components=(ANDROID_SOURCE_TAG_VERSION_COMPONENTS +
                                 ANDROID_SOURCE_TAG_REVISION_COMPONENTS) - 1):
  """Convert a version string to an integer range.

  Args:
    version: Version string to convert to an integer.
    wildcard_min: Whether to replace "x" with 0 (True) or the one minus the
      value of "base".
    base: Base used to multiply each component of the version number with the
      offset of the component in the version string.
    components: One minus the maximum number of components in the version
      string.

  Returns:
    Integer version value.
  """
  value = 0
  version_tokens = version.split('.')
  assert len(version_tokens) - 1 <= components
  version_tokens.extend(['x'] * (components + 1 - len(version_tokens)))
  for component in version_tokens:
    if component == 'x':
      component_value = 0 if wildcard_min else base - 1
    else:
      # Convert letters to integers - assuming ASCII characters.
      component = ''.join([c for c in component if c.isdigit()])
      component_value = int(component)
      component_value += sum([ord(c) - ord('a')
                              for c in component if not c.isdigit()])
    assert component_value < base
    value += component_value * (base ** components)
    components -= 1
  return value


def version_to_range(version):
  """Convert a version string to an integer range.

  Args:
    version: Version string to convert to an integer range.

  Returns:
    (min_version, max_version) where min_version and max_version is an
    inclusive range of the minimum and maximum version values respectively
    generated by version_to_value().
  """
  range_tokens = version.split(' - ')
  if len(range_tokens) == 1:
    range_tokens.append(range_tokens[0])
  return (version_to_value(range_tokens[0], True),
          version_to_value(range_tokens[1], False))


def extract_version_from_source_tag(source_tag):
  """Extract a version string from a source tag.

  Args:
    source_tag: Source tag to parse for a version string.

  Returns:
    Version string.
  """
  m = ANDROID_SOURCE_TAG_RE.match(source_tag)
  if not m:
    return ''
  version = m.groups()[0]
  version_components = version.split('.')
  version_components.extend(['0'] * (ANDROID_SOURCE_TAG_VERSION_COMPONENTS -
                                     len(version_components)))
  return '.'.join(version_components + m.groups()[1].split('.'))


def get_released_branches():
  """Parse the set of released branches from http://source.android.com/.

  Returns:
    Dictionary of (source_tag, version_value) tuples indexed by API level
    integers  where source_tag is the repo branch which contains the API
    version and version_value is an integer representation of the version tag.
  """
  parser = ApiLevelSourceTagsParser()
  parser.feed(urllib2.urlopen(BUILD_NUMBERS_URL).read())
  # Get the distinct list of Android versions that map to each API level and
  # support the NDK.
  api_level_to_version_range = {}
  ndk_api_version = 0
  for row in parser.tables[ApiLevelSourceTagsParser.API_LEVELS_ID]:
    api_level_string = row['API level']
    groups = ANDROID_API_LEVEL_RE.match(api_level_string).groups()
    ndk_api_version = int(groups[2]) if groups[2] else ndk_api_version
    if ndk_api_version > 0:
      api_level = int(groups[0])
      api_level_to_version_range[api_level] = version_to_range(row['Version'])

  api_level_to_source_tag = {}
  for row in parser.tables[ApiLevelSourceTagsParser.SOURCE_TAGS_ID]:
    source_tag = row['Branch']
    version = extract_version_from_source_tag(source_tag)
    if version:
      version_value = version_to_value(version, True)
      for api_level, version_range in api_level_to_version_range.iteritems():
        if (version_value >= version_range[0] and
            version_value <= version_range[1]):
          if (version_value >
              api_level_to_source_tag.get(api_level, ('', 0))[1]):
            api_level_to_source_tag[api_level] = (source_tag, version_value)
            break

  return api_level_to_source_tag


def apply_patches(verbose=False):
  """Apply any patches to the source required to build perf and perfhost.

  Args:
    verbose: Whether to display commands during the build process.
  """
  for dirpath, _, filenames in os.walk(SCRIPT_DIRECTORY):
    if '@' in dirpath:
      filename = os.path.basename(dirpath)
      project_path = filename.replace('@', os.path.sep)
      if not os.path.exists(project_path):
        if verbose:
          print >> sys.stderr, '%s does not exist, skipping.' % project_path
        continue

      commit_id = run_command_get_output(
          'git log -n 1 --format=format:%H',
          'Unable to get commit for project %s' % project_path,
          cwd=project_path, verbose=verbose)
      for patch in filenames:
        if commit_id == os.path.splitext(patch)[0]:
          patch_filename = os.path.join(dirpath, patch)
          run_command('git apply %s' % patch_filename,
                      'Unable to apply patch %s to %s' % (patch_filename,
                                                          project_path),
                      cwd=project_path, verbose=verbose)
          break


def archive_build_artifacts(archive_dir, api_level, source_tag, url):
  """Archive build artfiacts.

  Saves Android perf binaries to
    {archive_dir}/android-{api_level}/arch-{target_arch}
  and the host binaries to
    {archive_dir}/android-{api_level}/{host_os}-{host_arch}

  Args:
    archive_dir: Directory to copy artifacts to.
    api_level: API level of the source used to build perf binaries.
    source_tag: Source tag / branch perf was built from.
    url: Manifest project which contains references to the source required
      to build these binaries.
  """
  android_api_level = 'android-%d' % api_level
  for dirpath, _, filenames in os.walk('out'):
    source_file = ''
    target_dir = ''
    if 'perf' in filenames:
      arch_tokens = os.path.basename(os.path.abspath(
          os.path.join(dirpath, os.pardir, os.pardir))).split('_')
      if len(arch_tokens) == 1:
        arch_tokens.append('arm')
      source_file = os.path.join(dirpath, 'perf')
      target_dir = os.path.join(archive_dir, android_api_level,
                                'arch-%s' % arch_tokens[1])
    elif 'perfhost' in filenames:
      arch = os.path.basename(os.path.abspath(os.path.join(
          dirpath, os.pardir)))
      if arch == 'EXECUTABLES':
        continue
      source_file = os.path.join(dirpath, 'perfhost')
      target_dir = os.path.join(archive_dir, android_api_level, arch)
    if source_file and target_dir:
      print source_file, '-->', target_dir
      if not os.path.exists(target_dir):
        os.makedirs(target_dir)
      target_file = os.path.basename(source_file)
      with open(os.path.join(target_dir, 'build_info'), 'w') as f:
        f.write('%s built from %s branch %s%s' % (
            target_file, url, source_tag, os.linesep))
      shutil.copy(source_file, os.path.join(target_dir, target_file))


def sync_projects(manifest_url, source_version, source_tag, verbose=False):
  """Prepare the source tree for a build.

  Args:
    manifest_url: URL of the repo manifest to use for synchronization.
    source_version: Integer version derived from the source tag.
    source_tag: Tag / branch to sync from the manifest.
    verbose: Whether to display executed commands.

  Returns:
    A list of projects that need to be deleted to restore the tree to the
    expected state for repo.
  """
  restore_projects = []
  if (platform.system() == 'Darwin' and
      source_version < version_to_value('4.3.1', True)):
    # The build environment prior to 4.3.1 relied upon the clang toolchain
    # distributed with Xcode.  Clang can't be used to build external/elfutils
    # without modification since elfutils uses nested functions, furthermore
    # macports GCC crashes when attempting to link the host tools.  Therefore,
    # the following synchronizes the prebuilt GCC toolchain from 4.4.4, stores
    # it in a temporary directory and restores it after synchronizing the
    # target source tree.
    repo_init(manifest_url, 'android-4.4.4_r2', verbose=verbose)
    reset_git_projects_to_head(verbose=verbose)
    toolchain_projects = [p for p in extract_project_paths_from_repo_manifest()
                          if REPO_PROJECTS_DARWIN_HOST_GCC_RE.match(p)]
    repo_sync(toolchain_projects, verbose=verbose)
    # Rename the projects so repo doesn't clean them.
    for project in toolchain_projects:
      project_rename = (project, project + '-temp')
      restore_projects.append(project_rename)
      os.rename(project_rename[0], project_rename[1])

  repo_init(manifest_url, source_tag, verbose=verbose)
  reset_git_projects_to_head(verbose=verbose)
  repo_sync([p for p in extract_project_paths_from_repo_manifest()
             if REPO_PROJECTS_RE.match(p)], verbose=verbose)

  # Restore the saved projects.
  for project, project_temp in restore_projects:
    os.rename(project_temp, project)

  return [p[0] for p in restore_projects]


def main():
  """Checkout the Android tree and build perf along with the perfhost tool.

  For the most recently released branch of each API level do the following:
  * Get the minimal set of projects required to build perf.
  * Clean the tree.
  * Patch files required to perform a minimal build of perf.
  * Build perf and perfhost.
  * Archive build artifacts.

  Returns:
    0 if successful, non-zero otherwise.
  """
  # Parse command line arguments.
  parser = argparse.ArgumentParser()
  parser.add_argument('-s', '--source_dir',
                      help='Directory used to checkout the Android source.',
                      dest='source_dir',
                      default=os.path.join(os.getcwd(), 'tmp'))
  parser.add_argument('-o', '--output_dir',
                      help=('Directory where built perf binaries will be '
                            'stored.'), dest='output_dir',
                      default=os.path.join(os.getcwd(), 'bin'))
  parser.add_argument('-a', '--api_levels',
                      help=('List of API levels to build.  If this is not '
                            'specified all API levels are built.'),
                      default=[], dest='api_levels', nargs='+')
  parser.add_argument('-v', '--verbose',
                      help='Display verbose output during the build process.',
                      dest='verbose', default=False, action='store_true')
  args = parser.parse_args()
  source_directory = os.path.abspath(args.source_dir)
  output_directory = os.path.abspath(args.output_dir)
  verbose = args.verbose
  api_levels = [int(api) for api in args.api_levels if api.isdigit()]

  # Retrieve the set of source tags for each API level.
  api_level_to_source_tag = get_released_branches()

  # Create the source directory and change the working directory to it.
  if not os.path.exists(source_directory):
    os.makedirs(source_directory)
  os.chdir(source_directory)

  # Build perf and perfhost for each API level.
  trees_to_build = sorted(api_level_to_source_tag.iteritems(),
                          key=lambda s: s[1][1], reverse=True)
  # Filter trees without the Linux perf project.
  android_perf_first_version = version_to_value('4.1.x', True)
  trees_to_build = [t for t in trees_to_build
                    if t[1][1] >= android_perf_first_version]
  if verbose:
    print 'Building Linux perf for:'
    for tree in trees_to_build:
      print '  API level: %d, Branch: %s' % (tree[0], tree[1][0])

  for api_level, source_tag_version in trees_to_build:
    source_tag = source_tag_version[0]
    source_version = source_tag_version[1]

    if api_levels:
      if api_level not in api_levels:
        if verbose:
          print 'Skipping build of %s (API level %d)' % (source_tag, api_level)
        continue

    if verbose:
      print '=== Build %s (API level %d) ===' % (source_tag, api_level)

    # Retrieve the source, clean the tree.
    delete_projects = sync_projects(ANDROID_REPO_MANIFEST_URL, source_version,
                                    source_tag, verbose=verbose)

    # Patch main.mk to disable the Java version check since Java isn't
    # required to build the perf tools.
    patch_checks_in_makefile(BUILD_CORE_MAIN_MK, MAIN_MK_JAVA_VERSION_RE)

    # Apply patches required to build perf and perfhost.
    apply_patches(verbose=verbose)

    # Clean any build artifacts from a prior build.
    make_clean(verbose=verbose)

    # Build all AOSP build targets.
    for value, description in lunch_get_options(source_version):
      if [d for d in ('aosp_', 'full') if description.startswith(d)]:
        build_perf(value, source_version, verbose=verbose)

    archive_build_artifacts(output_directory, api_level, source_tag,
                            ANDROID_REPO_MANIFEST_URL)

    # Restore the state of the tree for repo.
    for p in delete_projects:
      shutil.rmtree(p)

  return 0


if __name__ == '__main__':
  sys.exit(main())
