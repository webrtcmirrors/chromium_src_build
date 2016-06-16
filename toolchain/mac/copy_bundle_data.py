# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import os
import shutil
import sys


def DetectEncoding(data, default_encoding='UTF-8'):
  """Detects the encoding used by |data| from the Byte-Order-Mark if present.

  Args:
    data: string whose encoding needs to be detected
    default_encoding: encoding returned if no BOM is found.

  Returns:
    The encoding determined from the BOM if present or |default_encoding| if
    no BOM was found.
  """
  if data.startswith('\xFE\xFF'):
    return 'UTF-16BE'

  if data.startswith('\xFF\xFE'):
    return 'UTF-16LE'

  if data.startswith('\xEF\xBB\xBF'):
    return 'UTF-8'

  return default_encoding


def CopyStringsFile(source, dest, strings_format):
  """Copies a .strings file from |source| to |dest| and convert it to UTF-16.

  Args:
    source: string, path to the source file
    dest: string, path to the destination file
  """
  with open(source, 'rb') as source_file:
    data = source_file.read()

  # Xcode's CpyCopyStringsFile / builtin-copyStrings seems to call
  # CFPropertyListCreateFromXMLData() behind the scenes; at least it prints
  #     CFPropertyListCreateFromXMLData(): Old-style plist parser: missing
  #     semicolon in dictionary.
  # on invalid files. Do the same kind of validation.
  import CoreFoundation as CF
  cfdata = CF.CFDataCreate(None, data, len(data))
  plist, error = CF.CFPropertyListCreateFromXMLData(None, cfdata, 0, None)
  if error:
    raise ValueError(error)

  if strings_format == 'legacy':
    encoding = DetectEncoding(data)
    with open(dest, 'wb') as dest_file:
      dest_file.write(data.decode(encoding).encode('UTF-16'))
  else:
    cfformat = {
      'xml1': CF.kCFPropertyListXMLFormat_v1_0,
      'binary1': CF.kCFPropertyListBinaryFormat_v1_0,
    }[strings_format]
    cfdata, error = CF.CFPropertyListCreateData(
        None, plist, CF.kCFPropertyListBinaryFormat_v1_0,
        0, None)
    if error:
      raise ValueError(error)

    data = CF.CFDataGetBytes(
        cfdata, CF.CFRangeMake(0, CF.CFDataGetLength(cfdata)), None)
    with open(dest, 'wb') as dest_file:
      dest_file.write(data)


def CopyFile(source, dest, strings_format):
  """Copies a file or directory from |source| to |dest|.

  Args:
    source: string, path to the source file
    dest: string, path to the destination file
  """
  if os.path.isdir(source):
    if os.path.exists(dest):
      shutil.rmtree(dest)
    # Copy tree.
    # TODO(thakis): This copies file attributes like mtime, while the
    # single-file branch below doesn't. This should probably be changed to
    # be consistent with the single-file branch.
    shutil.copytree(source, dest, symlinks=True)
    return

  if os.path.exists(dest):
    os.unlink(dest)

  _, extension = os.path.splitext(source)
  if extension == '.strings':
    CopyStringsFile(source, dest, strings_format)
    return

  shutil.copy(source, dest)


def Main():
  parser = argparse.ArgumentParser(
      description='copy source to destination for the creation of a bundle')
  parser.add_argument('--strings-format',
      choices=('xml1', 'binary1', 'legacy'), default='legacy',
      help='convert .strings file to format (default: %(default)s)')
  parser.add_argument('source', help='path to source file or directory')
  parser.add_argument('dest', help='path to destination')
  args = parser.parse_args()

  CopyFile(args.source, args.dest, args.strings_format)

if __name__ == '__main__':
  sys.exit(Main())
