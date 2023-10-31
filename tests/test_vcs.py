# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for reuse.vcs"""


import os
from pathlib import Path

from reuse import vcs


def test_find_root_in_git_repo(git_repository):
    """When using reuse from a child directory in a Git repo, always find the
    root directory.
    """
    os.chdir("src")
    result = vcs.find_root()

    assert Path(result).absolute().resolve() == git_repository


def test_find_root_in_hg_repo(hg_repository):
    """When using reuse from a child directory in a Mercurial repo, always find
    the root directory.
    """
    os.chdir("src")
    result = vcs.find_root()

    assert Path(result).absolute().resolve() == hg_repository


def test_find_root_in_pijul_repo(pijul_repository):
    """When using reuse from a child directory in a Pijul repo, always find
    the root directory.
    """
    os.chdir("src")
    result = vcs.find_root()

    assert Path(result).absolute().resolve() == pijul_repository
