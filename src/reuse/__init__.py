#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of reuse.  It is copyrighted by the contributors recorded
# in the version control history of the file, available from its original
# location: https://git.fsfe.org/carmenbianca/reuse
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

"""reuse is a tool for REUSE compliance."""

import logging
import os
import re
import subprocess
from collections import namedtuple
from pathlib import Path
from typing import IO, Iterator, Optional, Union

from debian.copyright import Copyright

from ._util import GIT_EXE, in_git_repo

__author__ = 'Carmen Bianca Bakker'
__email__ = 'carmenbianca@fsfe.org'
__license__ = 'GPLv3+'
__version__ = '0.0.1'

_logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

_LICENSE_PATTERN = re.compile(r'SPDX-License-Identifier: (.*)')
_LICENSE_FILENAME_PATTERN = re.compile(r'License-Filename: (.*)')

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
    re.compile(r'^\.gitignore$'),
]

LicenseInfo = namedtuple('LicenseInfo', ['licenses', 'filenames'])

_PathLike = Union[Path, str]


class ReuseException(Exception):
    """Base exception."""


class LicenseInfoNotFound(ReuseException):
    """Could not find license for file."""


def _copyright_from_debian(
        path: _PathLike,
        copyright: Copyright) -> Optional[LicenseInfo]:
    """Find the license information of *path* in the Debian copyright object.
    """
    result = copyright.find_files_paragraph(str(path))

    if result is None:
        raise LicenseInfoNotFound()

    _logger.debug('%s covered by debian/copyright', path)

    return LicenseInfo([result.license.synopsis], [])


def extract_license_info(file_object: IO) -> LicenseInfo:
    """Extract license information from comments in a file."""
    # TODO: This feels wrong.  Somehow detect whether file contains text?  I
    # don't frankly know how this is normally handled.
    try:
        text = file_object.read()
    except UnicodeDecodeError as error:
        _logger.warning('%s is a binary file', file_object.name)
        raise LicenseInfoNotFound('binary file') from error

    # TODO: Make this more efficient than doing a regex over the entire file.
    # Though, on a sidenote, it's pretty damn fast.
    license_matches = _LICENSE_PATTERN.findall(text)
    license_filename_matches = _LICENSE_FILENAME_PATTERN.findall(text)

    if not any(license_matches):
        _logger.debug(
            '%s does not contain license information', file_object.name)
        raise LicenseInfoNotFound('no license information found')
    if len(license_matches) != len(license_filename_matches):
        # TODO: Figure out if this is something that needs to be handled.  At
        # first sight yes, but what if the two licenses are GPL-3.0 and
        # GPL-3.0+ and they both point to the same file?
        pass

    # TODO: This results in `None` being added to the list if the two lists are
    # not of equal size.  This is obviously unclear behaviour.
    return LicenseInfo(license_matches, license_filename_matches)


class Project:

    def __init__(self, root: _PathLike):
        self._root = Path(root)
        if not self._root.is_dir():
            raise ReuseException('%s is no valid path' % self._root)

        self._is_git_repo = None
        # Use '0' as None, because None is a valid value...
        self._copyright_val = 0


    def all_files(self, directory: _PathLike = None) -> Iterator[Path]:
        """Yield all files in *directory* and its subdirectories.

        The files that are not yielded are:

        - Files ignored by VCS (e.g., see .gitignore)

        - Files ignored by reuse config file.

        - Files with the *.license suffix.
        """
        if directory is None:
            directory = self._root
        directory = Path(directory)

        for root, dirs, files in os.walk(directory):
            root = Path(root)
            _logger.debug('currently walking in %s', root)

            # Don't walk ignored directories
            for directory in list(dirs):
                for pattern in _IGNORE_DIR_PATTERNS:
                    if pattern.match(directory):
                        _logger.debug('ignoring %s - reuse', root / directory)
                        dirs.remove(directory)
                if self._ignored_by_vcs(root / directory):
                    _logger.debug(
                        'ignoring %s - ignored by vcs', root / directory)
                    dirs.remove(directory)

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

    def license_info_of(self, path: _PathLike) -> LicenseInfo:
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

        try:
            return _copyright_from_debian(
                self._relative_from_root(path),
                self._copyright)
        except LicenseInfoNotFound as e:
            raise

    def unlicensed(self, path: _PathLike) -> Iterator[Path]:
        """Yield all unlicensed files under path."""
        for file_ in self.all_files(path):
            try:
                self.license_info_of(file_)
            except LicenseInfoNotFound:
                yield file_

    @property
    def is_git_repo(self):
        if self._is_git_repo is None:
            self._is_git_repo = in_git_repo(self._root)
        return self._is_git_repo

    @property
    def _copyright(self):
        if self._copyright_val == 0:
            copyright_path = self._root / 'debian' / 'copyright'
            if copyright_path.exists():
                with copyright_path.open() as fp:
                    self._copyright_val = Copyright(fp)
            else:
                self._copyright_val = None
        return self._copyright_val

    def _ignored_by_git(self, path: _PathLike) -> bool:
        """Is *path* covered by the ignore mechanism of git?

        Always return False if git is not installed.
        """
        path = self._relative_from_root(path)
        if GIT_EXE is None:
            return False

        command = [GIT_EXE, 'check-ignore', str(path)]
        _logger.debug('running %s', ' '.join(command))

        result = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=self._root)
        return not result.returncode

    def _ignored_by_vcs(self, path: _PathLike) -> bool:
        """Is *path* covered by the ignore mechanism of the VCS (e.g.,
        .gitignore)?
        """
        if self.is_git_repo:
            return self._ignored_by_git(path)
        return False

    def _relative_from_root(self, path: _PathLike) -> Path:
        """If the project root is /tmp/project, and *path* is
        /tmp/project/src/file, then return src/file.
        """
        path = Path(path).resolve()
        common = os.path.commonpath([path, self._root.resolve()]) + '/'
        return str(path).replace(common, '')
