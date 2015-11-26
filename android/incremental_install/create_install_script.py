#!/usr/bin/env python

# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Creates a script to run an "_incremental" .apk."""

import argparse
import os
import pprint
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, 'gyp'))

from pylib import constants
from util import build_utils


SCRIPT_TEMPLATE = """\
#!/usr/bin/env python
#
# This file was generated by:
#     //build/android/incremental_install/create_install_script.py

import os
import subprocess
import sys


def _ResolvePath(path):
  script_directory = os.path.dirname(__file__)
  return os.path.abspath(os.path.join(script_directory, path))


# Exported to allow test runner to be able to install incremental apks.
def GetInstallParameters():
  apk_path = {apk_path}
  lib_dir = {lib_dir}
  dex_files = {dex_files}
  splits = {splits}
  show_proguard_warning = {show_proguard_warning}

  return dict(apk_path=_ResolvePath(apk_path),
              dex_files=[_ResolvePath(p) for p in dex_files],
              lib_dir=_ResolvePath(lib_dir),
              show_proguard_warning=show_proguard_warning,
              splits=[_ResolvePath(p) for p in splits])


def main():
  output_directory = {output_directory}
  cmd_path = {cmd_path}
  params = GetInstallParameters()
  cmd_args = [
      _ResolvePath(cmd_path),
      '--output-directory', _ResolvePath(output_directory),
  ]
  if params['lib_dir']:
    cmd_args.extend(('--lib-dir', params['lib_dir']))
  for dex_path in params['dex_files']:
    cmd_args.extend(('--dex-file', dex_path))
  for split in params['splits']:
    cmd_args.extend(('--split', split))
  cmd_args.append(params['apk_path'])
  if params['show_proguard_warning']:
    cmd_args.append('--show-proguard-warning')
  return subprocess.call(cmd_args + sys.argv[1:])

if __name__ == '__main__':
  sys.exit(main())
"""


def _ParseArgs(args):
  args = build_utils.ExpandFileArgs(args)
  parser = argparse.ArgumentParser()
  build_utils.AddDepfileOption(parser)
  parser.add_argument('--script-output-path',
                      help='Output path for executable script.',
                      required=True)
  parser.add_argument('--output-directory',
                      help='Path to the root build directory.',
                      default='.')
  parser.add_argument('--apk-path',
                      help='Path to the .apk to install.',
                      required=True)
  parser.add_argument('--split',
                      action='append',
                      dest='splits',
                      default=[],
                      help='A glob matching the apk splits. '
                           'Can be specified multiple times.')
  parser.add_argument('--lib-dir',
                      help='Path to native libraries directory.')
  parser.add_argument('--dex-file',
                      action='append',
                      default=[],
                      dest='dex_files',
                      help='List of dex files to include.')
  parser.add_argument('--dex-file-list',
                      help='GYP-list of dex files.')
  parser.add_argument('--show-proguard-warning',
                      action='store_true',
                      default=False,
                      help='Print a warning about proguard being disabled')

  options = parser.parse_args(args)
  options.dex_files += build_utils.ParseGypList(options.dex_file_list)
  return options


def main(args):
  options = _ParseArgs(args)

  def relativize(path):
    script_dir = os.path.dirname(options.script_output_path)
    return path and os.path.relpath(path, script_dir)

  installer_path = os.path.join(constants.DIR_SOURCE_ROOT, 'build', 'android',
                                'incremental_install', 'installer.py')
  pformat = pprint.pformat
  template_args = {
      'cmd_path': pformat(relativize(installer_path)),
      'apk_path': pformat(relativize(options.apk_path)),
      'output_directory': pformat(relativize(options.output_directory)),
      'lib_dir': pformat(relativize(options.lib_dir)),
      'dex_files': pformat([relativize(p) for p in options.dex_files]),
      'show_proguard_warning': pformat(options.show_proguard_warning),
      'splits': pformat([relativize(p) for p in options.splits]),
  }

  with open(options.script_output_path, 'w') as script:
    script.write(SCRIPT_TEMPLATE.format(**template_args))

  os.chmod(options.script_output_path, 0750)

  if options.depfile:
    build_utils.WriteDepfile(
        options.depfile,
        build_utils.GetPythonDependencies())


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
