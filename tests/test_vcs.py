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

from conftest import vcs_params


@vcs_params
class TestVCSStrategyCommon:
    """Common tests that should work for all strategies.."""

    def test_find_root(self, vcs_strategy, vcs_repo):
        """When using reuse in a child directory of a VCS repo, always find the
        root directory.
        """
        os.chdir("src")
        result = vcs_strategy.find_root()
        assert result == Path(os.path.relpath(vcs_repo, Path.cwd()))
