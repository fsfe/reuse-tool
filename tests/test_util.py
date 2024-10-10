# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2022 Carmen Bianca Bakker <carmenbianca@fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2022 Nico Rikken <nico.rikken@fsfe.org>
# SPDX-FileCopyrightText: 2022 Pietro Albini <pietro.albini@ferrous-systems.com>
# SPDX-FileCopyrightText: 2024 Rivos Inc.
# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for reuse._util"""

import os
from inspect import cleandoc
from io import BytesIO

import pytest
from boolean.boolean import ParseError

from reuse import _util
from reuse._util import _LICENSING

# REUSE-IgnoreStart


def test_extract_expression():
    """Parse various expressions."""
    expressions = ["GPL-3.0+", "GPL-3.0 AND CC0-1.0", "nonsense"]
    for expression in expressions:
        result = _util.extract_reuse_info(
            f"SPDX-License-Identifier: {expression}"
        )
        assert result.spdx_expressions == {_LICENSING.parse(expression)}


def test_extract_expression_from_ascii_art_frame():
    """Parse an expression from an ASCII art frame"""
    result = _util.extract_reuse_info(
        cleandoc(
            """
             /**********************************\\
             |*  SPDX-License-Identifier: MIT  *|
             \\**********************************/
            """
        )
    )
    assert result.spdx_expressions == {_LICENSING.parse("MIT")}


def test_extract_erroneous_expression():
    """Parse an incorrect expression."""
    expression = "SPDX-License-Identifier: GPL-3.0-or-later AND (MIT OR)"
    with pytest.raises(ParseError):
        _util.extract_reuse_info(expression)


def test_extract_no_info():
    """Given a string without REUSE information, return an empty ReuseInfo
    object.
    """
    result = _util.extract_reuse_info("")
    assert result == _util.ReuseInfo()


def test_extract_tab():
    """A tag followed by a tab is also valid."""
    result = _util.extract_reuse_info("SPDX-License-Identifier:\tMIT")
    assert result.spdx_expressions == {_LICENSING.parse("MIT")}


def test_extract_many_whitespace():
    """When a tag is followed by a lot of whitespace, the whitespace should be
    filtered out.
    """
    result = _util.extract_reuse_info("SPDX-License-Identifier:    MIT")
    assert result.spdx_expressions == {_LICENSING.parse("MIT")}


def test_extract_bibtex_comment():
    """A special case for BibTex comments."""
    expression = "@Comment{SPDX-License-Identifier: GPL-3.0-or-later}"
    result = _util.extract_reuse_info(expression)
    assert str(list(result.spdx_expressions)[0]) == "GPL-3.0-or-later"


def test_extract_copyright():
    """Given a file with copyright information, have it return that copyright
    information.
    """
    copyright_line = "SPDX-FileCopyrightText: 2019 Jane Doe"
    result = _util.extract_reuse_info(copyright_line)
    assert result.copyright_lines == {copyright_line}


def test_extract_copyright_duplicate():
    """When a copyright line is duplicated, only yield one."""
    copyright_line = "SPDX-FileCopyrightText: 2019 Jane Doe"
    result = _util.extract_reuse_info(
        "\n".join((copyright_line, copyright_line))
    )
    assert result.copyright_lines == {copyright_line}


def test_extract_copyright_tab():
    """A tag followed by a tab is also valid."""
    copyright_line = "SPDX-FileCopyrightText:\t2019 Jane Doe"
    result = _util.extract_reuse_info(copyright_line)
    assert result.copyright_lines == {copyright_line}


def test_extract_copyright_many_whitespace():
    """When a tag is followed by a lot of whitespace, that is also valid. The
    whitespace is not filtered out.
    """
    copyright_line = "SPDX-FileCopyrightText:    2019 Jane Doe"
    result = _util.extract_reuse_info(copyright_line)
    assert result.copyright_lines == {copyright_line}


def test_extract_copyright_variations():
    """There are multiple ways to declare copyright. All should be detected."""
    text = cleandoc(
        """
        SPDX-FileCopyrightText: 2019 spdx
        SPDX-FileCopyrightText: (C) 2019 spdx-c
        SPDX-FileCopyrightText: © 2019 spdx-symbol
        SPDX-FileCopyrightText: Copyright (C) 2019 spdx-string-c
        SPDX-FileCopyrightText: Copyright © 2019 spdx-string-symbol
        Copyright 2019 string
        Copyright (C) 2019 string-c
        Copyright © 2019 string-symbol
        © 2019 symbol
        """
    )

    result = _util.extract_reuse_info(text)
    lines = text.splitlines()
    for line in lines:
        assert line in result.copyright_lines
    assert len(lines) == len(result.copyright_lines)


def test_extract_with_ignore_block():
    """Ensure that the copyright and licensing information inside the ignore
    block is actually ignored.
    """
    text = cleandoc(
        """
        SPDX-FileCopyrightText: 2019 Jane Doe
        SPDX-License-Identifier: CC0-1.0
        REUSE-IgnoreStart
        SPDX-FileCopyrightText: 2019 John Doe
        SPDX-License-Identifier: GPL-3.0-or-later
        REUSE-IgnoreEnd
        SPDX-FileCopyrightText: 2019 Eve
        """
    )
    result = _util.extract_reuse_info(text)
    assert len(result.copyright_lines) == 2
    assert len(result.spdx_expressions) == 1


def test_extract_sameline_multiline():
    """When a copyright line is in a multi-line style comment on a single line,
    do not include the comment end pattern as part of the copyright.
    """
    text = "<!-- SPDX-FileCopyrightText: Jane Doe -->"
    result = _util.extract_reuse_info(text)
    assert len(result.copyright_lines) == 1
    assert result.copyright_lines == {"SPDX-FileCopyrightText: Jane Doe"}


def test_extract_special_endings():
    """Strip some non-comment-style endings from the end of copyright and
    licensing information.
    """
    text = cleandoc(
        """
        <tag value="Copyright 2019 Jane Doe">
        <tag value="Copyright 2019 John Doe" >
        <tag value="Copyright 2019 Joe Somebody" />
        <tag value='Copyright 2019 Alice'>
        <tag value='Copyright 2019 Bob' >
        <tag value='Copyright 2019 Eve' />
        [Copyright 2019 Ajnulo] ::
        """
    )
    result = _util.extract_reuse_info(text)
    for item in result.copyright_lines:
        assert ">" not in item
        assert "] ::" not in item


def test_extract_contributors():
    """Correctly extract SPDX-FileContributor information from text."""
    text = cleandoc(
        """
        # SPDX-FileContributor: Jane Doe
        """
    )
    result = _util.extract_reuse_info(text)
    assert result.contributor_lines == {"Jane Doe"}


def test_filter_ignore_block_with_comment_style():
    """Test that the ignore block is properly removed if start and end markers
    are in comment style.
    """
    text = cleandoc(
        """
        Relevant text
        # REUSE-IgnoreStart
        Ignored text
        # REUSE-IgnoreEnd
        Other relevant text
        """
    )
    expected = "Relevant text\n# \nOther relevant text"

    result = _util.filter_ignore_block(text)
    assert result == expected


def test_filter_ignore_block_non_comment_style():
    """Test that the ignore block is properly removed if start and end markers
    are not comment style.
    """
    text = cleandoc(
        """
        Relevant text
        REUSE-IgnoreStart
        Ignored text
        REUSE-IgnoreEnd
        Other relevant text
        """
    )
    expected = cleandoc(
        """
        Relevant text

        Other relevant text
        """
    )

    result = _util.filter_ignore_block(text)
    assert result == expected


def test_filter_ignore_block_with_ignored_information_on_same_line():
    """Test that the ignore block is properly removed if there is information to
    be ignored on the same line.
    """
    text = cleandoc(
        """
        Relevant text
        REUSE-IgnoreStart Copyright me
        Ignored text
        sdojfsdREUSE-IgnoreEnd
        Other relevant text
        """
    )
    expected = cleandoc(
        """
        Relevant text

        Other relevant text
        """
    )

    result = _util.filter_ignore_block(text)
    assert result == expected


def test_filter_ignore_block_with_relevant_information_on_same_line():
    """Test that the ignore block is properly removed if it has relevant
    information on the same line.
    """
    text = cleandoc(
        """
        Relevant textREUSE-IgnoreStart
        Ignored text
        REUSE-IgnoreEndOther relevant text
        """
    )
    expected = "Relevant textOther relevant text"

    result = _util.filter_ignore_block(text)
    assert result == expected


def test_filter_ignore_block_with_beginning_and_end_on_same_line_correct_order():  # pylint: disable=line-too-long
    """Test that the ignore block is properly removed if it has relevant
    information on the same line.
    """
    text = cleandoc(
        """
        Relevant textREUSE-IgnoreStartIgnored textREUSE-IgnoreEndOther
        relevant text
        """
    )
    expected = cleandoc(
        """
        Relevant textOther
        relevant text
        """
    )

    result = _util.filter_ignore_block(text)
    assert result == expected


def test_filter_ignore_block_with_beginning_and_end_on_same_line_wrong_order():
    """Test that the ignore block is properly removed if it has relevant
    information on the same line.
    """
    text = "Relevant textREUSE-IgnoreEndOther relevant textREUSE-IgnoreStartIgnored text"  # pylint: disable=line-too-long
    expected = "Relevant textREUSE-IgnoreEndOther relevant text"

    result = _util.filter_ignore_block(text)
    assert result == expected


def test_filter_ignore_block_without_end():
    """Test that the ignore block is properly removed if it has relevant
    information on the same line.
    """
    text = cleandoc(
        """
        Relevant text
        REUSE-IgnoreStart
        Ignored text
        Other ignored text
        """
    )
    expected = "Relevant text\n"

    result = _util.filter_ignore_block(text)
    assert result == expected


def test_filter_ignore_block_with_multiple_ignore_blocks():
    """Test that the ignore block is properly removed if it has relevant
    information on the same line.
    """
    text = cleandoc(
        """
        Relevant text
        REUSE-IgnoreStart
        Ignored text
        REUSE-IgnoreEnd
        Other relevant text
        REUSE-IgnoreStart
        Other ignored text
        REUSE-IgnoreEnd
        Even more relevant text
        """
    )
    expected = cleandoc(
        """
        Relevant text

        Other relevant text

        Even more relevant text
        """
    )

    result = _util.filter_ignore_block(text)
    assert result == expected


def test_make_copyright_line_simple():
    """Given a simple statement, make it a copyright line."""
    assert _util.make_copyright_line("hello") == "SPDX-FileCopyrightText: hello"


def test_make_copyright_line_year():
    """Given a simple statement and a year, make it a copyright line."""
    assert (
        _util.make_copyright_line("hello", year="2019")
        == "SPDX-FileCopyrightText: 2019 hello"
    )


def test_make_copyright_line_prefix_spdx():
    """Given a simple statement and prefix, make it a copyright line."""
    statement = _util.make_copyright_line("hello", copyright_prefix="spdx")
    assert statement == "SPDX-FileCopyrightText: hello"


def test_make_copyright_line_prefix_spdx_year():
    """Given a simple statement, prefix and a year, make it a copyright line."""
    statement = _util.make_copyright_line(
        "hello", year=2019, copyright_prefix="spdx"
    )
    assert statement == "SPDX-FileCopyrightText: 2019 hello"


def test_make_copyright_line_prefix_spdx_c_year():
    """Given a simple statement, prefix and a year, make it a copyright line."""
    statement = _util.make_copyright_line(
        "hello", year=2019, copyright_prefix="spdx-c"
    )
    assert statement == "SPDX-FileCopyrightText: (C) 2019 hello"


def test_make_copyright_line_prefix_spdx_symbol_year():
    """Given a simple statement, prefix and a year, make it a copyright line."""
    statement = _util.make_copyright_line(
        "hello", year=2019, copyright_prefix="spdx-symbol"
    )
    assert statement == "SPDX-FileCopyrightText: © 2019 hello"


def test_make_copyright_line_prefix_string_year():
    """Given a simple statement, prefix and a year, make it a copyright line."""
    statement = _util.make_copyright_line(
        "hello", year=2019, copyright_prefix="string"
    )
    assert statement == "Copyright 2019 hello"


def test_make_copyright_line_prefix_string_c_year():
    """Given a simple statement, prefix and a year, make it a copyright line."""
    statement = _util.make_copyright_line(
        "hello", year=2019, copyright_prefix="string-c"
    )
    assert statement == "Copyright (C) 2019 hello"


def test_make_copyright_line_prefix_spdx_string_c_year():
    """Given a simple statement, prefix and a year, make it a copyright line."""
    statement = _util.make_copyright_line(
        "hello", year=2019, copyright_prefix="spdx-string-c"
    )
    assert statement == "SPDX-FileCopyrightText: Copyright (C) 2019 hello"


def test_make_copyright_line_prefix_spdx_string_year():
    """Given a simple statement, prefix and a year, make it a copyright line."""
    statement = _util.make_copyright_line(
        "hello", year=2019, copyright_prefix="spdx-string"
    )
    assert statement == "SPDX-FileCopyrightText: Copyright 2019 hello"


def test_make_copyright_line_prefix_spdx_string_symbol_year():
    """Given a simple statement, prefix and a year, make it a copyright line."""
    statement = _util.make_copyright_line(
        "hello", year=2019, copyright_prefix="spdx-string-symbol"
    )
    assert statement == "SPDX-FileCopyrightText: Copyright © 2019 hello"


def test_make_copyright_line_prefix_string_symbol_year():
    """Given a simple statement, prefix and a year, make it a copyright line."""
    statement = _util.make_copyright_line(
        "hello", year=2019, copyright_prefix="string-symbol"
    )
    assert statement == "Copyright © 2019 hello"


def test_make_copyright_line_prefix_symbol_year():
    """Given a simple statement, prefix and a year, make it a copyright line."""
    statement = _util.make_copyright_line(
        "hello", year=2019, copyright_prefix="symbol"
    )
    assert statement == "© 2019 hello"


def test_make_copyright_line_existing_spdx_copyright():
    """Given a copyright line, do nothing."""
    value = "SPDX-FileCopyrightText: hello"
    assert _util.make_copyright_line(value) == value


def test_make_copyright_line_existing_other_copyright():
    """Given a non-SPDX copyright line, do nothing."""
    value = "© hello"
    assert _util.make_copyright_line(value) == value


def test_make_copyright_line_multine_error():
    """Given a multiline argument, expect an error."""
    with pytest.raises(RuntimeError):
        _util.make_copyright_line("hello\nworld")


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


def test_detect_line_endings_windows():
    """Given a CRLF string, detect the line endings."""
    assert _util.detect_line_endings("hello\r\nworld") == "\r\n"


def test_detect_line_endings_mac():
    """Given a CR string, detect the line endings."""
    assert _util.detect_line_endings("hello\rworld") == "\r"


def test_detect_line_endings_linux():
    """Given a LF string, detect the line endings."""
    assert _util.detect_line_endings("hello\nworld") == "\n"


def test_detect_line_endings_no_newlines():
    """Given a file without line endings, default to os.linesep."""
    assert _util.detect_line_endings("hello world") == os.linesep


# REUSE-IgnoreEnd
