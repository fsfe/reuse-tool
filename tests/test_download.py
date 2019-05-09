# SPDX-Copyright: 2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""All tests for reuse._download"""

import pytest
import requests

from reuse.download import download_license


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
