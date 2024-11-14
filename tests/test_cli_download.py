# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for download."""

# pylint: disable=redefined-outer-name,unused-argument,unspecified-encoding

import errno
import os
import shutil
from pathlib import Path
from unittest.mock import create_autospec
from urllib.error import URLError

import pytest
from click.testing import CliRunner

from reuse.cli import download
from reuse.cli.main import main

# REUSE-IgnoreStart


@pytest.fixture()
def mock_put_license_in_file(monkeypatch):
    """Create a mocked version of put_license_in_file."""
    result = create_autospec(download.put_license_in_file)
    monkeypatch.setattr(download, "put_license_in_file", result)
    return result


class TestDownload:
    """Tests for download."""

    def test_simple(self, empty_directory, mock_put_license_in_file):
        """Straightforward test."""
        result = CliRunner().invoke(main, ["download", "0BSD"])

        assert result.exit_code == 0
        mock_put_license_in_file.assert_called_with(
            "0BSD", Path(os.path.realpath("LICENSES/0BSD.txt")), source=None
        )

    def test_strip_plus(self, empty_directory, mock_put_license_in_file):
        """If downloading LIC+, download LIC instead."""
        result = CliRunner().invoke(main, ["download", "EUPL-1.2+"])

        assert result.exit_code == 0
        mock_put_license_in_file.assert_called_with(
            "EUPL-1.2",
            Path(os.path.realpath("LICENSES/EUPL-1.2.txt")),
            source=None,
        )

    def test_all(self, fake_repository, mock_put_license_in_file):
        """--all downloads all detected licenses."""
        shutil.rmtree("LICENSES")
        result = CliRunner().invoke(main, ["download", "--all"])

        assert result.exit_code == 0
        for lic in [
            "GPL-3.0-or-later",
            "LicenseRef-custom",
            "Autoconf-exception-3.0",
            "Apache-2.0",
            "CC0-1.0",
        ]:
            mock_put_license_in_file.assert_any_call(
                lic, Path(os.path.realpath(f"LICENSES/{lic}.txt")), source=None
            )

    def test_all_with_plus(self, fake_repository, mock_put_license_in_file):
        """--all downloads EUPL-1.2 if EUPL-1.2+ is detected."""
        Path("foo.py").write_text("# SPDX-License-Identifier: EUPL-1.2+")
        result = CliRunner().invoke(main, ["download", "--all"])

        assert result.exit_code == 0
        mock_put_license_in_file.assert_called_once_with(
            "EUPL-1.2",
            Path(os.path.realpath("LICENSES/EUPL-1.2.txt")),
            source=None,
        )

    def test_all_with_plus_and_non_plus(
        self, fake_repository, mock_put_license_in_file
    ):
        """If both EUPL-1.2 and EUPL-1.2+ is detected, download EUPL-1.2 only
        once.
        """
        Path("foo.py").write_text(
            """
            # SPDX-License-Identifier: EUPL-1.2+
            # SPDX-License-Identifier: EUPL-1.2
            """
        )
        result = CliRunner().invoke(main, ["download", "--all"])

        assert result.exit_code == 0
        mock_put_license_in_file.assert_called_once_with(
            "EUPL-1.2",
            Path(os.path.realpath("LICENSES/EUPL-1.2.txt")),
            source=None,
        )

    def test_all_and_license_mutually_exclusive(self, empty_directory):
        """--all and license args are mutually exclusive."""
        result = CliRunner().invoke(main, ["download", "--all", "0BSD"])
        assert result.exit_code != 0
        assert "are mutually exclusive" in result.output

    def test_all_and_output_mutually_exclusive(self, empty_directory):
        """--all and --output are mutually exclusive."""
        result = CliRunner().invoke(
            main, ["download", "--all", "--output", "foo"]
        )
        assert result.exit_code != 0
        assert "is mutually exclusive with" in result.output

    def test_file_exists(self, fake_repository, mock_put_license_in_file):
        """The to-be-downloaded file already exists."""
        mock_put_license_in_file.side_effect = FileExistsError(
            errno.EEXIST, "", "GPL-3.0-or-later.txt"
        )

        result = CliRunner().invoke(main, ["download", "GPL-3.0-or-later"])

        assert result.exit_code == 1
        assert "GPL-3.0-or-later.txt already exists" in result.output

    def test_exception(self, empty_directory, mock_put_license_in_file):
        """There was an error while downloading the license file."""
        mock_put_license_in_file.side_effect = URLError("test")

        result = CliRunner().invoke(main, ["download", "0BSD"])

        assert result.exit_code == 1
        assert "internet" in result.output

    def test_invalid_spdx(self, empty_directory, mock_put_license_in_file):
        """An invalid SPDX identifier was provided."""
        mock_put_license_in_file.side_effect = URLError("test")

        result = CliRunner().invoke(main, ["download", "does-not-exist"])

        assert result.exit_code == 1
        assert "not a valid SPDX License Identifier" in result.output

    def test_custom_output(self, empty_directory, mock_put_license_in_file):
        """Download the license into a custom file."""
        result = CliRunner().invoke(main, ["download", "-o", "foo", "0BSD"])

        assert result.exit_code == 0
        mock_put_license_in_file.assert_called_with(
            "0BSD", destination=Path("foo"), source=None
        )

    def test_custom_output_too_many(
        self, empty_directory, mock_put_license_in_file
    ):
        """Providing more than one license with a custom output results in an
        error.
        """
        result = CliRunner().invoke(
            main,
            ["download", "-o", "foo", "0BSD", "GPL-3.0-or-later"],
        )

        assert result.exit_code != 0
        assert (
            "Cannot use '--output' with more than one license" in result.output
        )

    def test_inside_licenses_dir(
        self, fake_repository, mock_put_license_in_file
    ):
        """While inside the LICENSES/ directory, don't create another LICENSES/
        directory.
        """
        os.chdir(fake_repository / "LICENSES")
        result = CliRunner().invoke(main, ["download", "0BSD"])
        assert result.exit_code == 0
        mock_put_license_in_file.assert_called_with(
            "0BSD", destination=Path("0BSD.txt").absolute(), source=None
        )

    def test_inside_licenses_dir_in_git(
        self, git_repository, mock_put_license_in_file
    ):
        """While inside a random LICENSES/ directory in a Git repository, use
        the root LICENSES/ directory.
        """
        (git_repository / "doc/LICENSES").mkdir()
        os.chdir(git_repository / "doc/LICENSES")
        result = CliRunner().invoke(main, ["download", "0BSD"])
        assert result.exit_code == 0
        mock_put_license_in_file.assert_called_with(
            "0BSD", destination=Path("../../LICENSES/0BSD.txt"), source=None
        )

    def test_different_root(self, fake_repository, mock_put_license_in_file):
        """Download using a different root."""
        (fake_repository / "new_root").mkdir()

        result = CliRunner().invoke(
            main,
            [
                "--root",
                str((fake_repository / "new_root").resolve()),
                "download",
                "MIT",
            ],
        )
        assert result.exit_code == 0
        mock_put_license_in_file.assert_called_with(
            "MIT", Path("new_root/LICENSES/MIT.txt").resolve(), source=None
        )

    def test_licenseref_no_source(self, empty_directory):
        """Downloading a LicenseRef license creates an empty file."""
        CliRunner().invoke(main, ["download", "LicenseRef-hello"])
        assert (
            empty_directory / "LICENSES/LicenseRef-hello.txt"
        ).read_text() == ""

    def test_licenseref_source_file(
        self,
        empty_directory,
    ):
        """Downloading a LicenseRef license with a source file copies that
        file's contents.
        """
        (empty_directory / "foo.txt").write_text("foo")
        CliRunner().invoke(
            main,
            ["download", "--source", "foo.txt", "LicenseRef-hello"],
        )
        assert (
            empty_directory / "LICENSES/LicenseRef-hello.txt"
        ).read_text() == "foo"

    def test_licenseref_source_dir(self, empty_directory):
        """Downloading a LicenseRef license with a source dir copies the text
        from the corresponding file in the directory.
        """
        (empty_directory / "lics").mkdir()
        (empty_directory / "lics/LicenseRef-hello.txt").write_text("foo")

        CliRunner().invoke(
            main, ["download", "--source", "lics", "LicenseRef-hello"]
        )
        assert (
            empty_directory / "LICENSES/LicenseRef-hello.txt"
        ).read_text() == "foo"

    def test_licenseref_false_source_dir(self, empty_directory):
        """Downloading a LicenseRef license with a source that does not contain
        the license results in an error.
        """
        (empty_directory / "lics").mkdir()

        result = CliRunner().invoke(
            main, ["download", "--source", "lics", "LicenseRef-hello"]
        )
        assert result.exit_code == 1
        assert (
            f"{Path('lics') / 'LicenseRef-hello.txt'} does not exist"
            in result.output
        )


class TestSimilarIdentifiers:
    """Test a private function _similar_spdx_identifiers."""

    # pylint: disable=protected-access

    def test_typo(self):
        """Given a misspelt SPDX License Identifier, suggest a better one."""
        result = download._similar_spdx_identifiers("GPL-3.0-or-lter")

        assert "GPL-3.0-or-later" in result
        assert "AGPL-3.0-or-later" in result
        assert "LGPL-3.0-or-later" in result

    def test_prefix(self):
        """Given an incomplete SPDX License Identifier, suggest a better one."""
        result = download._similar_spdx_identifiers("CC0")

        assert "CC0-1.0" in result


# REUSE-IgnoreEnd
