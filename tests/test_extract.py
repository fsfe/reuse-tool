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

import logging
import os
import subprocess
import sys
from inspect import cleandoc
from io import BytesIO

import pytest
from conftest import RESOURCES_DIRECTORY, chardet

from reuse.copyright import (
    CopyrightNotice,
    CopyrightPrefix,
    ReuseInfo,
    SpdxExpression,
)
from reuse.exceptions import NoEncodingModuleError
from reuse.extract import (
    contains_reuse_info,
    detect_encoding,
    detect_newline,
    extract_reuse_info,
    filter_ignore_block,
    get_encoding_module,
    reuse_info_of_file,
    set_encoding_module,
)

_IGNORE_END = "REUSE-IgnoreEnd"

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
            assert result.spdx_expressions == {SpdxExpression(expression)}

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
        assert result.spdx_expressions == {SpdxExpression("MIT")}

    def test_erroneous_expression(self):
        """Parse an incorrect expression."""
        expression = "GPL-3.0-or-later AND (MIT OR)"
        text = f"SPDX-License-Identifier: {expression}"
        result = extract_reuse_info(text)
        expected_expression = SpdxExpression(expression)
        assert result.spdx_expressions == {expected_expression}
        assert not expected_expression.is_valid

    def test_no_info(self):
        """Given a string without REUSE information, return an empty ReuseInfo
        object.
        """
        result = extract_reuse_info("")
        assert result == ReuseInfo()

    def test_tab(self):
        """A tag followed by a tab is also valid."""
        result = extract_reuse_info("SPDX-License-Identifier:\tMIT")
        assert result.spdx_expressions == {SpdxExpression("MIT")}

    def test_many_whitespace(self):
        """When a tag is followed by a lot of whitespace, the whitespace should
        be filtered out.
        """
        result = extract_reuse_info("SPDX-License-Identifier:    MIT")
        assert result.spdx_expressions == {SpdxExpression("MIT")}

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


@pytest.mark.usefixtures("encoding_module")
class TestDetectEncoding:
    """Tests for detect_encoding."""

    @pytest.mark.parametrize(
        "encoding",
        [
            "utf_8",
            "utf_8_sig",
            "utf_16",
            "utf_32",
            "iso8859_1",
        ],
    )
    def test_simple(self, encoding):
        """Given some text, correctly detect the decoding."""
        text = cleandoc(
            """
            # Copyright © 1911 Émile Verhaeren

            Si nos coeurs ont brûlé en des jours exaltants
            D'une amour claire autant que haute,
            L'âge aujourd'hui nous fait lâches et indulgents
            Et paisibles devant nos fautes.

            Tu ne nous grandis plus, ô jeune volonté,
            Par ton ardeur non asservie,
            Et c'est de calme doux et de pâle bonté
            Que se colore notre vie.

            Nous sommes au couchant de ton soleil, amour,
            Et nous masquons notre faiblesse
            Avec les mots banals et les pauvres discours
            D'une vaine et lente sagesse.

            Oh ! que nous serait triste et honteux l'avenir,
            Si dans notre hiver et nos brumes
            N'éclatait point, tel un flambeau, le souvenir
            Des âmes fières que nous fûmes.
            """
        )
        encoded = text.encode(encoding)
        result = detect_encoding(encoded)
        if encoding != "iso8859_1":
            assert result == encoding
        else:
            # A special case where cp1252 is a superset of iso8859_1.
            assert result in ["iso8859_1", "cp1252"]
        assert encoded.decode(result) == text

    def test_binary(self):
        """A binary file has no encoding."""
        with open(RESOURCES_DIRECTORY / "fsfe.png", "rb") as fp:
            assert detect_encoding(fp.read()) is None

    def test_never_ascii(self):
        """When something could be encoded in ASCII, expect UTF-8 instead."""
        text = cleandoc(
            """
            Beautiful is better than ugly.
            Explicit is better than implicit.
            Simple is better than complex.
            Complex is better than complicated.
            Flat is better than nested.
            Sparse is better than dense.
            Readability counts.
            Special cases aren't special enough to break the rules.
            Although practicality beats purity.
            Errors should never pass silently.
            Unless explicitly silenced.
            In the face of ambiguity, refuse the temptation to guess.
            There should be one-- and preferably only one --obvious way to do it
            Although that way may not be obvious at first unless you're Dutch.
            Now is better than never.
            Although never is often better than *right* now.
            If the implementation is hard to explain, it's a bad idea.
            If the implementation is easy to explain, it may be a good idea.
            Namespaces are one honking great idea -- let's do more of those!
            """
        ).encode("ascii")
        assert detect_encoding(text) == "utf_8"

    def test_empty_is_utf_8(self):
        """An empty file is assumed to be encoded UTF-8."""
        assert detect_encoding(b"") == "utf_8"

    def test_encoding_no_encoding_module(self, monkeypatch):
        """This should never happen because it would fail on import, but expect
        an error if no encoding module is available.
        """
        monkeypatch.setattr("reuse.extract._ENCODING_MODULE", None)
        with pytest.raises(NoEncodingModuleError):
            detect_encoding(b"Hello, world!")


class TestReuseInfoOfFile:
    """Tests for reuse_info_of_file."""

    def test_with_ignore_block(self):
        """Ensure that the copyright and licensing information inside the ignore
        block is actually ignored.
        """
        buffer = BytesIO(
            cleandoc(
                f"""
                SPDX-FileCopyrightText: 2019 Jane Doe
                SPDX-License-Identifier: CC0-1.0
                REUSE-IgnoreStart
                SPDX-FileCopyrightText: 2019 John Doe
                SPDX-License-Identifier: GPL-3.0-or-later
                {_IGNORE_END}
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

    def test_binary(self, caplog):
        """If the file is a binary, return an empty ReuseInfo and log."""
        caplog.set_level(logging.INFO)
        path = RESOURCES_DIRECTORY / "fsfe.png"
        with path.open("rb") as fp:
            result = reuse_info_of_file(fp)
            assert result == ReuseInfo()
        assert f"'{path}' was detected as a binary file" in caplog.text

    def test_log(self, caplog, encoding_module):
        """Log the extraction to with level logging.DEBUG"""
        caplog.set_level(logging.DEBUG, logger="reuse.extract")
        buffer = BytesIO(b"# Copyright Jane Doe")
        buffer.name = "foo.py"
        reuse_info_of_file(buffer)
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "DEBUG"
        assert caplog.records[0].msg == (
            f"extracting REUSE information from 'foo.py'"
            f" (encoding 'utf_8', encoding module '{encoding_module}',"
            f" newline '\\n')"
        )

    @pytest.mark.parametrize("newline", ["\r\n", "\r", "\n"])
    def test_all_newlines(self, newline):
        """Can lint files with any newline."""
        text = cleandoc(
            """
            SPDX-FileCopyrightText: Jane Doe
            SPDX-FileCopyrightText: John Doe
            """
        ).replace("\n", newline)
        buffer = BytesIO(text.encode("utf-8"))
        result = reuse_info_of_file(buffer)
        assert result == ReuseInfo(
            copyright_notices={
                CopyrightNotice("Jane Doe"),
                CopyrightNotice("John Doe"),
            }
        )

    @pytest.mark.parametrize(
        "encoding",
        [
            "utf_8",
            "utf_8_sig",
            "utf_16",
            "utf_32",
            "iso8859_1",
        ],
    )
    def test_encodings(self, encoding):
        """Can lint files with any encoding."""
        text = cleandoc(
            """
            SPDX-FileCopyrightText: Jane Doe
            SPDX-FileCopyrightText: John Doe
            """
        )
        buffer = BytesIO(text.encode(encoding))
        result = reuse_info_of_file(buffer)
        assert result == ReuseInfo(
            copyright_notices={
                CopyrightNotice("Jane Doe"),
                CopyrightNotice("John Doe"),
            }
        )


class TestFilterIgnoreBlock:
    """Tests for filter_ignore_block."""

    def test_with_comment_style(self):
        """Test that the ignore block is properly removed if start and end
        markers are in comment style.
        """
        text = cleandoc(
            f"""
            Relevant text
            # REUSE-IgnoreStart
            Ignored text
            # {_IGNORE_END}
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
            f"""
            Relevant text
            REUSE-IgnoreStart
            Ignored text
            {_IGNORE_END}
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
            f"""
            Relevant text
            REUSE-IgnoreStart Copyright me
            Ignored text
            sdojfsd{_IGNORE_END}
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
            f"""
            Relevant textREUSE-IgnoreStart
            Ignored text
            {_IGNORE_END}Other relevant text
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
            f"""
            Relevant textREUSE-IgnoreStartIgnored text{_IGNORE_END}Other
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
        text = f"Relevant text{_IGNORE_END}Other relevant textREUSE-IgnoreStartIgnored text"  # pylint: disable=line-too-long
        expected = f"Relevant text{_IGNORE_END}Other relevant text"

        result = filter_ignore_block(text)
        assert result == (expected, True)

    def test_end_start_end(self):
        """Test that an ignore block is properly removed even if the string
        starts with an end instruction.
        """
        text = cleandoc(
            f"""
            {_IGNORE_END}
            Relevant text
            REUSE-IgnoreStart
            IgnoredText
            REUSE-IgnoreEnd
            More relevant text
            """
        )
        expected = cleandoc(
            f"""
            {_IGNORE_END}
            Relevant text

            More relevant text
            """
        )

        result = filter_ignore_block(text)
        assert result == (expected, False)

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
            f"""
            Relevant text
            REUSE-IgnoreStart
            Ignored text
            {_IGNORE_END}
            Other relevant text
            REUSE-IgnoreStart
            Other ignored text
            {_IGNORE_END}
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
        # REUSE-IgnoreStart
        expected = ""

        result = filter_ignore_block(text, in_ignore_block=True)
        assert result == (expected, False)


class TestDetectNewLine:
    """Tests for detect_newline."""

    @pytest.mark.parametrize("newline", ["\r\n", "\r", "\n"])
    @pytest.mark.parametrize(
        "encoding",
        ["utf_8", "utf_8_sig", "utf_16", "utf_16_be", "utf_32", "iso8859_1"],
    )
    def test_simple(self, newline, encoding):
        """Test whether newline is correctly spotted."""
        assert (
            detect_newline(
                f"hello{newline}world".encode(encoding), encoding=encoding
            )
            == newline
        )

    def test_no_newlines(self):
        """Given a file without line endings, default to os.linesep."""
        assert detect_newline(b"hello world") == os.linesep


class TestContainsReuseInfo:
    """Tests for contain_reuse_info."""

    @pytest.mark.parametrize(
        "text",
        [
            "SPDX-FileCopyrightText: Jane Doe",
            "SPDX-License-Identifier: MIT",
            "SPDX-FileCopyrightText: Jane Doe\nSPDX-License-Identifier: MIT",
        ],
    )
    def test_simple(self, text):
        """If a text contains a license, a copyright notice, or both, expect
        True.
        """
        assert contains_reuse_info(text)

    def test_no_info(self):
        """If there is no info, expect False."""
        assert not contains_reuse_info("Hello, world!")

    def test_ignore_block(self):
        """If the info is in an ignore block, expect False."""
        assert not contains_reuse_info(
            cleandoc(
                f"""
                REUSE-IgnoreStart
                Copyright Jane Doe
                {_IGNORE_END}
                """
            )
        )


class TestEncodingModule:
    """Tests for picking the correct encoding module."""

    def test_wrong_env(self):
        """If REUSE_ENCODING_MODULE is set to an unsupported value, exit."""
        env = os.environ.copy()
        env["REUSE_ENCODING_MODULE"] = "foo"
        result = subprocess.run(
            [sys.executable, "-c", "import reuse.extract"],
            env=env,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            check=False,
        )
        assert result.returncode != 0
        assert result.stdout.decode("utf-8").strip() == (
            "REUSE_ENCODING_MODULE must have a value in ['magic',"
            " 'charset_normalizer', 'chardet']; it has 'foo'. Aborting."
        )

    @chardet
    def test_pick_module(self):
        """If REUSE_ENCODING_MODULE is set to a correct value, correctly select
        that encoding module.
        """
        env = os.environ.copy()
        env["REUSE_ENCODING_MODULE"] = "chardet"
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import reuse.extract;"
                "print(reuse.extract._ENCODING_MODULE.__name__, end='')",
            ],
            env=env,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            check=False,
        )
        assert result.returncode == 0
        assert result.stdout == b"chardet"

    def test_get_encoding_module(self, encoding_module):
        """Test whether get_encoding_module returns the correct module."""
        assert get_encoding_module().__name__ == encoding_module

    def test_set_wrong_encoding_module_(self):
        """If setting to an unsupported module, expect an error."""
        with pytest.raises(NoEncodingModuleError):
            set_encoding_module("foo")  # type: ignore[arg-type]


# Reuse-IgnoreEnd
