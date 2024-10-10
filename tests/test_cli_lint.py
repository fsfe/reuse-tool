# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2019 Stefan Bakker <s.bakker777@gmail.com>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2022 Pietro Albini <pietro.albini@ferrous-systems.com>
# SPDX-FileCopyrightText: 2024 Carmen Bianca BAKKER <carmenbianca@fsfe.org>
# SPDX-FileCopyrightText: 2024 Skyler Grey <sky@a.starrysky.fyi>
# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

# pylint: disable=unused-argument,too-many-public-methods

"""Tests for lint."""

import json
import os
import shutil
from inspect import cleandoc

from click.testing import CliRunner
from conftest import RESOURCES_DIRECTORY

from reuse._util import cleandoc_nl
from reuse.cli.main import main
from reuse.report import LINT_VERSION


class TestLint:
    """Tests for lint."""

    def test_simple(self, fake_repository, optional_git_exe, optional_hg_exe):
        """Run a successful lint. The optional VCSs are there to make sure that
        the test also works if these programs are not installed.
        """
        result = CliRunner().invoke(main, ["lint"])

        assert result.exit_code == 0
        assert ":-)" in result.output

    def test_reuse_toml(self, fake_repository_reuse_toml):
        """Run a simple lint with REUSE.toml."""
        result = CliRunner().invoke(main, ["lint"])

        assert result.exit_code == 0
        assert ":-)" in result.output

    def test_dep5(self, fake_repository_dep5):
        """Run a simple lint with .reuse/dep5."""
        result = CliRunner().invoke(main, ["lint"])

        assert result.exit_code == 0
        assert ":-)" in result.output

    def test_git(self, git_repository):
        """Run a successful lint."""
        result = CliRunner().invoke(main, ["lint"])

        assert result.exit_code == 0
        assert ":-)" in result.output

    def test_submodule(self, submodule_repository):
        """Run a successful lint."""
        (submodule_repository / "submodule/foo.c").write_text("foo")
        result = CliRunner().invoke(main, ["lint"])

        assert result.exit_code == 0
        assert ":-)" in result.output

    def test_submodule_included(self, submodule_repository):
        """Run a successful lint."""
        result = CliRunner().invoke(main, ["--include-submodules", "lint"])

        assert result.exit_code == 0
        assert ":-)" in result.output

    def test_submodule_included_fail(self, submodule_repository):
        """Run a failed lint."""
        (submodule_repository / "submodule/foo.c").write_text("foo")
        result = CliRunner().invoke(main, ["--include-submodules", "lint"])

        assert result.exit_code == 1
        assert ":-(" in result.output

    def test_meson_subprojects(self, fake_repository):
        """Verify that subprojects are ignored."""
        result = CliRunner().invoke(main, ["lint"])

        assert result.exit_code == 0
        assert ":-)" in result.output

    def test_meson_subprojects_fail(self, subproject_repository):
        """Verify that files in './subprojects' are not ignored."""
        # ./subprojects/foo.wrap misses license and linter fails
        (subproject_repository / "subprojects/foo.wrap").write_text("foo")
        result = CliRunner().invoke(main, ["lint"])

        assert result.exit_code == 1
        assert ":-(" in result.output

    def test_meson_subprojects_included_fail(self, subproject_repository):
        """When Meson subprojects are included, fail on errors."""
        result = CliRunner().invoke(
            main, ["--include-meson-subprojects", "lint"]
        )

        assert result.exit_code == 1
        assert ":-(" in result.output

    def test_meson_subprojects_included(self, subproject_repository):
        """Successfully lint when Meson subprojects are included."""
        # ./subprojects/libfoo/foo.c has license and linter succeeds
        (subproject_repository / "subprojects/libfoo/foo.c").write_text(
            cleandoc(
                """
                SPDX-FileCopyrightText: 2022 Jane Doe
                SPDX-License-Identifier: GPL-3.0-or-later
                """
            )
        )
        result = CliRunner().invoke(
            main, ["--include-meson-subprojects", "lint"]
        )

        assert result.exit_code == 0
        assert ":-)" in result.output

    def test_fail(self, fake_repository):
        """Run a failed lint."""
        (fake_repository / "foo.py").write_text("foo")
        result = CliRunner().invoke(main, ["lint"])

        assert result.exit_code > 0
        assert "foo.py" in result.output
        assert ":-(" in result.output

    def test_fail_quiet(self, fake_repository):
        """Run a failed lint."""
        (fake_repository / "foo.py").write_text("foo")
        result = CliRunner().invoke(main, ["lint", "--quiet"])

        assert result.exit_code > 0
        assert result.output == ""

    def test_dep5_decode_error(self, fake_repository_dep5):
        """Display an error if dep5 cannot be decoded."""
        shutil.copy(
            RESOURCES_DIRECTORY / "fsfe.png",
            fake_repository_dep5 / ".reuse/dep5",
        )
        result = CliRunner().invoke(main, ["lint"])
        assert result.exit_code != 0
        assert str(fake_repository_dep5 / ".reuse/dep5") in result.output
        assert "could not be parsed" in result.output
        assert "'utf-8' codec can't decode byte" in result.output

    def test_dep5_parse_error(self, fake_repository_dep5, capsys):
        """Display an error if there's a dep5 parse error."""
        (fake_repository_dep5 / ".reuse/dep5").write_text("foo")
        result = CliRunner().invoke(main, ["lint"])
        assert result.exit_code != 0
        assert str(fake_repository_dep5 / ".reuse/dep5") in result.output
        assert "could not be parsed" in result.output

    def test_toml_parse_error_version(self, fake_repository_reuse_toml, capsys):
        """If version has the wrong type, print an error."""
        (fake_repository_reuse_toml / "REUSE.toml").write_text("version = 'a'")
        result = CliRunner().invoke(main, ["lint"])
        assert result.exit_code != 0
        assert str(fake_repository_reuse_toml / "REUSE.toml") in result.output
        assert "could not be parsed" in result.output

    def test_toml_parse_error_annotation(
        self, fake_repository_reuse_toml, capsys
    ):
        """If there is an error in an annotation, print an error."""
        (fake_repository_reuse_toml / "REUSE.toml").write_text(
            cleandoc_nl(
                """
                version = 1

                [[annotations]]
                path = 1
                """
            )
        )
        result = CliRunner().invoke(main, ["lint"])
        assert result.exit_code != 0
        assert str(fake_repository_reuse_toml / "REUSE.toml") in result.output
        assert "could not be parsed" in result.output

    def test_json(self, fake_repository):
        """Run a failed lint."""
        result = CliRunner().invoke(main, ["lint", "--json"])
        output = json.loads(result.output)

        assert result.exit_code == 0
        assert output["lint_version"] == LINT_VERSION
        assert len(output["files"]) == 8

    def test_json_fail(self, fake_repository):
        """Run a failed lint."""
        (fake_repository / "foo.py").write_text("foo")
        result = CliRunner().invoke(main, ["lint", "--json"])
        output = json.loads(result.output)

        assert result.exit_code > 0
        assert output["lint_version"] == LINT_VERSION
        assert len(output["non_compliant"]["missing_licensing_info"]) == 1
        assert len(output["non_compliant"]["missing_copyright_info"]) == 1
        assert len(output["files"]) == 9

    def test_no_file_extension(self, fake_repository):
        """If a license has no file extension, the lint fails."""
        (fake_repository / "LICENSES/CC0-1.0.txt").rename(
            fake_repository / "LICENSES/CC0-1.0"
        )
        result = CliRunner().invoke(main, ["lint"])

        assert result.exit_code > 0
        assert "Licenses without file extension: CC0-1.0" in result.output
        assert ":-(" in result.output

    def test_custom_root(self, fake_repository):
        """Use a custom root location."""
        result = CliRunner().invoke(main, ["--root", "doc", "lint"])

        assert result.exit_code > 0
        assert "usage.md" in result.output
        assert ":-(" in result.output

    def test_custom_root_git(self, git_repository):
        """Use a custom root location in a git repo."""
        result = CliRunner().invoke(main, ["--root", "doc", "lint"])

        assert result.exit_code > 0
        assert "usage.md" in result.output
        assert ":-(" in result.output

    def test_custom_root_different_cwd(self, fake_repository_reuse_toml):
        """Use a custom root while CWD is different."""
        os.chdir("/")
        result = CliRunner().invoke(
            main, ["--root", str(fake_repository_reuse_toml), "lint"]
        )

        assert result.exit_code == 0
        assert ":-)" in result.output

    def test_custom_root_is_file(self, fake_repository):
        """Custom root cannot be a file."""
        result = CliRunner().invoke(main, ["--root", ".reuse/dep5", "lint"])
        assert result.exit_code != 0

    def test_custom_root_not_exists(self, fake_repository):
        """Custom root must exist."""
        result = CliRunner().invoke(main, ["--root", "does-not-exist", "lint"])
        assert result.exit_code != 0

    def test_no_multiprocessing(self, fake_repository, multiprocessing):
        """--no-multiprocessing works."""
        result = CliRunner().invoke(main, ["--no-multiprocessing", "lint"])

        assert result.exit_code == 0
        assert ":-)" in result.output
