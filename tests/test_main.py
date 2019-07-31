# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""All tests for reuse._main"""

# pylint: disable=redefined-outer-name

import errno
import os
from inspect import cleandoc
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


def test_lint(
    fake_repository, stringio, git_exe
):  # pylint: disable=unused-argument
    """Run a successful lint. git_exe is there to make sure that the test
    also works if git is not installed.
    """
    result = main(["lint", str(fake_repository)], out=stringio)

    assert result == 0
    assert ":-)" in stringio.getvalue()


def test_lint_git(git_repository, stringio):
    """Run a successful lint."""
    result = main(["lint", str(git_repository)], out=stringio)

    assert result == 0
    assert ":-)" in stringio.getvalue()


def test_lint_fail(fake_repository, stringio):
    """Run a failed lint."""
    (fake_repository / "foo.py").touch()
    result = main(["lint", str(fake_repository)], out=stringio)

    assert result > 0
    assert "foo.py" in stringio.getvalue()
    assert ":-(" in stringio.getvalue()


def test_spdx(fake_repository, stringio):
    """Compile to an SPDX document."""
    os.chdir(str(fake_repository))
    result = main(["spdx"], out=stringio)

    # FIXME: This test is rubbish.
    assert result == 0
    assert stringio.getvalue()


def test_download(fake_repository, stringio, mock_put_license_in_file):
    """Straightforward test."""
    # pylint: disable=unused-argument
    result = main(["download", "0BSD"], out=stringio)

    assert result == 0
    mock_put_license_in_file.assert_called_with(
        "0BSD", Path("LICENSES/0BSD.txt").resolve()
    )


def test_download_file_exists(
    fake_repository, stringio, mock_put_license_in_file
):
    """The to-be-downloaded file already exists."""
    # pylint: disable=unused-argument
    mock_put_license_in_file.side_effect = FileExistsError(
        errno.EEXIST, "", "GPL-3.0-or-later.txt"
    )

    with pytest.raises(SystemExit):
        main(["download", "GPL-3.0-or-later"], out=stringio)


def test_download_request_exception(
    fake_repository, stringio, mock_put_license_in_file
):
    """There was an error while downloading the license file."""
    # pylint: disable=unused-argument
    mock_put_license_in_file.side_effect = requests.RequestException()

    with pytest.raises(SystemExit):
        main(["download", "0BSD"], out=stringio)


def test_download_invalid_spdx(
    fake_repository, stringio, mock_put_license_in_file
):
    """An invalid SPDX identifier was provided."""
    # pylint: disable=unused-argument
    mock_put_license_in_file.side_effect = requests.RequestException()

    with pytest.raises(SystemExit):
        main(["download", "does-not-exist"], out=stringio)


def test_download_custom_output(
    empty_directory, stringio, mock_put_license_in_file
):
    """Download the license into a custom file."""
    # pylint: disable=unused-argument
    result = main(["download", "-o", "foo", "0BSD"], out=stringio)

    assert result == 0
    mock_put_license_in_file.assert_called_with(
        "0BSD", destination=Path("foo")
    )


# FIXME: Replace this test with a monkeypatched test
def test_addheader_simple(fake_repository, stringio):
    """Add a header to a file that does not have one."""
    simple_file = fake_repository / "foo.py"
    simple_file.write_text("pass")

    result = main(
        [
            "addheader",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Mary Sue",
            "foo.py",
        ],
        out=stringio,
    )

    assert result == 0
    assert (
        simple_file.read_text()
        == cleandoc(
            """
            # spdx-FileCopyrightText: Mary Sue
            #
            # spdx-License-Identifier: GPL-3.0-or-later

            pass
            """
        ).replace("spdx", "SPDX")
    )


def test_addheader_specify_style(fake_repository, stringio):
    """Add a header to a file that does not have one, using a custom style."""
    simple_file = fake_repository / "foo.py"
    simple_file.write_text("pass")

    result = main(
        [
            "addheader",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Mary Sue",
            "--style",
            "c",
            "foo.py",
        ],
        out=stringio,
    )

    assert result == 0
    assert (
        simple_file.read_text()
        == cleandoc(
            """
            // spdx-FileCopyrightText: Mary Sue
            //
            // spdx-License-Identifier: GPL-3.0-or-later

            pass
            """
        ).replace("spdx", "SPDX")
    )


def test_addheader_implicit_style(fake_repository, stringio):
    """Add a header to a file that has a recognised extension."""
    simple_file = fake_repository / "foo.js"
    simple_file.write_text("pass")

    result = main(
        [
            "addheader",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Mary Sue",
            "foo.js",
        ],
        out=stringio,
    )

    assert result == 0
    assert (
        simple_file.read_text()
        == cleandoc(
            """
            // spdx-FileCopyrightText: Mary Sue
            //
            // spdx-License-Identifier: GPL-3.0-or-later

            pass
            """
        ).replace("spdx", "SPDX")
    )


def test_addheader_unrecognised_style(fake_repository):
    """Add a header to a file that has an unrecognised extension."""
    simple_file = fake_repository / "foo.foo"
    simple_file.write_text("pass")

    with pytest.raises(SystemExit):
        main(
            [
                "addheader",
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Mary Sue",
                "foo.foo",
            ]
        )


def test_addheader_no_copyright_or_license(fake_repository):
    """Add a header, but supply no copyright or license."""
    simple_file = fake_repository / "foo.py"
    simple_file.write_text("pass")

    with pytest.raises(SystemExit):
        main(["addheader", "foo.py"])
