# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for reuse._util"""

# pylint: disable=protected-access,invalid-name

import os
from argparse import ArgumentTypeError
from inspect import cleandoc
from io import BytesIO
from pathlib import Path

import pytest
from boolean.boolean import ParseError
from license_expression import LicenseSymbol

from reuse import _util
from reuse._util import _LICENSING

try:
    import pwd

    is_root = pwd.getpwuid(os.getuid()).pw_name == "root"
    is_posix = True
except ImportError:
    is_root = False
    is_posix = False


git = pytest.mark.skipif(not _util.GIT_EXE, reason="requires git")
no_root = pytest.mark.xfail(is_root, reason="fails when user is root")
posix = pytest.mark.skipif(not is_posix, reason="Windows not supported")


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


def test_extract_tab():
    """A tag followed by a tab is also valid."""
    result = _util.extract_spdx_info("SPDX" "-License-Identifier:\tMIT")
    assert result.spdx_expressions == {_LICENSING.parse("MIT")}


def test_extract_many_whitespace():
    """When a tag is followed by a lot of whitespace, the whitespace should be
    filtered out.
    """
    result = _util.extract_spdx_info("SPDX" "-License-Identifier:    MIT")
    assert result.spdx_expressions == {_LICENSING.parse("MIT")}


def test_extract_bibtex_comment():
    """A special case for BibTex comments."""
    expression = "@Comment{SPDX" "-License-Identifier: GPL-3.0-or-later}"
    result = _util.extract_spdx_info(expression)
    assert str(list(result.spdx_expressions)[0]) == "GPL-3.0-or-later"


def test_extract_copyright():
    """Given a file with copyright information, have it return that copyright
    information.
    """
    copyright = "SPDX" "-FileCopyrightText: 2019 Jane Doe"
    result = _util.extract_spdx_info(copyright)
    assert result.copyright_lines == {copyright}


def test_extract_copyright_duplicate():
    """When a copyright line is duplicated, only yield one."""
    copyright = "SPDX" "-FileCopyrightText: 2019 Jane Doe"
    result = _util.extract_spdx_info("\n".join((copyright, copyright)))
    assert result.copyright_lines == {copyright}


def test_extract_copyright_tab():
    """A tag followed by a tab is also valid."""
    copyright = "SPDX" "-FileCopyrightText:\t2019 Jane Doe"
    result = _util.extract_spdx_info(copyright)
    assert result.copyright_lines == {copyright}


def test_extract_copyright_many_whitespace():
    """When a tag is followed by a lot of whitespace, that is also valid. The
    whitespace is not filtered out.
    """
    copyright = "SPDX" "-FileCopyrightText:    2019 Jane Doe"
    result = _util.extract_spdx_info(copyright)
    assert result.copyright_lines == {copyright}


def test_extract_copyright_variations():
    """There are multiple ways to declare copyright. All should be detected."""
    text = cleandoc(
        """
        SPDX-FileCopyrightText: 2019 Jane Doe
        SPDX-FileCopyrightText: © 2019 Jane Doe
        © 2019 Jane Doe
        Copyright © 2019 Jane Doe
        Copyright 2019 Jane Doe
        Copyright (C) 2019 Jane Doe
        """
    )

    result = _util.extract_spdx_info(text)
    lines = text.splitlines()
    for line in lines:
        assert line in result.copyright_lines
    assert len(lines) == len(result.copyright_lines)


def test_copyright_from_dep5(copyright):
    """Verify that the glob in the dep5 file is matched."""
    result = _util._copyright_from_dep5("doc/foo.rst", copyright)
    assert LicenseSymbol("CC0-1.0") in result.spdx_expressions
    assert "2017 Mary Sue" in result.copyright_lines


def test_make_copyright_line_simple():
    """Given a simple statement, make it a copyright line."""
    assert (
        _util.make_copyright_line("hello") == "SPDX"
        "-FileCopyrightText: hello"
    )


def test_make_copyright_line_year():
    """Given a simple statement and a year, make it a copyright line."""
    assert (
        _util.make_copyright_line("hello", year="2019") == "SPDX"
        "-FileCopyrightText: 2019 hello"
    )


def test_make_copyright_line_style_spdx():
    """Given a simple statement and style, make it a copyright line."""
    statement = _util.make_copyright_line("hello", copyright_style="spdx")
    assert statement == "SPDX-FileCopyrightText: hello"


def test_make_copyright_line_style_spdx_year():
    """Given a simple statement, style and a year, make it a copyright line."""
    statement = _util.make_copyright_line(
        "hello", year=2019, copyright_style="spdx"
    )
    assert statement == "SPDX-FileCopyrightText: 2019 hello"


def test_make_copyright_line_style_string_year():
    """Given a simple statement, style and a year, make it a copyright line."""
    statement = _util.make_copyright_line(
        "hello", year=2019, copyright_style="string"
    )
    assert statement == "Copyright 2019 hello"


def test_make_copyright_line_style_string_c_year():
    """Given a simple statement, style and a year, make it a copyright line."""
    statement = _util.make_copyright_line(
        "hello", year=2019, copyright_style="string-c"
    )
    assert statement == "Copyright (C) 2019 hello"


def test_make_copyright_line_style_string_symbol_year():
    """Given a simple statement, style and a year, make it a copyright line."""
    statement = _util.make_copyright_line(
        "hello", year=2019, copyright_style="string-symbol"
    )
    assert statement == "Copyright © 2019 hello"


def test_make_copyright_line_style_symbol_year():
    """Given a simple statement, style and a year, make it a copyright line."""
    statement = _util.make_copyright_line(
        "hello", year=2019, copyright_style="symbol"
    )
    assert statement == "© 2019 hello"


def test_make_copyright_line_existing_spdx_copyright():
    """Given a copyright line, do nothing."""
    value = "SPDX" "-FileCopyrightText: hello"
    assert _util.make_copyright_line(value) == value


def test_make_copyright_line_existing_other_copyright():
    """Given a non-SPDX copyright line, do nothing."""
    value = "© hello"
    assert _util.make_copyright_line(value) == value


def test_make_copyright_line_multine_error():
    """Given a multiline arguement, expect an error."""
    with pytest.raises(RuntimeError):
        _util.make_copyright_line("hello\nworld")


# pylint: disable=unused-argument


def test_pathtype_read_simple(fake_repository):
    """Get a Path to a readable file."""
    result = _util.PathType("r")("src/source_code.py")

    assert result == Path("src/source_code.py")


def test_pathtype_read_directory(fake_repository):
    """Get a Path to a readable directory."""
    result = _util.PathType("r")("src")

    assert result == Path("src")


def test_pathtype_read_directory_force_file(fake_repository):
    """Cannot read a directory when a file is forced."""
    with pytest.raises(ArgumentTypeError):
        _util.PathType("r", force_file=True)("src")


@no_root
@posix
def test_pathtype_read_not_readable(fake_repository):
    """Cannot read a nonreadable file."""
    os.chmod("src/source_code.py", 0o000)

    with pytest.raises(ArgumentTypeError):
        _util.PathType("r")("src/source_code.py")

    os.chmod("src/source_code.py", 0o777)


def test_pathtype_read_not_exists(empty_directory):
    """Cannot read a file that does not exist."""
    with pytest.raises(ArgumentTypeError):
        _util.PathType("r")("foo.py")


def test_pathtype_write_not_exists(empty_directory):
    """Get a Path for a file that does not exist."""
    result = _util.PathType("w")("foo.py")

    assert result == Path("foo.py")


def test_pathtype_write_exists(fake_repository):
    """Get a Path for a file that exists."""
    result = _util.PathType("w")("src/source_code.py")

    assert result == Path("src/source_code.py")


def test_pathtype_write_directory(fake_repository):
    """Cannot write to directory."""
    with pytest.raises(ArgumentTypeError):
        _util.PathType("w")("src")


@no_root
@posix
def test_pathtype_write_exists_but_not_writeable(fake_repository):
    """Cannot get Path of file that exists but isn't writeable."""
    os.chmod("src/source_code.py", 0o000)

    with pytest.raises(ArgumentTypeError):
        _util.PathType("w")("src/source_code.py")

    os.chmod("src/source_code.py", 0o777)


@no_root
@posix
def test_pathtype_write_not_exist_but_directory_not_writeable(fake_repository):
    """Cannot get Path of file that does not exist but directory isn't
    writeable.
    """
    os.chmod("src", 0o000)

    with pytest.raises(ArgumentTypeError):
        _util.PathType("w")("src/foo.py")

    os.chmod("src", 0o777)


def test_pathtype_invalid_mode(empty_directory):
    """Only valid modes are 'r' and 'w'."""
    with pytest.raises(ValueError):
        _util.PathType("o")


def test_decoded_text_from_binary_simple():
    """A unicode string encoded as bytes object decodes back correctly."""
    text = "Hello, world ☺"
    encoded = text.encode("utf-8")
    assert _util.decoded_text_from_binary(BytesIO(encoded)) == text


def test_decoded_text_from_binary_size():
    """Only a given amount of bytes is decoded."""
    text = "Hello, world ☺"
    encoded = text.encode("utf-8")
    assert _util.decoded_text_from_binary(BytesIO(encoded), size=5) == "Hello"


def test_decoded_text_from_binary_crlf():
    """Given CRLF line endings, convert to LF."""
    text = "Hello\r\nworld"
    encoded = text.encode("utf-8")
    assert _util.decoded_text_from_binary(BytesIO(encoded)) == "Hello\nworld"


def test_similar_spdx_identifiers():
    """Given a misspelt SPDX License Identifier, suggest a better one."""
    result = _util.similar_spdx_identifiers("GPL-3.0-or-lter")

    assert "GPL-3.0-or-later" in result
    assert "AGPL-3.0-or-later" in result
    assert "LGPL-3.0-or-later" in result
