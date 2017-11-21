#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2017  Free Software Foundation Europe e.V.
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

"""Tests for reuse."""

import os
import shutil
from itertools import zip_longest
from pathlib import Path

import pytest

import reuse
from reuse import _util

# pylint: disable=invalid-name
git = pytest.mark.skipif(
    not _util.GIT_EXE,
    reason='requires git')


# Set of licenses used in tests.  This is a bit of duplication from conftest.
USED_LICENSES = set(['CC0-1.0', 'GPL-3.0', 'GPL-2.0', 'BSD-3-Clause'])


def _reuse_info_equal(first, second) -> bool:
    """Compare two ReuseInfo objects.

    This is necessary because (,) != [].
    """
    for left, right in zip_longest(first, second):
        if tuple(left) != tuple(right):
            return False
    return True


def test_extract_license_from_file(file_with_license_comments):
    """Test whether you can correctly extract reuse information from a code
    file's comments.
    """
    result = reuse.extract_reuse_info(
        file_with_license_comments.getvalue())
    assert _reuse_info_equal(result, file_with_license_comments.reuse_info)


def test_extract_no_license_info():
    """Given a file without reuse information, raise LicenseInfoNotFound."""
    result = reuse.extract_reuse_info('')
    assert _reuse_info_equal(result, reuse.ReuseInfo([], []))


def test_reuse_info_of_file_does_not_exist(fake_repository):
    """Raise a LicenseInfoNotFound error when asking for the reuse info of a
    file that does not exist.
    """
    project = reuse.Project(fake_repository)
    with pytest.raises(reuse.ReuseInfoNotFound):
        project.reuse_info_of('does_not_exist')


def test_reuse_info_of_only_copyright(fake_repository):
    """A file contains only a copyright line.  Test whether it correctly picks
    up on that.
    """
    (fake_repository / 'foo.py').write_text('Copyright (C) 2017  Mary Sue')
    project = reuse.Project(fake_repository)
    reuse_info = project.reuse_info_of('foo.py')
    assert not any(reuse_info.spdx_expressions)
    assert len(reuse_info.copyright_lines) == 1
    assert reuse_info.copyright_lines[0] == 'Copyright (C) 2017  Mary Sue'


def test_reuse_info_of_only_copyright_but_covered_by_debian(fake_repository):
    """A file contains only a copyright line, but debian/copyright also has
    information on this file.  Prioritise debian/copyright's output.
    """
    (fake_repository / 'src/foo.py').write_text('Copyright ignore-me')
    project = reuse.Project(fake_repository)
    reuse_info = project.reuse_info_of('src/foo.py')
    assert any(reuse_info.spdx_expressions)
    assert reuse_info.copyright_lines[0] != 'Copyright ignore-me'


def test_error_in_debian_copyright(fake_repository):
    """If there is an error in debian/copyright, just ignore its existence."""
    (fake_repository / 'debian/copyright').write_text('invalid')
    project = reuse.Project(fake_repository)
    with pytest.raises(reuse.ReuseInfoNotFound):
        project.reuse_info_of('src/no_license.py')


def test_license_file_detected(empty_file_with_license_file):
    """Test whether---when given a file and a license file---the license file
    is detected and read.
    """
    directory = empty_file_with_license_file[0]
    reuse_info = empty_file_with_license_file[1]

    project = reuse.Project(directory)

    all_files = list(project.all_files(directory))
    assert len(all_files) == 1

    result = project.reuse_info_of(all_files[0])
    assert _reuse_info_equal(result, reuse_info)


def test_all_licensed(fake_repository):
    """Given a repository where all files are licensed, check if
    Project.unlicensed yields nothing.
    """
    project = reuse.Project(fake_repository)

    assert not list(project.unlicensed())


def test_all_licensed_no_debian_copyright(fake_repository):
    """The exact same as test_all_licensed, but now without
    debian/copyright.
    """
    shutil.rmtree(str(fake_repository / 'debian'))
    os.remove(str(fake_repository / 'src/no_license.py'))

    project = reuse.Project(fake_repository)

    assert not list(project.unlicensed())


def test_one_unlicensed(fake_repository):
    """Given a repository where one file is not licensed, check if
    Project.unlicensed yields that file.
    """
    (fake_repository / 'foo.py').touch()

    project = reuse.Project(fake_repository)

    assert list(project.unlicensed()) == [fake_repository / 'foo.py']


def test_licenses_from_filenames(fake_repository):
    """Given a repository, extract the license identifiers from the
    filenames.
    """
    project = reuse.Project(fake_repository)

    assert set(project.licenses.keys()) == USED_LICENSES
    assert set(
        map(str, project.licenses.values())) == \
        set(['LICENSES/{}.txt'.format(spdx) for spdx in USED_LICENSES])


def test_licenses_licenseref_from_filename(empty_directory):
    """Extract SPDX identifier from filename if it begins with 'LicenseRef-'"""
    (empty_directory / 'LICENSES').mkdir()
    (empty_directory / 'LICENSES/LicenseRef-hello.txt').touch()

    project = reuse.Project(empty_directory)

    assert set(project.licenses.keys()) == {'LicenseRef-hello'}


@pytest.mark.parametrize(
    'license_file',
    ['COPYING', 'COPYING.md', 'LICENSE', 'LICENCE', 'COPYRIGHT',
     'LICENSES/MIT.txt', 'LICENSES/subdir/MIT.txt'])
def test_license_from_tag(empty_directory, license_file):
    """Extract license identifiers from the license file itself."""
    (empty_directory / license_file).parent.mkdir(parents=True, exist_ok=True)
    (empty_directory / license_file).write_text(
        'Valid-License-Identifier: MIT')

    project = reuse.Project(empty_directory)
    assert list(project.licenses.keys()) == ['MIT']
    assert list(project.licenses.values()) == [Path(license_file)]


def test_licenses_priority(empty_directory):
    """.license files are prioritised over the files themselves."""
    (empty_directory / 'COPYING').write_text('Valid-License-Identifier: MIT')
    (empty_directory / 'COPYING.license').write_text(
        'Valid-License-Identifier: GPL-3.0')

    project = reuse.Project(empty_directory)
    assert list(project.licenses.keys()) == ['GPL-3.0']


def test_licenses_from_different_pwd(empty_directory):
    """If the PWD is different, still provide correct licenses."""
    os.chdir('/')
    (empty_directory / 'COPYING').write_text('Valid-License-Identifier: MIT')

    project = reuse.Project(empty_directory)
    assert list(project.licenses.keys()) == ['MIT']


def test_licenses_multiple_in_file(empty_directory):
    """If there are multiple licenses in a file, return them all."""
    (empty_directory / 'COPYING').write_text(
        'Valid-License-Identifier: GPL-3.0\n'
        'Valid-License-Identifier: GPL-3.0+')

    project = reuse.Project(empty_directory)
    assert set(project.licenses.keys()) == {'GPL-3.0', 'GPL-3.0+'}


@git
def test_unlicensed_but_ignored_by_git(git_repository):
    """Given a Git repository where some files are unlicensed---but ignored by
    git---check if Project.unlicensed yields nothing.
    """
    project = reuse.Project(git_repository)

    assert not list(project.unlicensed())


def test_encoding():
    """Given a source code file, correctly detect its encoding and read it."""
    tests_directory = Path(__file__).parent.resolve()
    encoding_directory = tests_directory / 'resources/encoding'
    project = reuse.Project(encoding_directory)

    for path in encoding_directory.iterdir():
        reuse_info = project.reuse_info_of(path)
        assert reuse_info.copyright_lines[0] == 'Copyright © 2017  Liberté'
