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
from collections import namedtuple
from itertools import zip_longest
from pathlib import Path
from typing import IO, Iterator, List, Union

__author__ = 'Carmen Bianca Bakker'
__email__ = 'carmenbianca@fsfe.org'
__license__ = 'GPLv3+'
__version__ = '0.0.1'

_logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

LICENSE_PATTERN = re.compile(r'SPDX-License-Identifier: (.*?)\s')
LICENSE_FILENAME_PATTERN = re.compile(r'License-Filename: (.*?)\s')

LICENSE_FILE_PATTERNS = [
    re.compile(r'^LICEN[CS]E'),
    re.compile(r'^COPYING'),
]

LicenseInfo = namedtuple('LicenseInfo', ['name', 'filename'])


class ReuseException(Exception):
    """Base exception."""


class LicenseInfoNotFound(ReuseException):
    """Could not find license for file."""


def all_files(directory: Union[Path, str] = None) -> Iterator[Path]:
    """Yield all files in *directory* and its subdirectories.

    The files that are not yielded are:

    - Files ignored by VCS (e.g., see .gitignore)

    - Files ignored by reuse config file.

    - Files with the *.license suffix.
    """
    if directory is None:
        directory = Path.cwd()
    directory = Path(directory)

    for root, dirs, files in os.walk(directory):
        root = Path(root)
        _logger.debug('currently walking in %s', root)

        # Don't walk VCS.
        vcs_dirs = {'.git', '.svn'}
        intersection = vcs_dirs.intersection(set(dirs))
        for ignored in intersection:
            _logger.debug('ignoring %s - VCS', root / ignored)
            dirs.remove(ignored)

        # Don't walk LICENSES
        LICENSES_DIR = 'LICENSES'
        if LICENSES_DIR in dirs:
            _logger.debug('ignoring %s - LICENSES', root / LICENSES_DIR)
            dirs.remove(LICENSES_DIR)

        # Filter files.
        # TODO: Apply better filtering
        for file_ in files:
            # .license files
            if file_.endswith('.license'):
                continue

            # LICENSE/COPYING files
            try:
                for pattern in LICENSE_FILE_PATTERNS:
                    if pattern.match(file_):
                        _logger.debug('ignoring %s - license', root / file_)
                        # Have to continue the outer loop here, so throw an
                        # exception.  Not the cleanest solution.
                        raise ReuseException()
            except ReuseException:
                continue

            _logger.debug('yielding %s', file_)
            yield root / file_


def licenses_of(path: Union[Path, str]) -> List[LicenseInfo]:
    """Get the license information of *path*."""
    path = Path(path)
    license_path = Path('{}.license'.format(path))

    # TODO: Maybe get license information from central config file if it exists
    if not license_path.exists():
        license_path = path
    else:
        _logger.debug(
            'detected %s license file, searching that instead', license_path)

    _logger.debug('searching %s for license information', path)

    with license_path.open() as fp:
        return extract_licenses_from_file(fp)


def extract_licenses_from_file(file_object: IO) -> List[LicenseInfo]:
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
    license_matches = LICENSE_PATTERN.findall(text)
    license_filename_matches = LICENSE_FILENAME_PATTERN.findall(text)

    if any(not x for x in (license_matches, license_filename_matches)):
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
    return [
        LicenseInfo(x, y)
        for x, y in zip_longest(license_matches, license_filename_matches)]
