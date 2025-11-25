# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2024 Skyler Grey <sky@a.starrysky.fyi>
# SPDX-FileCopyrightText: 2025 Nguyễn Gia Phong <cnx@loang.net>
# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for reuse.vcs"""


import os
from pathlib import Path
from typing import cast

from reuse import vcs


def test_find_root_in_fossil_checkout(fossil_checkout):
    """Test finding a Fossil checkout from a child directory."""
    os.chdir("src")
    result = vcs.find_root()
    assert isinstance(result, Path)
    assert result.absolute().resolve() == fossil_checkout


def test_find_root_in_git_repo(git_repository):
    """When using reuse from a child directory in a Git repo, always find the
    root directory.
    """
    os.chdir("src")
    result = cast(Path, vcs.find_root())

    assert Path(result).absolute().resolve() == git_repository


def test_find_root_in_hg_repo(hg_repository):
    """When using reuse from a child directory in a Mercurial repo, always find
    the root directory.
    """
    os.chdir("src")
    result = cast(Path, vcs.find_root())

    assert Path(result).absolute().resolve() == hg_repository


def test_find_root_in_jujutsu_repo(jujutsu_repository):
    """When using reuse from a child directory in a Jujutsu repo, always find
    the root directory.
    """
    os.chdir("src")
    result = cast(Path, vcs.find_root())

    assert Path(result).absolute().resolve() == jujutsu_repository


def test_find_root_in_pijul_repo(pijul_repository):
    """When using reuse from a child directory in a Pijul repo, always find
    the root directory.
    """
    os.chdir("src")
    result = cast(Path, vcs.find_root())

    assert Path(result).absolute().resolve() == pijul_repository
