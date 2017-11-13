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

from io import StringIO, TextIOWrapper
from itertools import zip_longest
from unittest import mock

import pytest

import reuse
from reuse import _util

# pylint: disable=invalid-name
git = pytest.mark.skipif(
    not _util.GIT_EXE,
    reason='requires git')


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


def test_extract_from_binary():
    """When giving a binary file to extract_license_info, raise
    LicenseInfoNotFound.
    """
    file_object = mock.Mock(spec=TextIOWrapper)
    # No idea how the UnicodeDecodeError arguments work: Just leave it as is.
    file_object.read.side_effect = UnicodeDecodeError('utf-8', b'', 0, 0, '')

    with pytest.raises(reuse.LicenseInfoNotFound):
        reuse.extract_license_info(file_object)


def test_extract_no_license_info():
    """Given a file without license information, raise LicenseInfoNotFound."""
    with pytest.raises(reuse.LicenseInfoNotFound):
        reuse.extract_license_info(StringIO())


def test_license_file_detected(empty_file_with_license_file):
    """Test whether---when given a file and a license file---the license file
    is detected and read.
    """
    directory = empty_file_with_license_file[0]
    license_info = empty_file_with_license_file[1]

    project = reuse.Project(directory)

    all_files = list(project.all_files(directory))
    assert len(all_files) == 1

    result = project.license_info_of(all_files[0])
    assert _license_info_equal(result, license_info)


def test_all_licensed(fake_repository):
    """Given a repository where all files are licensed, check if
    Project.unlicensed yields nothing.
    """
    project = reuse.Project(fake_repository)

    assert not list(project.unlicensed())


def test_one_unlicensed(fake_repository):
    """Given a repository where one file is not licensed, check if
    Project.unlicensed yields that file.
    """
    (fake_repository / 'foo.py').touch()

    project = reuse.Project(fake_repository)

    assert list(project.unlicensed()) == [fake_repository / 'foo.py']


@git
def test_unlicensed_but_ignored_by_git(git_repository):
    """Given a Git repository where some files are unlicensed---but ignored by
    git---check if Project.unlicensed yields nothing.
    """
    project = reuse.Project(git_repository)

    assert not list(project.unlicensed())
