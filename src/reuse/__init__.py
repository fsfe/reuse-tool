#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of reuse.  It is copyrighted by the contributors recorded
# in the version control history of the file, available from its original
# location: https://git.fsfe.org/reuse/reuse
#
# reuse is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# reuse is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# reuse.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0+
# License-Filename: LICENSES/GPL-3.0.txt

"""reuse is a tool for compliance with the REUSE Project recommendations."""

# pylint: disable=ungrouped-imports

import datetime
import hashlib
import logging
import os
import re
import sys
from collections import namedtuple
from pathlib import Path
from typing import BinaryIO, Iterator, Optional, TextIO
from uuid import uuid4

from debian.copyright import Copyright

from ._util import GIT_EXE, PathLike, execute_command, in_git_repo

__author__ = 'Carmen Bianca Bakker'
__email__ = 'carmenbianca@fsfe.org'
__license__ = 'GPLv3+'
__version__ = '0.0.4'

_logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

_LICENSE_PATTERN = re.compile(r'SPDX-License-Identifier: (.*)')
_LICENSE_FILENAME_PATTERN = re.compile(r'License-Filename: (.*)')
_COPYRIGHT_PATTERN = re.compile(r'(Copyright .*)')

_IGNORE_DIR_PATTERNS = [
    re.compile(r'\.git'),
    re.compile(r'^\.svn$'),
    re.compile(r'^LICEN[CS]ES$'),
    re.compile(r'^debian$'),
]

_IGNORE_FILE_PATTERNS = [
    re.compile(r'^LICEN[CS]E'),
    re.compile(r'^COPYING'),
    re.compile(r'.*\.license$'),
    re.compile(r'.*\.spdx$'),
    re.compile(r'^\.gitignore$'),
]

LicenseInfo = namedtuple(
    'LicenseInfo',
    ['licenses', 'filenames', 'copyright_lines'])


class ReuseException(Exception):
    """Base exception."""


class LicenseInfoNotFound(ReuseException):
    """Could not find license for file."""


def _checksum(file_object: BinaryIO, hash_function) -> str:
    """Return checksum of *file_object*."""
    result = hash_function()
    for chunk in iter(
            lambda: file_object.read(128 * result.block_size), b''):
        result.update(chunk)
    return result.hexdigest()


def _copyright_from_debian(
        path: PathLike,
        copyright: Copyright) -> Optional[LicenseInfo]:
    """Find the license information of *path* in the Debian copyright object.
    """
    result = copyright.find_files_paragraph(str(path))

    if result is None:
        raise LicenseInfoNotFound()

    _logger.debug('%s covered by debian/copyright', path)

    return LicenseInfo(
        [result.license.synopsis],
        [],
        list(map(str.strip, result.copyright.splitlines())))


def extract_license_info(file_object: TextIO) -> LicenseInfo:
    """Extract license information from comments in a file."""
    # TODO: This feels wrong.  Somehow detect whether file contains text?  I
    # don't frankly know how this is normally handled.
    try:
        text = file_object.read()
    except UnicodeDecodeError as error:
        _logger.warning('%s could not be decoded as Unicode', file_object.name)
        raise LicenseInfoNotFound('could not decode') from error

    # TODO: Make this more efficient than doing a regex over the entire file.
    # Though, on a sidenote, it's pretty damn fast.
    license_matches = _LICENSE_PATTERN.findall(text)
    license_filename_matches = _LICENSE_FILENAME_PATTERN.findall(text)
    copyright_matches = _COPYRIGHT_PATTERN.findall(text)

    if not any(license_matches):
        _logger.debug(
            '%s does not contain license information', file_object)
        raise LicenseInfoNotFound('no license information found')
    if len(license_matches) != len(license_filename_matches):
        # TODO: Figure out if this is something that needs to be handled.  At
        # first sight yes, but what if the two licenses are GPL-3.0 and
        # GPL-3.0+ and they both point to the same file?
        pass

    return LicenseInfo(
        license_matches,
        license_filename_matches,
        copyright_matches)


class Project:
    """Holds a project's root, more or less.  This is very convenient, because
    a lot of interactions require knowing where you are in relation to the
    project root.
    """

    def __init__(self, root: PathLike):
        self._root = Path(root)
        if not self._root.is_dir():
            raise ReuseException('%s is no valid path' % self._root)

        self._is_git_repo = None
        # Use '0' as None, because None is a valid value...
        self._copyright_val = 0
        self._detected_license_files = set()

    def all_files(self, directory: PathLike = None) -> Iterator[Path]:
        """Yield all files in *directory* and its subdirectories.

        The files that are not yielded are:

        - Files ignored by VCS (e.g., see .gitignore)

        - Files/directories matching IGNORE_*_PATTERNS.
        """
        if directory is None:
            directory = self._root
        directory = Path(directory)

        for root, dirs, files in os.walk(str(directory)):
            root = Path(root)
            _logger.debug('currently walking in %s', root)

            # Don't walk ignored directories
            for dir_ in list(dirs):
                for pattern in _IGNORE_DIR_PATTERNS:
                    if pattern.match(dir_):
                        _logger.debug('ignoring %s - reuse', root / dir_)
                        dirs.remove(dir_)
                if self._ignored_by_vcs(root / dir_):
                    _logger.debug(
                        'ignoring %s - ignored by vcs', root / dir_)
                    dirs.remove(dir_)

            # Filter files.
            for file_ in files:
                # General ignored files
                try:
                    for pattern in _IGNORE_FILE_PATTERNS:
                        if pattern.match(file_):
                            _logger.debug('ignoring %s - reuse', root / file_)
                            # Have to continue the outer loop here, so throw an
                            # exception.  Not the cleanest solution.
                            raise ReuseException()
                except ReuseException:
                    continue

                if self._ignored_by_vcs(root / file_):
                    _logger.debug('ignoring %s - ignored by vcs', root / file_)
                    continue

                _logger.debug('yielding %s', file_)
                yield root / file_

    def license_info_of(
            self,
            path: PathLike,
            ignore_debian: bool = False) -> LicenseInfo:
        """Get the license information of *path*."""
        path = Path(path)
        license_path = Path('{}.license'.format(path))

        if license_path.exists():
            _logger.debug(
                'detected %s license file, searching that instead',
                license_path)
        else:
            license_path = path

        _logger.debug('searching %s for license information', path)

        with license_path.open() as fp:
            try:
                return extract_license_info(fp)
            except LicenseInfoNotFound:
                pass

        if ignore_debian or not self._copyright:
            raise LicenseInfoNotFound()

        try:
            return _copyright_from_debian(
                self._relative_from_root(path),
                self._copyright)
        except LicenseInfoNotFound:
            raise

    def unlicensed(
            self,
            path: PathLike = None,
            ignore_debian: bool = False) -> Iterator[Path]:
        """Yield all unlicensed files under *path*.

        If *path* is not specified, it becomes root.
        """
        if path is None:
            path = self._root
        for file_ in self.all_files(path):
            try:
                self.license_info_of(file_, ignore_debian=ignore_debian)
            except LicenseInfoNotFound:
                yield file_

    def bill_of_materials(self, out=sys.stdout) -> None:
        """Generate a bill of materials from the project.  The bill of
        materials is written to *out*.

        See https://spdx.org/specifications.
        """
        # Write mandatory tags
        out.write('SPDXVersion: SPDX-2.1\n')
        out.write('DataLicense: CC0-1.0\n')
        out.write('SPDXID: SPDXRef-DOCUMENT\n')

        out.write('DocumentName: {}\n'.format(self._root.resolve().name))
        # TODO: Generate UUID from git revision maybe
        # TODO: Fix the URL
        out.write(
            'DocumentNamespace: '
            'http://spdx.org/spdxdocs/spdx-v2.1-{}\n'.format(uuid4()))

        # Author
        # TODO: Fix Person and Organization
        out.write('Creator: Person: Anonymous ()\n')
        out.write('Creator: Organization: Anonymous ()\n')
        out.write('Creator: Tool: reuse-{}\n'.format(__version__))

        now = datetime.datetime.utcnow()
        now = now.replace(microsecond=0)
        out.write('Created: {}Z\n'.format(now.isoformat()))
        out.write(
            'CreatorComment: <text>This document was created automatically '
            'using available license information consistent with the '
            'REUSE project.</text>\n')

        all_files = list(self.all_files())

        # List all DESCRIBES relationships.  This involves some code
        # duplication in determining the relative path to the file and its
        # hash.
        for file_ in all_files:
            relative = self._relative_from_root(file_)
            ref = hashlib.sha1(str(relative).encode('utf-8')).hexdigest()
            out.write(
                'Relationship: SPDXRef-DOCUMENT describes '
                'SPDXRef-{}\n'.format(ref))

        # File information
        for file_ in all_files:
            out.write('\n')
            self._file_information(file_, out)

        # Licenses
        for file_ in self._detected_license_files:
            if not Path(file_).exists():
                _logger.warning('could not find %s', file_)
                continue
            out.write('\n')
            out.write(
                'LicenseID: LicenseRef-{}\n'.format(
                    hashlib.sha1(str(file_).encode('utf-8')).hexdigest()))
            # TODO: Maybe do an assertion here
            out.write('LicenseName: NOASSERTION\n')

            with (self._root / file_).open() as fp:
                out.write('ExtractedText: <text>{}</text>\n'.format(fp.read()))

    @property
    def is_git_repo(self) -> bool:
        """Is the project a git repository?  Cache the result."""
        if self._is_git_repo is None:
            self._is_git_repo = in_git_repo(self._root)
        return self._is_git_repo

    @property
    def _copyright(self) -> Optional[Copyright]:
        if self._copyright_val == 0:
            copyright_path = self._root / 'debian' / 'copyright'
            if copyright_path.exists():
                with copyright_path.open() as fp:
                    self._copyright_val = Copyright(fp)
            else:
                self._copyright_val = None
        return self._copyright_val

    def _ignored_by_git(self, path: PathLike) -> bool:
        """Is *path* covered by the ignore mechanism of git?

        Always return False if git is not installed.
        """
        path = self._relative_from_root(path)
        if GIT_EXE is None:
            return False

        command = [GIT_EXE, 'check-ignore', str(path)]
        result = execute_command(command, _logger, cwd=str(self._root))

        return not result.returncode

    def _ignored_by_vcs(self, path: PathLike) -> bool:
        """Is *path* covered by the ignore mechanism of the VCS (e.g.,
        .gitignore)?
        """
        if self.is_git_repo:
            return self._ignored_by_git(path)
        return False

    def _relative_from_root(self, path: PathLike) -> Path:
        """If the project root is /tmp/project, and *path* is
        /tmp/project/src/file, then return src/file.
        """
        path = Path(path).resolve()
        common = os.path.commonpath([str(path), str(self._root.resolve())])
        return Path(str(path).replace(common + '/', ''))

    def _file_information(self, path: PathLike, out=sys.stdout) -> None:
        """Create SPDX File Information for *path*."""
        relative = self._relative_from_root(path)
        encoded = str(relative).encode('utf-8')
        out.write('FileName: ./{}\n'.format(relative))
        out.write('SPDXID: SPDXRef-{}\n'.format(
            hashlib.sha1(encoded).hexdigest()))

        with path.open('rb') as fp:
            out.write(
                'FileChecksum: SHA1: {}\n'.format(
                    _checksum(fp, hashlib.sha1)))

        # IMPORTANT: Make no assertion about concluded license.  This tool
        # cannot, with full certainty, determine the license of a file.
        out.write('LicenseConcluded: NOASSERTION\n')

        try:
            license_info = self.license_info_of(path)
        except LicenseInfoNotFound:
            license_info = LicenseInfo([], [], [])

        for spdx in license_info.licenses:
            out.write('LicenseInfoInFile: {}\n'.format(spdx))

        for filename in license_info.filenames:
            out.write(
                'LicenseInfoInFile: LicenseRef-{}\n'.format(
                    hashlib.sha1(filename.encode('utf-8')).hexdigest()))
            self._detected_license_files.add(filename)

        if license_info.copyright_lines:
            for line in license_info.copyright_lines:
                out.write('FileCopyrightText: <text>{}</text>\n'.format(line))
        else:
            out.write('FileCopyrightText: NONE\n')
