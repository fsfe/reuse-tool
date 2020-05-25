# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2019 Stefan Bakker <s.bakker777@gmail.com>
# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for reuse._main: lint, spdx, download"""

# pylint: disable=redefined-outer-name,unused-argument

import errno
import os
from pathlib import Path
from unittest.mock import create_autospec

import pytest
import requests

from reuse import download
from reuse._main import main


@pytest.fixture()
def mock_put_license_in_file(monkeypatch):
    """Create a mocked version of put_license_in_file."""
    result = create_autospec(download.put_license_in_file)
    monkeypatch.setattr(download, "put_license_in_file", result)
    return result


def test_lint(fake_repository, stringio, git_exe):
    """Run a successful lint. git_exe is there to make sure that the test
    also works if git is not installed.
    """
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


def test_lint_fail(fake_repository, stringio):
    """Run a failed lint."""
    (fake_repository / "foo.py").write_text("foo")
    result = main(["lint"], out=stringio)

    assert result > 0
    assert "foo.py" in stringio.getvalue()
    assert ":-(" in stringio.getvalue()


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
    assert "index.rst" in stringio.getvalue()
    assert ":-(" in stringio.getvalue()


def test_lint_custom_root_git(git_repository, stringio):
    """Use a custom root location in a git repo."""
    result = main(["--root", "doc", "lint"], out=stringio)

    assert result > 0
    assert "index.rst" in stringio.getvalue()
    assert ":-(" in stringio.getvalue()


def test_lint_custom_root_different_cwd(fake_repository, stringio):
    """Use a custom root while CWD is different."""
    os.chdir("/")
    result = main(["--root", str(fake_repository), "lint"], out=stringio)

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


def test_spdx(fake_repository, stringio):
    """Compile to an SPDX document."""
    os.chdir(str(fake_repository))
    result = main(["spdx"], out=stringio)

    # TODO: This test is rubbish.
    assert result == 0
    assert stringio.getvalue()


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
        "0BSD", Path("LICENSES/0BSD.txt").resolve()
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


def test_download_request_exception(
    fake_repository, stringio, mock_put_license_in_file
):
    """There was an error while downloading the license file."""
    mock_put_license_in_file.side_effect = requests.RequestException()

    result = main(["download", "0BSD"], out=stringio)

    assert result == 1
    assert "internet" in stringio.getvalue()


def test_download_invalid_spdx(
    fake_repository, stringio, mock_put_license_in_file
):
    """An invalid SPDX identifier was provided."""
    mock_put_license_in_file.side_effect = requests.RequestException()

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
        "0BSD", destination=Path("foo")
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
