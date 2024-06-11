# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2019 Stefan Bakker <s.bakker777@gmail.com>
# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2022 Pietro Albini <pietro.albini@ferrous-systems.com>
# SPDX-FileCopyrightText: 2024 Carmen Bianca BAKKER <carmenbianca@fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for reuse._main: lint, spdx, download"""

# pylint: disable=redefined-outer-name,unused-argument

import errno
import json
import os
import re
import shutil
import warnings
from inspect import cleandoc
from pathlib import Path
from typing import Generator, Optional
from unittest.mock import create_autospec
from urllib.error import URLError

import pytest
from conftest import RESOURCES_DIRECTORY
from freezegun import freeze_time

from reuse import download
from reuse._main import main
from reuse._util import GIT_EXE, HG_EXE, PIJUL_EXE, cleandoc_nl
from reuse.report import LINT_VERSION

# REUSE-IgnoreStart


@pytest.fixture(params=[True, False])
def optional_git_exe(
    request, monkeypatch
) -> Generator[Optional[str], None, None]:
    """Run the test with or without git."""
    exe = GIT_EXE if request.param else ""
    monkeypatch.setattr("reuse.vcs.GIT_EXE", exe)
    monkeypatch.setattr("reuse._util.GIT_EXE", exe)
    yield exe


@pytest.fixture(params=[True, False])
def optional_hg_exe(
    request, monkeypatch
) -> Generator[Optional[str], None, None]:
    """Run the test with or without mercurial."""
    exe = HG_EXE if request.param else ""
    monkeypatch.setattr("reuse.vcs.HG_EXE", exe)
    monkeypatch.setattr("reuse._util.HG_EXE", exe)
    yield exe


@pytest.fixture(params=[True, False])
def optional_pijul_exe(
    request, monkeypatch
) -> Generator[Optional[str], None, None]:
    """Run the test with or without Pijul."""
    exe = PIJUL_EXE if request.param else ""
    monkeypatch.setattr("reuse.vcs.PIJUL_EXE", exe)
    monkeypatch.setattr("reuse._util.PIJUL_EXE", exe)
    yield exe


@pytest.fixture()
def mock_put_license_in_file(monkeypatch):
    """Create a mocked version of put_license_in_file."""
    result = create_autospec(download.put_license_in_file)
    monkeypatch.setattr(download, "put_license_in_file", result)
    return result


def test_lint(fake_repository, stringio, optional_git_exe, optional_hg_exe):
    """Run a successful lint. The optional VCSs are there to make sure that the
    test also works if these programs are not installed.
    """
    result = main(["lint"], out=stringio)

    assert result == 0
    assert ":-)" in stringio.getvalue()


def test_lint_reuse_toml(fake_repository_reuse_toml, stringio):
    """Run a simple lint with REUSE.toml."""
    result = main(["lint"], out=stringio)

    assert result == 0
    assert ":-)" in stringio.getvalue()


def test_lint_dep5(fake_repository_dep5, stringio):
    """Run a simple lint with .reuse/dep5."""
    result = main(["lint"], out=stringio)

    assert result == 0
    assert ":-)" in stringio.getvalue()


def test_lint_git(git_repository, stringio):
    """Run a successful lint."""
    result = main(["lint"], out=stringio)

    assert result == 0
    assert ":-)" in stringio.getvalue()


def test_lint_submodule(submodule_repository, stringio):
    """Run a successful lint."""
    (submodule_repository / "submodule/foo.c").write_text("foo")
    result = main(["lint"], out=stringio)

    assert result == 0
    assert ":-)" in stringio.getvalue()


def test_lint_submodule_included(submodule_repository, stringio):
    """Run a successful lint."""
    result = main(["--include-submodules", "lint"], out=stringio)

    assert result == 0
    assert ":-)" in stringio.getvalue()


def test_lint_submodule_included_fail(submodule_repository, stringio):
    """Run a failed lint."""
    (submodule_repository / "submodule/foo.c").write_text("foo")
    result = main(["--include-submodules", "lint"], out=stringio)

    assert result == 1
    assert ":-(" in stringio.getvalue()


def test_lint_meson_subprojects(fake_repository, stringio):
    """Verify that subprojects are ignored."""
    (fake_repository / "meson.build").write_text(
        cleandoc(
            """
            SPDX-FileCopyrightText: 2022 Jane Doe
            SPDX-License-Identifier: CC0-1.0
            """
        )
    )
    subprojects_dir = fake_repository / "subprojects"
    subprojects_dir.mkdir()
    libfoo_dir = subprojects_dir / "libfoo"
    libfoo_dir.mkdir()
    # ./subprojects/foo.wrap has license and linter succeeds
    (subprojects_dir / "foo.wrap").write_text(
        cleandoc(
            """
            SPDX-FileCopyrightText: 2022 Jane Doe
            SPDX-License-Identifier: CC0-1.0
            """
        )
    )
    # ./subprojects/libfoo/foo.c misses license but is ignored
    (libfoo_dir / "foo.c").write_text("foo")
    result = main(["lint"], out=stringio)

    assert result == 0
    assert ":-)" in stringio.getvalue()


def test_lint_meson_subprojects_fail(fake_repository, stringio):
    """Verify that files in './subprojects' are not ignored."""
    (fake_repository / "meson.build").write_text(
        cleandoc(
            """
            SPDX-FileCopyrightText: 2022 Jane Doe
            SPDX-License-Identifier: CC0-1.0
            """
        )
    )
    subprojects_dir = fake_repository / "subprojects"
    subprojects_dir.mkdir()
    # ./subprojects/foo.wrap misses license and linter fails
    (subprojects_dir / "foo.wrap").write_text("foo")
    result = main(["lint"], out=stringio)

    assert result == 1
    assert ":-(" in stringio.getvalue()


def test_lint_meson_subprojects_included_fail(fake_repository, stringio):
    """When Meson subprojects are included, fail on errors."""
    (fake_repository / "meson.build").write_text(
        cleandoc(
            """
            SPDX-FileCopyrightText: 2022 Jane Doe
            SPDX-License-Identifier: CC0-1.0
            """
        )
    )
    libfoo_dir = fake_repository / "subprojects/libfoo"
    libfoo_dir.mkdir(parents=True)
    # ./subprojects/libfoo/foo.c misses license and linter fails
    (libfoo_dir / "foo.c").write_text("foo")
    result = main(["--include-meson-subprojects", "lint"], out=stringio)

    assert result == 1
    assert ":-(" in stringio.getvalue()


def test_lint_meson_subprojects_included(fake_repository, stringio):
    """Successfully lint when Meson subprojects are included."""
    (fake_repository / "meson.build").write_text(
        cleandoc(
            """
            SPDX-FileCopyrightText: 2022 Jane Doe
            SPDX-License-Identifier: CC0-1.0
            """
        )
    )
    libfoo_dir = fake_repository / "subprojects/libfoo"
    libfoo_dir.mkdir(parents=True)
    # ./subprojects/libfoo/foo.c has license and linter succeeds
    (libfoo_dir / "foo.c").write_text(
        cleandoc(
            """
            SPDX-FileCopyrightText: 2022 Jane Doe
            SPDX-License-Identifier: GPL-3.0-or-later
            """
        )
    )
    result = main(["--include-meson-subprojects", "lint"], out=stringio)

    assert result == 0
    assert ":-)" in stringio.getvalue()


def test_lint_fail(fake_repository, stringio):
    """Run a failed lint."""
    (fake_repository / "foo.py").write_text("foo")
    result = main(["lint"], out=stringio)

    assert result > 0
    assert "foo.py" in stringio.getvalue()
    assert ":-(" in stringio.getvalue()


def test_lint_fail_quiet(fake_repository, stringio):
    """Run a failed lint."""
    (fake_repository / "foo.py").write_text("foo")
    result = main(["lint", "--quiet"], out=stringio)

    assert result > 0
    assert stringio.getvalue() == ""


def test_lint_dep5_decode_error(fake_repository_dep5, capsys):
    """Display an error if dep5 cannot be decoded."""
    shutil.copy(
        RESOURCES_DIRECTORY / "fsfe.png", fake_repository_dep5 / ".reuse/dep5"
    )
    with pytest.raises(SystemExit):
        main(["lint"])
    assert "could not be decoded" in capsys.readouterr().err


def test_lint_dep5_parse_error(fake_repository_dep5, capsys):
    """Display an error if there's a dep5 parse error."""
    (fake_repository_dep5 / ".reuse/dep5").write_text("foo")
    with pytest.raises(SystemExit):
        main(["lint"])
    assert "could not be parsed" in capsys.readouterr().err


def test_lint_json(fake_repository, stringio):
    """Run a failed lint."""
    result = main(["lint", "--json"], out=stringio)
    output = json.loads(stringio.getvalue())

    assert result == 0
    assert output["lint_version"] == LINT_VERSION
    assert len(output["files"]) == 8


def test_lint_json_fail(fake_repository, stringio):
    """Run a failed lint."""
    (fake_repository / "foo.py").write_text("foo")
    result = main(["lint", "--json"], out=stringio)
    output = json.loads(stringio.getvalue())

    assert result > 0
    assert output["lint_version"] == LINT_VERSION
    assert len(output["non_compliant"]["missing_licensing_info"]) == 1
    assert len(output["non_compliant"]["missing_copyright_info"]) == 1
    assert len(output["files"]) == 9


def test_lint_no_file_extension(fake_repository, stringio):
    """If a license has no file extension, the lint fails."""
    (fake_repository / "LICENSES/CC0-1.0.txt").rename(
        fake_repository / "LICENSES/CC0-1.0"
    )
    result = main(["lint"], out=stringio)

    assert result > 0
    assert "Licenses without file extension: CC0-1.0" in stringio.getvalue()
    assert ":-(" in stringio.getvalue()


def test_lint_custom_root(fake_repository, stringio):
    """Use a custom root location."""
    result = main(["--root", "doc", "lint"], out=stringio)

    assert result > 0
    assert "usage.md" in stringio.getvalue()
    assert ":-(" in stringio.getvalue()


def test_lint_custom_root_git(git_repository, stringio):
    """Use a custom root location in a git repo."""
    result = main(["--root", "doc", "lint"], out=stringio)

    assert result > 0
    assert "usage.md" in stringio.getvalue()
    assert ":-(" in stringio.getvalue()


def test_lint_custom_root_different_cwd(fake_repository_reuse_toml, stringio):
    """Use a custom root while CWD is different."""
    os.chdir("/")
    result = main(
        ["--root", str(fake_repository_reuse_toml), "lint"], out=stringio
    )

    assert result == 0
    assert ":-)" in stringio.getvalue()


def test_lint_custom_root_is_file(fake_repository, stringio):
    """Custom root cannot be a file."""
    with pytest.raises(SystemExit):
        main(["--root", ".reuse/dep5", "lint"], out=stringio)


def test_lint_custom_root_not_exists(fake_repository, stringio):
    """Custom root must exist."""
    with pytest.raises(SystemExit):
        main(["--root", "does-not-exist", "lint"], out=stringio)


def test_lint_no_multiprocessing(fake_repository, stringio, multiprocessing):
    """--no-multiprocessing works."""
    result = main(["--no-multiprocessing", "lint"], out=stringio)

    assert result == 0
    assert ":-)" in stringio.getvalue()


@freeze_time("2024-04-08T17:34:00Z")
def test_spdx(fake_repository, stringio):
    """Compile to an SPDX document."""
    os.chdir(str(fake_repository))
    result = main(["spdx"], out=stringio)
    output = stringio.getvalue()

    # Ensure no LicenseConcluded is included without the flag
    assert "\nLicenseConcluded: NOASSERTION\n" in output
    assert "\nLicenseConcluded: GPL-3.0-or-later\n" not in output
    assert "\nCreator: Person: Anonymous ()\n" in output
    assert "\nCreator: Organization: Anonymous ()\n" in output
    assert "\nCreated: 2024-04-08T17:34:00Z\n" in output

    # TODO: This test is rubbish.
    assert result == 0
    assert output


def test_spdx_creator_info(fake_repository, stringio):
    """Ensure the --creator-* flags are properly formatted"""
    os.chdir(str(fake_repository))
    result = main(
        [
            "spdx",
            "--creator-person=Jane Doe (jane.doe@example.org)",
            "--creator-organization=FSFE",
        ],
        out=stringio,
    )
    output = stringio.getvalue()

    assert result == 0
    assert "\nCreator: Person: Jane Doe (jane.doe@example.org)\n" in output
    assert "\nCreator: Organization: FSFE ()\n" in output


def test_spdx_add_license_concluded(fake_repository, stringio):
    """Compile to an SPDX document with the LicenseConcluded field."""
    os.chdir(str(fake_repository))
    result = main(
        [
            "spdx",
            "--add-license-concluded",
            "--creator-person=Jane Doe",
            "--creator-organization=FSFE",
        ],
        out=stringio,
    )
    output = stringio.getvalue()

    # Ensure no LicenseConcluded is included without the flag
    assert result == 0
    assert "\nLicenseConcluded: NOASSERTION\n" not in output
    assert "\nLicenseConcluded: GPL-3.0-or-later\n" in output
    assert "\nCreator: Person: Jane Doe ()\n" in output
    assert "\nCreator: Organization: FSFE ()\n" in output


def test_spdx_add_license_concluded_without_creator_info(
    fake_repository, stringio
):
    """Adding LicenseConcluded should require creator information"""
    os.chdir(str(fake_repository))
    with pytest.raises(SystemExit):
        main(["spdx", "--add-license-concluded"], out=stringio)


def test_spdx_no_multiprocessing(fake_repository, stringio, multiprocessing):
    """--no-multiprocessing works."""
    os.chdir(str(fake_repository))
    result = main(["--no-multiprocessing", "spdx"], out=stringio)

    # TODO: This test is rubbish.
    assert result == 0
    assert stringio.getvalue()


def test_download(fake_repository, stringio, mock_put_license_in_file):
    """Straightforward test."""
    result = main(["download", "0BSD"], out=stringio)

    assert result == 0
    mock_put_license_in_file.assert_called_with(
        "0BSD", Path("LICENSES/0BSD.txt").resolve(), source=None
    )


def test_download_file_exists(
    fake_repository, stringio, mock_put_license_in_file
):
    """The to-be-downloaded file already exists."""
    mock_put_license_in_file.side_effect = FileExistsError(
        errno.EEXIST, "", "GPL-3.0-or-later.txt"
    )

    result = main(["download", "GPL-3.0-or-later"], out=stringio)

    assert result == 1
    assert "GPL-3.0-or-later.txt already exists" in stringio.getvalue()


def test_download_exception(
    fake_repository, stringio, mock_put_license_in_file
):
    """There was an error while downloading the license file."""
    mock_put_license_in_file.side_effect = URLError("test")

    result = main(["download", "0BSD"], out=stringio)

    assert result == 1
    assert "internet" in stringio.getvalue()


def test_download_invalid_spdx(
    fake_repository, stringio, mock_put_license_in_file
):
    """An invalid SPDX identifier was provided."""
    mock_put_license_in_file.side_effect = URLError("test")

    result = main(["download", "does-not-exist"], out=stringio)

    assert result == 1
    assert "not a valid SPDX License Identifier" in stringio.getvalue()


def test_download_custom_output(
    empty_directory, stringio, mock_put_license_in_file
):
    """Download the license into a custom file."""
    result = main(["download", "-o", "foo", "0BSD"], out=stringio)

    assert result == 0
    mock_put_license_in_file.assert_called_with(
        "0BSD", destination=Path("foo"), source=None
    )


def test_download_custom_output_too_many(
    empty_directory, stringio, mock_put_license_in_file
):
    """Providing more than one license with a custom output results in an
    error.
    """
    with pytest.raises(SystemExit):
        main(
            ["download", "-o", "foo", "0BSD", "GPL-3.0-or-later"], out=stringio
        )


def test_download_inside_licenses_dir(
    fake_repository, stringio, mock_put_license_in_file
):
    """While inside the LICENSES/ directory, don't create another LICENSES/
    directory.
    """
    os.chdir(fake_repository / "LICENSES")
    result = main(["download", "0BSD"], out=stringio)
    assert result == 0
    mock_put_license_in_file.assert_called_with(
        "0BSD", destination=Path("0BSD.txt").absolute(), source=None
    )


def test_download_inside_licenses_dir_in_git(
    git_repository, stringio, mock_put_license_in_file
):
    """While inside a random LICENSES/ directory in a Git repository,.use the
    root LICENSES/ directory.
    """
    (git_repository / "doc/LICENSES").mkdir()
    os.chdir(git_repository / "doc/LICENSES")
    result = main(["download", "0BSD"], out=stringio)
    assert result == 0
    mock_put_license_in_file.assert_called_with(
        "0BSD", destination=Path("../../LICENSES/0BSD.txt"), source=None
    )


def test_download_different_root(
    fake_repository, stringio, mock_put_license_in_file
):
    """Download using a different root."""
    (fake_repository / "new_root").mkdir()

    result = main(
        [
            "--root",
            str((fake_repository / "new_root").resolve()),
            "download",
            "MIT",
        ],
        out=stringio,
    )
    assert result == 0
    mock_put_license_in_file.assert_called_with(
        "MIT", Path("new_root/LICENSES/MIT.txt").resolve(), source=None
    )


def test_download_licenseref_no_source(empty_directory, stringio):
    """Downloading a LicenseRef license creates an empty file."""
    main(["download", "LicenseRef-hello"], out=stringio)
    assert (empty_directory / "LICENSES/LicenseRef-hello.txt").read_text() == ""


def test_download_licenseref_source_file(empty_directory, stringio):
    """Downloading a LicenseRef license with a source file copies that file's
    contents.
    """
    (empty_directory / "foo.txt").write_text("foo")
    main(["download", "--source", "foo.txt", "LicenseRef-hello"], out=stringio)
    assert (
        empty_directory / "LICENSES/LicenseRef-hello.txt"
    ).read_text() == "foo"


def test_download_licenseref_source_dir(empty_directory, stringio):
    """Downloading a LicenseRef license with a source dir copies the text from
    the corresponding file in the directory.
    """
    (empty_directory / "lics").mkdir()
    (empty_directory / "lics/LicenseRef-hello.txt").write_text("foo")

    main(["download", "--source", "lics", "LicenseRef-hello"], out=stringio)
    assert (
        empty_directory / "LICENSES/LicenseRef-hello.txt"
    ).read_text() == "foo"


def test_download_licenseref_false_source_dir(empty_directory, stringio):
    """Downloading a LicenseRef license with a source that does not contain the
    license results in an error.
    """
    (empty_directory / "lics").mkdir()

    result = main(
        ["download", "--source", "lics", "LicenseRef-hello"], out=stringio
    )
    assert result != 0
    assert (
        f"{Path('lics') / 'LicenseRef-hello.txt'} does not exist"
        in stringio.getvalue()
    )


def test_supported_licenses(stringio):
    """Invoke the supported-licenses command and check whether the result
    contains at least one license in the expected format.
    """

    assert main(["supported-licenses"], out=stringio) == 0
    assert re.search(
        # pylint: disable=line-too-long
        r"GPL-3\.0-or-later\s+GNU General Public License v3\.0 or later\s+https:\/\/spdx\.org\/licenses\/GPL-3\.0-or-later\.html\s+\n",
        stringio.getvalue(),
    )


def test_convert_dep5(fake_repository_dep5, stringio):
    """Convert a DEP5 repository to a REUSE.toml repository."""
    result = main(["convert-dep5"], out=stringio)

    assert result == 0
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


def test_convert_dep5_no_dep5_file(fake_repository, stringio):
    """Cannot convert when there is no .reuse/dep5 file."""
    with pytest.raises(SystemExit):
        main(["convert-dep5"], out=stringio)


def test_convert_dep5_no_warning(fake_repository_dep5, stringio):
    """No PendingDeprecationWarning when running convert-dep5."""
    with warnings.catch_warnings(record=True) as caught_warnings:
        result = main(["convert-dep5"], out=stringio)
        assert result == 0
        assert not caught_warnings


# REUSE-IgnoreEnd
