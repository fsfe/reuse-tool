# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2022 Carmen Bianca Bakker <carmenbianca@fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2022 Nico Rikken <nico.rikken@fsfe.org>
# SPDX-FileCopyrightText: 2022 Pietro Albini <pietro.albini@ferrous-systems.com>
# SPDX-FileCopyrightText: 2024 Rivos Inc.
# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for reuse.extract"""

import os
from inspect import cleandoc
from io import BytesIO

import pytest
from boolean.boolean import ParseError

from reuse import _LICENSING
from reuse.copyright import CopyrightNotice, CopyrightPrefix, ReuseInfo
from reuse.extract import (
    detect_line_endings,
    extract_reuse_info,
    filter_ignore_block,
    reuse_info_of_file,
)

# REUSE-IgnoreStart


class TestExtractReuseInfo:
    """Tests for extract_reuse_info."""

    def test_expression(self):
        """Parse various expressions."""
        expressions = ["GPL-3.0+", "GPL-3.0 AND CC0-1.0", "nonsense"]
        for expression in expressions:
            result = extract_reuse_info(
                f"SPDX-License-Identifier: {expression}"
            )
            assert result.spdx_expressions == {_LICENSING.parse(expression)}

    def test_expression_from_ascii_art_frame(self):
        """Parse an expression from an ASCII art frame"""
        result = extract_reuse_info(
            cleandoc(
                """
                 /**********************************\\
                 |*  SPDX-License-Identifier: MIT  *|
                 \\**********************************/
                """
            )
        )
        assert result.spdx_expressions == {_LICENSING.parse("MIT")}

    def test_erroneous_expression(self):
        """Parse an incorrect expression."""
        expression = "SPDX-License-Identifier: GPL-3.0-or-later AND (MIT OR)"
        with pytest.raises(ParseError):
            extract_reuse_info(expression)

    def test_no_info(self):
        """Given a string without REUSE information, return an empty ReuseInfo
        object.
        """
        result = extract_reuse_info("")
        assert result == ReuseInfo()

    def test_tab(self):
        """A tag followed by a tab is also valid."""
        result = extract_reuse_info("SPDX-License-Identifier:\tMIT")
        assert result.spdx_expressions == {_LICENSING.parse("MIT")}

    def test_many_whitespace(self):
        """When a tag is followed by a lot of whitespace, the whitespace should
        be filtered out.
        """
        result = extract_reuse_info("SPDX-License-Identifier:    MIT")
        assert result.spdx_expressions == {_LICENSING.parse("MIT")}

    def test_bibtex_comment(self):
        """A special case for BibTex comments."""
        expression = "@Comment{SPDX-License-Identifier: GPL-3.0-or-later}"
        result = extract_reuse_info(expression)
        assert str(list(result.spdx_expressions)[0]) == "GPL-3.0-or-later"

    def test_copyright(self):
        """Given a file with copyright information, have it return that
        copyright information.
        """
        notice = "SPDX-FileCopyrightText: 2019 Jane Doe"
        result = extract_reuse_info(notice)
        assert result.copyright_notices == {CopyrightNotice.from_string(notice)}

    def test_copyright_duplicate(self):
        """When a copyright line is duplicated, only yield one."""
        notice = "SPDX-FileCopyrightText: 2019 Jane Doe"
        result = extract_reuse_info("\n".join((notice, notice)))
        assert result.copyright_notices == {CopyrightNotice.from_string(notice)}

    def test_copyright_tab(self):
        """A tag followed by a tab is also valid."""
        notice = "SPDX-FileCopyrightText:\t2019 Jane Doe"
        result = extract_reuse_info(notice)
        assert result.copyright_notices == {CopyrightNotice.from_string(notice)}

    def test_copyright_many_whitespace(self):
        """When a tag is followed by a lot of whitespace, that is also valid.
        The whitespace is not filtered out.
        """
        notice = "SPDX-FileCopyrightText:    2019 Jane Doe"
        result = extract_reuse_info(notice)
        assert result.copyright_notices == {CopyrightNotice.from_string(notice)}

    def test_copyright_variations(self):
        """There are multiple ways to declare copyright. All should be
        detected.
        """
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

        result = extract_reuse_info(text)
        lines = text.splitlines()
        for line in lines:
            assert CopyrightNotice.from_string(line) in result.copyright_notices
        assert len(lines) == len(result.copyright_notices)

    def test_sameline_multiline(self):
        """When a copyright line is in a multi-line style comment on a single
        line, do not include the comment end pattern as part of the copyright.
        """
        text = "<!-- SPDX-FileCopyrightText: Jane Doe -->"
        result = extract_reuse_info(text)
        assert len(result.copyright_notices) == 1
        assert result.copyright_notices == {
            CopyrightNotice.from_string("SPDX-FileCopyrightText: Jane Doe")
        }

    def test_special_endings(self):
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
        result = extract_reuse_info(text)
        for item in result.copyright_notices:
            assert ">" not in str(item)
            assert "] ::" not in str(item)

    def test_special_ending_with_spacing_after(self):
        """Strip spacing after a special ending."""
        text = "<tag value='Copyright 2019 Jane Doe'> \t"
        result = extract_reuse_info(text)
        assert result.copyright_notices == {
            CopyrightNotice.from_string("Copyright 2019 Jane Doe")
        }

    def test_contributors(self):
        """Correctly extract SPDX-FileContributor information from text."""
        text = cleandoc(
            """
            # SPDX-FileContributor: Jane Doe
            """
        )
        result = extract_reuse_info(text)
        assert result.contributor_lines == {"Jane Doe"}


class TestReuseInfoOfFile:
    """Tests for reuse_info_of_file."""

    def test_with_ignore_block(self):
        """Ensure that the copyright and licensing information inside the ignore
        block is actually ignored.
        """
        buffer = BytesIO(
            cleandoc(
                """
                SPDX-FileCopyrightText: 2019 Jane Doe
                SPDX-License-Identifier: CC0-1.0
                REUSE-IgnoreStart
                SPDX-FileCopyrightText: 2019 John Doe
                SPDX-License-Identifier: GPL-3.0-or-later
                REUSE-IgnoreEnd
                SPDX-FileCopyrightText: 2019 Eve
                """
            ).encode("utf-8")
        )
        result = reuse_info_of_file(buffer, chunk_size=10)
        assert len(result.copyright_notices) == 2
        assert len(result.spdx_expressions) == 1

    def test_different_buffer(self):
        """Even with a very small buffer, the entire file is correctly read and
        parsed.
        """
        buffer = BytesIO(
            cleandoc(
                """
                SPDX-FileCopyrightText: 2019 Jane Doe
                SPDX-FileCopyrightText: 2019 John Doe
                SPDX-FileCopyrightText: 2019 Eve
                SPDX-License-Identifier: GPL-3.0-or-later
                SPDX-License-Identifier: CC0-1.0
                """
            ).encode("utf-8")
        )
        result = reuse_info_of_file(buffer, chunk_size=5, line_size=50)
        assert len(result.copyright_notices) == 3
        assert len(result.spdx_expressions) == 2

    def test_too_small_line_size(self):
        """If the line is too long (or line_size too small), then some lines
        won't be correctly parsed.
        """
        buffer = BytesIO(b"Copyright Jane Doe")
        result = reuse_info_of_file(buffer, chunk_size=10, line_size=4)
        assert result.copyright_notices == {
            CopyrightNotice("Jane", prefix=CopyrightPrefix.STRING)
        }


class TestFilterIgnoreBlock:
    """Tests for filter_ignore_block."""

    def test_with_comment_style(self):
        """Test that the ignore block is properly removed if start and end
        markers are in comment style.
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

        result = filter_ignore_block(text)
        assert result == (expected, False)

    def test_non_comment_style(self):
        """Test that the ignore block is properly removed if start and end
        markers are not comment style.
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

        result = filter_ignore_block(text)
        assert result == (expected, False)

    def test_with_ignored_information_on_same_line(self):
        """Test that the ignore block is properly removed if there is
        information to be ignored on the same line.
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

        result = filter_ignore_block(text)
        assert result == (expected, False)

    def test_with_relevant_information_on_same_line(self):
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

        result = filter_ignore_block(text)
        assert result == (expected, False)

    def test_with_beginning_and_end_on_same_line_correct_order(
        self,
    ):
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

        result = filter_ignore_block(text)
        assert result == (expected, False)

    def test_with_beginning_and_end_on_same_line_wrong_order(self):
        """Test that the ignore block is properly removed if it has relevant
        information on the same line.
        """
        text = "Relevant textREUSE-IgnoreEndOther relevant textREUSE-IgnoreStartIgnored text"  # pylint: disable=line-too-long
        expected = "Relevant textREUSE-IgnoreEndOther relevant text"

        result = filter_ignore_block(text)
        assert result == (expected, True)

    def test_without_end(self):
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

        result = filter_ignore_block(text)
        assert result == (expected, True)

    def test_with_multiple_ignore_blocks(self):
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

        result = filter_ignore_block(text)
        assert result == (expected, False)

    def test_only_start(self):
        """If the only thing in the string is 'REUSE-IgnoreStart', correctly set
        *in_ignore_block*.
        """
        text = "REUSE-IgnoreStart"
        expected = ""

        result = filter_ignore_block(text)
        assert result == (expected, True)

    def test_only_end(self):
        """If the only thing in the string is 'REUSE-IgnoreEnd', correctly set
        *in_ignore_block*.
        """
        text = "REUSE-IgnoreEnd"
        expected = ""

        result = filter_ignore_block(text, in_ignore_block=True)
        assert result == (expected, False)


def test_detect_line_endings_windows():
    """Given a CRLF string, detect the line endings."""
    assert detect_line_endings("hello\r\nworld") == "\r\n"


def test_detect_line_endings_mac():
    """Given a CR string, detect the line endings."""
    assert detect_line_endings("hello\rworld") == "\r"


def test_detect_line_endings_linux():
    """Given a LF string, detect the line endings."""
    assert detect_line_endings("hello\nworld") == "\n"


def test_detect_line_endings_no_newlines():
    """Given a file without line endings, default to os.linesep."""
    assert detect_line_endings("hello world") == os.linesep


# Reuse-IgnoreEnd
