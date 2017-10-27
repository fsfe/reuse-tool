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

"""Tests for reuse."""

from itertools import zip_longest

import reuse


def _license_info_equal(first, second) -> bool:
    """Compare two LicenseInfo objects.

    This is necessary because (,) != [].
    """
    for left, right in zip_longest(first, second):
        if tuple(left) != tuple(right):
            return False
    return True

def test_extract_license_from_file(file_with_license_comments):
    """Test whether you can correctly extract license information from a code
    file's comments.
    """
    result = reuse.extract_license_info(
        file_with_license_comments)
    assert _license_info_equal(result, file_with_license_comments.license_info)


def test_license_file_detected(empty_file_with_license_file):
    """Test whether—when given a file and a license file—the license file is
    detected and read.
    """
    directory = empty_file_with_license_file[0]
    license_info = empty_file_with_license_file[1]

    project = reuse.Project(directory)

    all_files = list(project.all_files(directory))
    assert len(all_files) == 1

    result = project.license_info_of(all_files[0])
    assert _license_info_equal(result, license_info)
