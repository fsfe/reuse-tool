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

"""Core functionality of reuse."""

import logging
import os
from pathlib import Path
from typing import Iterator, Union

_logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class License:
    pass


def all_files(directory: Union[Path, str] = None) -> Iterator[Path]:
    """Yield all files in *directory* and its subdirectories.

    The files that are not yielded are:

    - Files ignored by VCS (e.g., see .gitignore)

    - Files ignored by reuse config file.
    """
    if directory is None:
        directory = Path.cwd()
    directory = Path(directory)

    for root, dirs, files in os.walk(directory):
        _logger.debug('currently walking in %s', root)

        # Don't walk VCS.
        vcs_dirs = {'.git', '.svn'}
        intersection = vcs_dirs.intersection(set(dirs))
        for ignored in intersection:
            _logger.debug('ignoring %s - VCS', ignored)
            dirs.remove(ignored)

        # TODO: Apply better filtering
        for file_ in files:
            _logger.debug('yielding %s', file_)
            yield file_

def license_of(path: Union[Path, str]) -> License:
    """Get the license information of *path*."""
    path = Path(path)
    license_path = Path('{}.license'.format(path))

    # TODO: Maybe get license information from central config file if it exists
    if license_path.exists():
        # TODO
        _logger.debug('detected %s', license_path)
    else:
        # TODO
        _logger.debug('searching %s for license information', path)
