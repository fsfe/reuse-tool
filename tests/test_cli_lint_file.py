# SPDX-FileCopyrightText: 2024 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for lint-file."""

# pylint: disable=unused-argument

from click.testing import CliRunner

from reuse.cli.main import main


class TestLintFile:
    """Tests for lint-file."""

    def test_simple(self, fake_repository):
        """A simple test to make sure it works."""
        result = CliRunner().invoke(main, ["lint-file", "src/custom.py"])
        assert result.exit_code == 0
        assert not result.output

    def test_quiet_lines_mutually_exclusive(self, empty_directory):
        """'--quiet' and '--lines' are mutually exclusive."""
        (empty_directory / "foo.py").write_text("foo")
        result = CliRunner().invoke(
            main, ["lint-file", "--quiet", "--lines", "foo"]
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output

    def test_no_copyright_licensing(self, fake_repository):
        """A file is correctly spotted when it has no copyright or licensing
        info.
        """
        (fake_repository / "foo.py").write_text("foo")
        result = CliRunner().invoke(main, ["lint-file", "foo.py"])
        assert result.exit_code == 1
        output = result.output
        assert "foo.py" in output
        assert "no license identifier" in output
        assert "no copyright notice" in output

    def test_path_outside_project(self, empty_directory):
        """A file can't be outside the project."""
        result = CliRunner().invoke(main, ["lint-file", ".."])
        assert result.exit_code != 0
        assert "'..' is not in" in result.output

    def test_file_not_exists(self, empty_directory):
        """A file must exist."""
        result = CliRunner().invoke(main, ["lint-file", "foo.py"])
        assert "'foo.py' does not exist" in result.output

    def test_ignored_file(self, fake_repository):
        """A corner case where a specified file is ignored. It isn't checked at
        all.
        """
        (fake_repository / "COPYING").write_text("foo")
        result = CliRunner().invoke(main, ["lint-file", "COPYING"])
        assert result.exit_code == 0

    def test_file_covered_by_toml(self, fake_repository_reuse_toml):
        """If a file is covered by REUSE.toml, use its infos."""
        (fake_repository_reuse_toml / "doc/foo.md").write_text("foo")
        result = CliRunner().invoke(main, ["lint-file", "doc/foo.md"])
        assert result.exit_code == 0
