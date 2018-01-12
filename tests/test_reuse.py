# -*- coding: utf-8 -*-
#
# Copyright (C) 2017-2018  Free Software Foundation Europe e.V.
#
# This file is part of reuse, available from its original location:
# <https://git.fsfe.org/reuse/reuse/>.
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
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for reuse."""

import os
import shutil
from itertools import zip_longest
from pathlib import Path
from textwrap import dedent

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
    """Given a file without reuse information, return an empty ReuseInfo
    object.
    """
    result = reuse.extract_reuse_info('')
    assert _reuse_info_equal(result, reuse.ReuseInfo([], []))


def test_extract_expression():
    """Parse various expressions."""
    expressions = [
        'GPL-3.0+',
        'GPL-3.0 AND CC0-1.0',
        'nonsense',
    ]
    for expression in expressions:
        result = reuse.extract_reuse_info(
            'SPDX-License-'
            'Identifier: {}'.format(expression))
        assert result.spdx_expressions == {expression}


def test_project_not_a_directory(empty_directory):
    """Cannot create a Project without a valid directory."""
    (empty_directory / 'foo.py').touch()
    with pytest.raises(NotADirectoryError):
        reuse.Project(empty_directory / 'foo.py')


def test_reuse_info_of_file_does_not_exist(fake_repository):
    """Raise FileNotFoundError when asking for the reuse info of a file that
    does not exist.
    """
    project = reuse.Project(fake_repository)
    with pytest.raises(FileNotFoundError):
        project.reuse_info_of(fake_repository / 'does_not_exist')


def test_reuse_info_of_directory(empty_directory):
    """Raise IsADirectoryError when calling reuse_info_of on a directory."""
    (empty_directory / 'src').mkdir()

    project = reuse.Project(empty_directory)
    with pytest.raises(IsADirectoryError):
        project.reuse_info_of(empty_directory / 'src')


def test_reuse_info_of_unlicensed_file(fake_repository):
    """Return an empty ReuseInfo object when asking for the reuse information
    of a file that has no reuse information.
    """
    (fake_repository / 'foo.py').touch()
    project = reuse.Project(fake_repository)
    assert not any(project.reuse_info_of('foo.py'))


def test_reuse_info_of_only_copyright(fake_repository):
    """A file contains only a copyright line.  Test whether it correctly picks
    up on that.
    """
    (fake_repository / 'foo.py').write_text('Copyright (C) 2017  Mary Sue')
    project = reuse.Project(fake_repository)
    reuse_info = project.reuse_info_of('foo.py')
    assert not any(reuse_info.spdx_expressions)
    assert len(reuse_info.copyright_lines) == 1
    assert reuse_info.copyright_lines.pop() == 'Copyright (C) 2017  Mary Sue'


def test_reuse_info_of_only_copyright_also_covered_by_debian(fake_repository):
    """A file contains only a copyright line, but debian/copyright also has
    information on this file.  Use both.
    """
    (fake_repository / 'doc/foo.py').write_text('Copyright in file')
    project = reuse.Project(fake_repository)
    reuse_info = project.reuse_info_of('doc/foo.py')
    assert any(reuse_info.spdx_expressions)
    assert len(reuse_info.copyright_lines) == 2
    assert 'Copyright in file' in reuse_info.copyright_lines
    assert '2017 Mary Sue' in reuse_info.copyright_lines


def test_reuse_info_of_also_covered_by_debian(fake_repository):
    """A file contains all reuse information, but debian/copyright also
    provides information on this file.  Use both.
    """
    (fake_repository / 'doc/foo.py').write_text(
        dedent("""
            SPDX-License-Identifier: GPL-3.0
            Copyright in file"""))
    project = reuse.Project(fake_repository)
    reuse_info = project.reuse_info_of('doc/foo.py')
    for thing in reuse_info:
        assert len(thing) == 2
    assert 'GPL-3.0' in reuse_info.spdx_expressions
    assert 'CC0-1.0' in reuse_info.spdx_expressions
    assert 'Copyright in file' in reuse_info.copyright_lines
    assert '2017 Mary Sue' in reuse_info.copyright_lines


def test_reuse_info_of_no_duplicates(empty_directory):
    """A file contains the same lines twice.  The ReuseInfo only contains those
    lines once.
    """
    spdx_line = 'SPDX-License-Identifier: GPL-3.0+\n'
    copyright_line = 'Copyright (C) 2017  Free Software Foundation Europe\n'
    text = spdx_line + copyright_line

    (empty_directory / 'foo.py').write_text(text * 2)
    project = reuse.Project(empty_directory)
    reuse_info = project.reuse_info_of('foo.py')
    for thing in reuse_info:
        assert len(thing) == 1
    assert 'GPL-3.0+' in reuse_info.spdx_expressions
    assert copyright_line.strip() in reuse_info.copyright_lines


def test_error_in_debian_copyright(fake_repository):
    """If there is an error in debian/copyright, just ignore its existence."""
    (fake_repository / 'debian/copyright').write_text('invalid')
    project = reuse.Project(fake_repository)
    assert not any(project.reuse_info_of('doc/index.rst'))


def test_all_files(empty_directory):
    """Given a directory with some files, yield all files."""
    (empty_directory / 'foo').touch()
    (empty_directory / 'bar').touch()

    project = reuse.Project(empty_directory)
    assert {file_.name for file_ in project.all_files()} == {'foo', 'bar'}


def test_all_files_on_single_file(empty_directory):
    """When a file is given as parameter instead of a directory, just yield the
    file.
    """
    (empty_directory / 'foo').touch()

    project = reuse.Project(empty_directory)
    result = list(project.all_files(empty_directory / 'foo'))

    assert len(result) == 1
    assert result[0].name == 'foo'


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
    Project.lint yields nothing.
    """
    project = reuse.Project(fake_repository)

    assert not list(project.lint())


def test_all_licensed_from_different_pwd(fake_repository):
    """Same as the other test, but try a different PWD."""
    os.chdir('/')
    project = reuse.Project(fake_repository)

    assert not list(project.lint())


def test_empty_directory_is_licensed(empty_directory):
    """An empty directory is licensed."""
    project = reuse.Project(empty_directory)

    assert not list(project.lint())


def test_all_licensed_no_debian_copyright(fake_repository):
    """The exact same as test_all_licensed, but now without
    debian/copyright.
    """
    shutil.rmtree(str(fake_repository / 'debian'))
    os.remove(str(fake_repository / 'doc/index.rst'))

    project = reuse.Project(fake_repository)

    assert not list(project.lint())


def test_one_unlicensed(fake_repository):
    """Given a repository where one file is not licensed, check if
    Project.unlicensed yields that file.
    """
    (fake_repository / 'foo.py').touch()

    project = reuse.Project(fake_repository)

    assert list(project.lint()) == [fake_repository / 'foo.py']


def test_all_licensed_but_unknown_license(fake_repository):
    """If a file points to a license that does not exist, it is unlicensed."""
    (fake_repository / 'foo.py').write_text(
        'SPDX-License-Identifier: LicenseRef-foo')

    project = reuse.Project(fake_repository)

    assert list(project.lint()) == [fake_repository / 'foo.py']


def test_all_licensed_but_error_in_spdx_expression(fake_repository):
    """If a file contains an SPDX expression that cannot be parsed, it is
    unlicensed.
    """
    (fake_repository / 'foo.py').write_text(
        'SPDX-License-Identifier: this is an invalid expression')

    project = reuse.Project(fake_repository)

    assert list(project.lint()) == [fake_repository / 'foo.py']


def test_lint_only_copyright(empty_directory):
    """If a file has only copyright information associated with it, it is
    unlicensed.
    """
    (empty_directory / 'foo.py').write_text(
        'Copyright (C) 2017  Mary Sue')

    project = reuse.Project(empty_directory)

    assert project.lint_file(empty_directory / 'foo.py')
    assert not project.lint_file(
        empty_directory / 'foo.py',
        spdx_mandatory=False)


def test_lint_only_spdx(empty_directory):
    """If a file has only SPDX information associated with it, it is
    unlicensed.
    """
    (empty_directory / 'foo.py').write_text(
        'SPDX-License-Identifier: MIT')
    (empty_directory / 'COPYING').write_text(
        'Valid-License-Identifier: MIT')

    project = reuse.Project(empty_directory)

    assert project.lint_file(empty_directory / 'foo.py')
    assert not project.lint_file(
        empty_directory / 'foo.py',
        copyright_mandatory=False)


def test_lint_not_a_file(fake_repository):
    """lint_file raises an OSError when called on a non-file."""
    project = reuse.Project(fake_repository)
    with pytest.raises(OSError):
        project.lint_file(fake_repository / 'src')


def test_lint_license_not_found(empty_directory):
    """If a license is used that doesn't appear in Project.licenses, lint
    complains.
    """
    (empty_directory / 'foo.py').write_text(
        'Copyright (C) 2017  Mary Sue\n'
        'SPDX-License-Identifier: MIT')
    project = reuse.Project(empty_directory)

    assert any(project.lint())


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


def test_licenses_no_file_extension(fake_repository):
    """Given a license file with no extension, correctly identify it."""
    (fake_repository / 'LICENSES/GPL-3.0.txt').rename(
        fake_repository / 'LICENSES/GPL-3.0')
    project = reuse.Project(fake_repository)

    assert set(project.licenses.keys()) == USED_LICENSES


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


def test_licenses_unknown(empty_directory):
    """If a license has no known license identifier, create one for it."""
    (empty_directory / 'COPYING').touch()
    (empty_directory / 'LICENSES').mkdir()
    (empty_directory / 'LICENSES/NOT-IN-SPDX-LIST.txt').touch()

    project = reuse.Project(empty_directory)
    assert set(project.licenses.keys()) == {
        'LicenseRef-Unknown0', 'LicenseRef-Unknown1'}


def test_licenses_conflict(empty_directory):
    """If two license files both resolve to the same identifier, raise a
    RuntimeError.
    """
    (empty_directory / 'COPYING').write_text(
        'Valid-License-Identifier: MIT')
    (empty_directory / 'LICENSE').write_text(
        'Valid-License-Identifier: MIT')

    project = reuse.Project(empty_directory)
    with pytest.raises(RuntimeError):
        assert project.licenses


@git
def test_unlicensed_but_ignored_by_git(git_repository):
    """Given a Git repository where some files are unlicensed---but ignored by
    git---check if Project.unlicensed yields nothing.
    """
    project = reuse.Project(git_repository)

    assert not list(project.lint())


def test_encoding():
    """Given a source code file, correctly detect its encoding and read it."""
    tests_directory = Path(__file__).parent.resolve()
    encoding_directory = tests_directory / 'resources/encoding'
    project = reuse.Project(encoding_directory)

    for path in encoding_directory.iterdir():
        reuse_info = project.reuse_info_of(path)
        assert reuse_info.copyright_lines.pop() == 'Copyright © 2017  Liberté'
