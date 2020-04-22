# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for reuse.vcs"""

# pylint: disable=invalid-name

import os
from pathlib import Path

import pytest

from reuse import vcs
from reuse._util import GIT_EXE, HG_EXE

git = pytest.mark.skipif(not GIT_EXE, reason="requires git")
hg = pytest.mark.skipif(not HG_EXE, reason="requires mercurial")


@git
def test_find_root_in_git_repo(git_repository):
    """When using reuse from a child directory in a Git repo, always find the
    root directory.
    """
    os.chdir("src")
    result = vcs.find_root()

    assert Path(result).absolute().resolve() == git_repository


@hg
def test_find_root_in_hg_repo(hg_repository):
    """When using reuse from a child directory in a Mercurial repo, always find
    the root directory.
    """
    os.chdir("src")
    result = vcs.find_root()

    assert Path(result).absolute().resolve() == hg_repository
