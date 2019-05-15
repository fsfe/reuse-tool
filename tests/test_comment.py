# SPDX-Copyright: 2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""All tests for reuse._comment.

A lot of SPDX tags are explicitly wrong in this module, and replaced with the
tags REUSE-Copyright and REUSE-License-Identifier. This makes it easier for the
project itself to remain REUSE compliant.
"""

from inspect import cleandoc
from textwrap import dedent

import pytest

from reuse._comment import (
    CCommentStyle,
    CommentParseError,
    CommentStyle,
    create_comment,
    parse_comment,
)


def test_create_comment_python():
    """Create a simple Python comment."""
    text = cleandoc(
        """
        REUSE-Copyright: Mary Sue

        REUSE-License-Identifier: GPL-3.0-or-later
        """
    )
    expected = cleandoc(
        """
        # REUSE-Copyright: Mary Sue
        #
        # REUSE-License-Identifier: GPL-3.0-or-later
        """
    )

    assert create_comment(text) == expected


def test_parse_comment_python():
    """Parse a simple Python comment."""
    text = cleandoc(
        """
        # REUSE-Copyright: Mary Sue
        #
        # REUSE-License-Identifier: GPL-3.0-or-later
        """
    )
    expected = cleandoc(
        """
        REUSE-Copyright: Mary Sue

        REUSE-License-Identifier: GPL-3.0-or-later
        """
    )

    assert parse_comment(text) == expected


def test_parse_comment_python_indented():
    """Preserve indentations in Python comments."""
    text = cleandoc(
        """
        # def foo():
        #     print("foo")
        """
    )
    expected = cleandoc(
        """
        def foo():
            print("foo")
        """
    )

    assert parse_comment(text) == expected


def test_create_comment_python_strip_newlines():
    """Don't include unnecessary newlines in the comment."""
    text = "\nhello\n"
    expected = "# hello"

    assert create_comment(text) == expected


def test_parse_comment_python_strip_newlines():
    """When given a comment, remove newlines before and after before parsing.
    """
    text = dedent(
        """

        #
        # hello
        #

        """
    )
    expected = "\nhello\n"

    assert parse_comment(text) == expected


def test_parse_comment_python_not_a_comment():
    """Raise CommentParseError when a comment isn't provided."""
    text = "Hello world"

    with pytest.raises(CommentParseError):
        parse_comment(text)


def test_parse_comment_python_single_line_is_not_comment():
    """Raise CommentParseError when a single line is not a comment."""
    text = cleandoc(
        """
        # Hello
        world
        """
    )

    with pytest.raises(CommentParseError):
        parse_comment(text)


def test_parse_comment_python_multi_error():
    """Raise CommentParseError when trying to parse a multi-line Python
    comment.
    """
    with pytest.raises(CommentParseError):
        CommentStyle.parse_comment_multi("Hello world")


def test_create_comment_c_single():
    """Create a C comment with single-line comments."""
    text = cleandoc(
        """
        Hello
        world
        """
    )
    expected = cleandoc(
        """
        // Hello
        // world
        """
    )

    assert create_comment(text, style=CCommentStyle) == expected


def test_parse_comment_c_single():
    """Parse a C comment with single-line comments."""
    text = cleandoc(
        """
        // Hello
        // world
        """
    )
    expected = cleandoc(
        """
        Hello
        world
        """
    )

    assert parse_comment(text, style=CCommentStyle) == expected


def test_create_comment_c_multi():
    """Create a C comment with multi-line comments."""
    text = cleandoc(
        """
        Hello
        world
        """
    )
    expected = cleandoc(
        """
        /*
         * Hello
         * world
         */
        """
    )

    assert (
        create_comment(text, style=CCommentStyle, force_multi=True) == expected
    )


def test_parse_comment_c_multi():
    """Parse a C comment with multi-line comments."""
    text = cleandoc(
        """
        /*
         * Hello
         * world
         */
        """
    )
    expected = cleandoc(
        """
        Hello
        world
        """
    )
    assert parse_comment(text, style=CCommentStyle) == expected


def test_parse_comment_c_multi_missing_middle():
    """Parse a C comment even though the middle markers are missing."""
    text = cleandoc(
        """
        /*
        Hello
        world
        */
        """
    )
    expected = cleandoc(
        """
        Hello
        world
        """
    )

    assert parse_comment(text, style=CCommentStyle) == expected


def test_parse_comment_c_multi_misaligned_end():
    """Parse a C comment even though the end is misaligned."""
    text = cleandoc(
        """
        /*
         * Hello
         * world
        */
        """
    )
    expected = cleandoc(
        """
        Hello
        world
        """
    )

    assert parse_comment(text, style=CCommentStyle) == expected

    text = cleandoc(
        """
        /*
         * Hello
         * world
          */
        """
    )
    expected = cleandoc(
        """
        Hello
        world
        """
    )

    assert parse_comment(text, style=CCommentStyle) == expected


def test_parse_comment_c_multi_no_middle():
    """Parse a C comment that has no middle whatsoever."""
    text = cleandoc(
        """
        /* Hello
         * world */
        """
    )
    expected = cleandoc(
        """
        Hello
        world
        """
    )

    assert parse_comment(text, style=CCommentStyle) == expected


def test_parse_comment_c_multi_ends_at_last():
    """Parse a C comment that treats the last line like a regular line."""
    text = cleandoc(
        """
        /*
         * Hello
         * world */
        """
    )
    expected = cleandoc(
        """
        Hello
        world
        """
    )

    assert parse_comment(text, style=CCommentStyle) == expected


def test_parse_comment_c_multi_starts_at_first():
    """Parse a C comment that treats the first line like a regular line."""
    text = cleandoc(
        """
        /* Hello
         * world
         */
        """
    )
    expected = cleandoc(
        """
        Hello
        world
        """
    )

    assert parse_comment(text, style=CCommentStyle) == expected


def test_parse_comment_c_multi_indented():
    """Preserve indentations in C comments."""
    text = cleandoc(
        """
        /*
         * Hello
         *   world
         */
        """
    )
    expected = cleandoc(
        """
        Hello
          world
        """
    )

    assert parse_comment(text, style=CCommentStyle) == expected


def test_parse_comment_c_multi_single_line():
    """Parse a single-line multi-line comment."""
    text = "/* Hello world */"
    expected = "Hello world"

    assert parse_comment(text, style=CCommentStyle) == expected


def test_parse_comment_c_multi_no_start():
    """Raise CommentParseError when there is no comment starter."""
    text = "Hello world */"

    with pytest.raises(CommentParseError):
        parse_comment(text, style=CCommentStyle)

    with pytest.raises(CommentParseError):
        CCommentStyle.parse_comment_multi(text)


def test_parse_comment_c_multi_no_end():
    """Raise CommentParseError when there is no comment end."""
    text = "/* Hello world"

    with pytest.raises(CommentParseError):
        parse_comment(text, style=CCommentStyle)
