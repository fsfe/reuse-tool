# SPDX-Copyright: 2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""All tests for reuse.download"""

import os
from pathlib import Path

import pytest
import requests

from reuse.download import download_license, put_license_in_file


class MockResponse:
    """Super simple mocked version of Response."""

    # pylint: disable=too-few-public-methods

    def __init__(self, text=None, status_code=None):
        self.text = text
        self.status_code = status_code


def test_download(monkeypatch):
    """A straightforward test: Request license text, get license text."""
    monkeypatch.setattr(requests, "get", lambda _: MockResponse("hello", 200))
    result = download_license("0BSD")
    assert result == "hello"


def test_download_404(monkeypatch):
    """If the server returns a 404, there is no license text."""
    monkeypatch.setattr(
        requests, "get", lambda _: MockResponse(status_code=404)
    )
    with pytest.raises(requests.RequestException):
        download_license("does-not-exist")


def test_download_exception(monkeypatch):
    """If requests raises an exception itself, that exception is not escaped.
    """

    def raise_exception(_):
        raise requests.RequestException()

    monkeypatch.setattr(requests, "get", raise_exception)
    with pytest.raises(requests.RequestException):
        download_license("hello world")


def test_put_simple(fake_repository, monkeypatch):
    """Straightforward test."""
    monkeypatch.setattr(
        requests, "get", lambda _: MockResponse("hello\n", 200)
    )
    put_license_in_file("0BSD")

    assert (fake_repository / "LICENSES/0BSD.txt").read_text() == "hello\n"


def test_put_file_exists(fake_repository, monkeypatch):
    """The to-be-downloaded file already exists."""
    # pylint: disable=unused-argument
    monkeypatch.setattr(
        requests, "get", lambda _: MockResponse("hello\n", 200)
    )

    with pytest.raises(FileExistsError) as exc_info:
        put_license_in_file("GPL-3.0-or-later")
    assert Path(exc_info.value.filename).name == "GPL-3.0-or-later.txt"


def test_put_request_exception(fake_repository, monkeypatch):
    """There was an error while downloading the license file."""
    # pylint: disable=unused-argument
    monkeypatch.setattr(
        requests, "get", lambda _: MockResponse(status_code=404)
    )

    with pytest.raises(requests.RequestException):
        put_license_in_file("0BSD")


def test_put_in_licenses_dir(fake_repository, monkeypatch):
    """Put license file in current directory, if current directory is the
    LICENSES/ directory.
    """
    monkeypatch.setattr(
        requests, "get", lambda _: MockResponse("hello\n", 200)
    )
    os.chdir("LICENSES")
    put_license_in_file("0BSD")

    assert (fake_repository / "LICENSES/0BSD.txt").read_text() == "hello\n"


def test_put_empty_dir(empty_directory, monkeypatch):
    """Create a LICENSES/ directory if one does not yet exist."""
    monkeypatch.setattr(
        requests, "get", lambda _: MockResponse("hello\n", 200)
    )
    put_license_in_file("0BSD")

    assert (empty_directory / "LICENSES").exists()
    assert (empty_directory / "LICENSES/0BSD.txt").read_text() == "hello\n"


def test_put_git_repository(git_repository, monkeypatch):
    """Find the LICENSES/ directory in a Git repository."""
    monkeypatch.setattr(
        requests, "get", lambda _: MockResponse("hello\n", 200)
    )
    os.chdir("src")
    put_license_in_file("0BSD")

    assert (git_repository / "LICENSES/0BSD.txt").read_text() == "hello\n"


def test_put_custom_output(empty_directory, monkeypatch):
    """Download the license into a custom file."""
    monkeypatch.setattr(
        requests, "get", lambda _: MockResponse("hello\n", 200)
    )
    put_license_in_file("0BSD", destination="foo")

    assert (empty_directory / "foo").read_text() == "hello\n"
