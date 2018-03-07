# -*- coding: utf-8 -*-
#
# Copyright (C) 2017  Free Software Foundation Europe e.V.
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

"""Tests for the CLI for reuse."""

from io import StringIO
from itertools import zip_longest
from textwrap import dedent

import pytest
from reuse import __version__, _main, _util

# pylint: disable=invalid-name
git = pytest.mark.skipif(
    not _util.GIT_EXE,
    reason='requires git')


def test_lint_none(fake_repository):
    """Given a repository in which every file is licensed, return an exit code
    of 0 and print nothing.
    """
    out = StringIO()
    result = _main.main(['lint', str(fake_repository)], out)

    assert result == 0
    assert not out.getvalue()


@git
def test_lint_gitignore(git_repository):
    """Given a repository with files ignored by Git, skip over those files."""
    out = StringIO()
    result = _main.main(['lint', str(git_repository)], out)

    assert result == 0
    assert not out.getvalue()


def test_lint_ignore_debian(fake_repository):
    """When debian/copyright is ignored, non-compliant files are found."""
    out = StringIO()
    result = _main.main(['--ignore-debian', 'lint', str(fake_repository)], out)

    output_lines = out.getvalue().splitlines()
    assert len(output_lines) == 1
    assert 'index.rst' in output_lines[0]
    assert result


def test_lint_twice_path(fake_repository):
    """When providing the same path twice, only output those files once."""
    (fake_repository / 'foo.py').touch()
    (fake_repository / 'bar.py').touch()
    out = StringIO()
    result = _main.main(['lint'] + [str(fake_repository / 'foo.py')] * 2, out)

    output_lines = out.getvalue().splitlines()
    assert len(output_lines) == 1
    assert 'foo.py' in output_lines[0]
    assert result


@pytest.mark.xfail(reason='Order of files is not reliable')
def test_compile(tiny_repository):
    """A correct bill of materials is generated."""
    # result = runner.invoke(
    #     _main.cli,
    #     ['compile'])
    result = None

    expected = dedent("""\
        SPDXVersion: SPDX-2.1
        DataLicense: CC0-1.0
        SPDXID: SPDXRef-DOCUMENT
        DocumentName: {dirname}
        DocumentNamespace: http://spdx.org/spdxdocs/spdx-v2.1-04c223f0-4415-47fd-9860-7074a07f753e
        Creator: Person: Anonymous ()
        Creator: Organization: Anonymous ()
        Creator: Tool: reuse-{version}
        Created: 2017-11-08T11:07:30Z
        CreatorComment: <text>This document was created automatically using available reuse information consistent with the REUSE Initiative.</text>
        Relationship: SPDXRef-DOCUMENT describes SPDXRef-8008eeb8d2000e5aa6eaa51b1cdc944d726e1107
        Relationship: SPDXRef-DOCUMENT describes SPDXRef-bb5656f1b5e8283a8e930c54afd9a8bfebe7a548

        FileName: ./src/code.py
        SPDXID: SPDXRef-8008eeb8d2000e5aa6eaa51b1cdc944d726e1107
        FileChecksum: SHA1: fb17c6dd60b8b8c35128c8a14905e1ef328b1534
        LicenseConcluded: NOASSERTION
        LicenseInfoInFile: GPL-3.0+
        FileCopyrightText: <text>Copyright (C) 2017  Free Software Foundation Europe e.V.</text>

        FileName: ./src/no_license.py
        SPDXID: SPDXRef-bb5656f1b5e8283a8e930c54afd9a8bfebe7a548
        FileChecksum: SHA1: da39a3ee5e6b4b0d3255bfef95601890afd80709
        LicenseConcluded: NOASSERTION
        LicenseInfoInFile: CC0-1.0
        FileCopyrightText: <text>2017 Mary Sue</text>""".format(
            dirname=tiny_repository.name,
            version=__version__))

    for result_line, expected_line in zip_longest(
            result.output.splitlines(),
            expected.splitlines()):
        # Just ignore these
        if 'DocumentNamespace' in result_line:
            continue
        if 'Created' in result_line:
            continue

        assert result_line == expected_line
