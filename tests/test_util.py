# SPDX-Copyright: 2017-2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for reuse._util"""

# pylint: disable=protected-access

import os
from pathlib import Path

import pytest
from boolean.boolean import ParseError
from license_expression import LicenseSymbol

from reuse import _util
from reuse._util import _LICENSING

# pylint: disable=invalid-name
git = pytest.mark.skipif(not _util.GIT_EXE, reason="requires git")


def test_extract_expression():
    """Parse various expressions."""
    expressions = ["GPL-3.0+", "GPL-3.0 AND CC0-1.0", "nonsense"]
    for expression in expressions:
        result = _util.extract_spdx_info(
            "SPDX" "-License-Identifier: {}".format(expression)
        )
        assert result.spdx_expressions == {_LICENSING.parse(expression)}


def test_extract_erroneous_expression():
    """Parse an incorrect expression."""
    expression = "SPDX" "-License-Identifier: GPL-3.0-or-later AND (MIT OR)"
    with pytest.raises(ParseError):
        _util.extract_spdx_info(expression)


def test_extract_no_info():
    """Given a file without SPDX information, return an empty SpdxInfo
    object.
    """
    result = _util.extract_spdx_info("")
    assert result == _util.SpdxInfo(set(), set())


def test_extract_copyright():
    """Given a file with copyright information, have it return that copyright
    information.
    """
    copyright = "2019 Jane Doe"
    result = _util.extract_spdx_info("SPDX-Copyright: {}".format(copyright))
    assert result.copyright_lines == {copyright}


def test_extract_copyright_duplicate():
    """When a copyright line is duplicated, only yield one."""
    copyright = "2019 Jane Doe"
    result = _util.extract_spdx_info(
        "SPDX-Copyright: {}\n".format(copyright) * 2
    )
    assert result.copyright_lines == {copyright}


def test_extract_valid_license():
    """Correctly extract valid license identifier tag from file."""
    text = "Valid-License-Identifier: MIT"
    result = _util.extract_valid_license(text)
    assert result == {"MIT"}


def test_copyright_from_dep5(copyright):
    """Verify that the glob in the dep5 file is matched."""
    result = _util._copyright_from_dep5("doc/foo.rst", copyright)
    assert LicenseSymbol("CC0-1.0") in result.spdx_expressions
    assert "2017 Mary Sue" in result.copyright_lines


@git
def test_find_root_in_git_repo(git_repository):
    """When using reuse from a child directory in a Git repo, always find the
    root directory.
    """
    os.chdir("src")
    result = _util.find_root()

    assert Path(result).absolute().resolve() == git_repository
