# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for convert-dep5."""

import warnings

from click.testing import CliRunner

from reuse._util import cleandoc_nl
from reuse.cli.main import main

# pylint: disable=unused-argument


class TestConvertDep5:
    """Tests for convert-dep5."""

    def test_simple(self, fake_repository_dep5):
        """Convert a DEP5 repository to a REUSE.toml repository."""
        result = CliRunner().invoke(main, ["convert-dep5"])
        assert result.exit_code == 0
        assert not (fake_repository_dep5 / ".reuse/dep5").exists()
        assert (fake_repository_dep5 / "REUSE.toml").exists()
        assert (fake_repository_dep5 / "REUSE.toml").read_text() == cleandoc_nl(
            """
            version = 1

            [[annotations]]
            path = "doc/**"
            precedence = "aggregate"
            SPDX-FileCopyrightText = "2017 Jane Doe"
            SPDX-License-Identifier = "CC0-1.0"
            """
        )

    def test_no_dep5_file(self, fake_repository):
        """Cannot convert when there is no .reuse/dep5 file."""
        result = CliRunner().invoke(main, ["convert-dep5"])
        assert result.exit_code != 0

    def test_no_warning(self, fake_repository_dep5):
        """No PendingDeprecationWarning when running convert-dep5."""
        with warnings.catch_warnings(record=True) as caught_warnings:
            result = CliRunner().invoke(main, ["convert-dep5"])
            assert result.exit_code == 0
            assert not caught_warnings
