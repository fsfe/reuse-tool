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

"""Tests for the CLI for reuse."""

import pytest

from reuse import _main, _util

# pylint: disable=invalid-name
git = pytest.mark.skipif(
    not _util.GIT_EXE,
    reason='requires git')


def test_lint_none(fake_repository, runner):
    """Given a repository in which every file is licensed, return an exit code
    of 0 and print nothing.
    """
    result = runner.invoke(_main.cli, ['lint', str(fake_repository)])

    assert not result.output
    assert result.exit_code == 0


@git
def test_lint_gitignore(git_repository, runner):
    """Given a repository with files ignored by Git, skip over those files."""
    result = runner.invoke(_main.cli, ['lint', str(git_repository)])

    assert not result.output
    assert result.exit_code == 0


def test_lint_ignore_debian(fake_repository, runner):
    """When debian/copyright is ignored, non-compliant files are found."""
    result = runner.invoke(
        _main.cli,
        ['--ignore-debian', 'lint', str(fake_repository)])

    output_lines = result.output.splitlines()
    assert len(output_lines) == 1
    assert 'no_license.py' in output_lines[0]
    assert result.exit_code
