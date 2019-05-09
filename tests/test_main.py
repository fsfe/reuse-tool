# SPDX-Copyright: 2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""All tests for reuse._main"""

import os

import requests

from reuse._main import main


class MockResponse:
    """Super simple mocked version of Response."""

    # pylint: disable=too-few-public-methods

    def __init__(self, text=None, status_code=None):
        self.text = text
        self.status_code = status_code


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


def test_spdx(fake_repository, stringio):
    """Compile to an SPDX document."""
    os.chdir(str(fake_repository))
    result = main(["spdx"], out=stringio)

    # FIXME: This test is rubbish.
    assert result == 0
    assert stringio.getvalue()


def test_download(fake_repository, stringio, monkeypatch):
    """Straightforward test."""
    monkeypatch.setattr(
        requests, "get", lambda _: MockResponse("hello\n", 200)
    )
    result = main(["download", "0BSD"], out=stringio)

    assert result == 0
    assert (fake_repository / "LICENSES/0BSD.txt").read_text() == "hello\n"


def test_download_file_exists(fake_repository, stringio, monkeypatch):
    """The to-be-downloaded file already exists."""
    # pylint: disable=unused-argument
    monkeypatch.setattr(
        requests, "get", lambda _: MockResponse("hello\n", 200)
    )
    result = main(["download", "GPL-3.0-or-later"], out=stringio)

    assert result == 1
    assert "GPL-3.0-or-later.txt already exists" in stringio.getvalue()


def test_download_request_exception(fake_repository, stringio, monkeypatch):
    """There was an error while downloading the license file."""
    # pylint: disable=unused-argument
    monkeypatch.setattr(
        requests, "get", lambda _: MockResponse(status_code=404)
    )
    result = main(["download", "0BSD"], out=stringio)

    assert result == 1
    assert "Failed to download license" in stringio.getvalue()
    assert "internet connection" in stringio.getvalue()


def test_download_invalid_spdx(fake_repository, stringio, monkeypatch):
    """An invalid SPDX identifier was provided."""
    # pylint: disable=unused-argument
    monkeypatch.setattr(
        requests, "get", lambda _: MockResponse(status_code=404)
    )
    result = main(["download", "does-not-exist"], out=stringio)

    assert result == 1
    assert "Failed to download license" in stringio.getvalue()
    assert "does-not-exist is not a valid" in stringio.getvalue()


def test_download_in_licenses_dir(fake_repository, stringio, monkeypatch):
    """Put license file in current directory, if current directory is the
    LICENSES/ directory.
    """
    monkeypatch.setattr(
        requests, "get", lambda _: MockResponse("hello\n", 200)
    )
    os.chdir("LICENSES")
    result = main(["download", "0BSD"], out=stringio)

    assert result == 0
    assert (fake_repository / "LICENSES/0BSD.txt").read_text() == "hello\n"


def test_download_empty_dir(empty_directory, stringio, monkeypatch):
    """Create a LICENSES/ directory if one does not yet exist."""
    monkeypatch.setattr(
        requests, "get", lambda _: MockResponse("hello\n", 200)
    )
    result = main(["download", "0BSD"], out=stringio)

    assert result == 0
    assert (empty_directory / "LICENSES").exists()
    assert (empty_directory / "LICENSES/0BSD.txt").read_text() == "hello\n"


def test_download_git_repository(git_repository, stringio, monkeypatch):
    """Find the LICENSES/ directory in a Git repository."""
    monkeypatch.setattr(
        requests, "get", lambda _: MockResponse("hello\n", 200)
    )
    os.chdir("src")
    result = main(["download", "0BSD"], out=stringio)

    assert result == 0
    assert (git_repository / "LICENSES/0BSD.txt").read_text() == "hello\n"


def test_download_custom_output(empty_directory, stringio, monkeypatch):
    """Download the license into a custom file."""
    monkeypatch.setattr(
        requests, "get", lambda _: MockResponse("hello\n", 200)
    )
    result = main(["download", "-o", "foo", "0BSD"], out=stringio)

    assert result == 0
    assert (
        (empty_directory / "foo").read_text()
        == "Valid-License-Identifier: 0BSD\n"
        "License-Text:\n"
        "\n"
        "hello\n"
    )


def test_download_custom_exception(empty_directory, stringio, monkeypatch):
    """Download the exception into a custom file."""
    monkeypatch.setattr(
        requests, "get", lambda _: MockResponse("hello\n", 200)
    )
    result = main(
        ["download", "-o", "foo", "Autoconf-exception-3.0"], out=stringio
    )

    assert result == 0
    assert (
        (empty_directory / "foo").read_text()
        == "Valid-Exception-Identifier: Autoconf-exception-3.0\n"
        "Exception-Text:\n"
        "\n"
        "hello\n"
    )
