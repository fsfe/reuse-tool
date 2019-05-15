# SPDX-Copyright: 2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Module for parsing and creating comments. Just enough to deal with comment
headers, in any case.
"""

from abc import ABC
from textwrap import dedent


class CommentParseError(Exception):
    """An error occurred during the parsing of a comment."""


class CommentStyle(ABC):
    """Base class for comment style."""

    SINGLE_LINE = None
    # (start, middle, end)
    # e.g., ("/*", "*", "*/")
    MULTI_LINE = (None, None, None)
    INDENT_BEFORE_MIDDLE = ""
    INDENT_BEFORE_END = ""

    @classmethod
    def create_comment(cls, text: str, force_multi: bool = False) -> str:
        """Comment all lines in *text*. Single-line comments are preferred over
        multi-line comments, unless *force_multi* is provided.
        """
        text = text.strip()
        if force_multi or cls.SINGLE_LINE is None:
            return cls.create_comment_multi(text)
        return cls.create_comment_single(text)

    @classmethod
    def create_comment_single(cls, text: str) -> str:
        """Comment all lines in *text*, using single-line comments."""
        text = text.strip()
        result = []
        for line in text.splitlines():
            line_result = cls.SINGLE_LINE
            if line:
                line_result += " " + line
            result.append(line_result)
        return "\n".join(result)

    @classmethod
    def create_comment_multi(cls, text: str) -> str:
        """Comment all lines in *text*, using multi-line comments."""
        text = text.strip()
        result = []
        result.append(cls.MULTI_LINE[0])
        for line in text.splitlines():
            line_result = ""
            if cls.MULTI_LINE[1]:
                line_result += cls.INDENT_BEFORE_MIDDLE + cls.MULTI_LINE[1]
            if line:
                line_result += " " + line
            result.append(line_result)
        result.append(cls.INDENT_BEFORE_END + cls.MULTI_LINE[2])
        return "\n".join(result)

    @classmethod
    def parse_comment(cls, text: str) -> str:
        """Uncomment all lines in *text*.

        :raises CommentParseError: if *text* could not be parsed.
        """
        text = text.strip()
        if cls.SINGLE_LINE is not None and text.startswith(cls.SINGLE_LINE):
            return cls.parse_comment_single(text)
        if cls.MULTI_LINE[0] is not None and text.startswith(
            cls.MULTI_LINE[0]
        ):
            return cls.parse_comment_multi(text)
        raise CommentParseError(
            "Text starts with neither a single- nor multi-line comment"
        )

    @classmethod
    def parse_comment_single(cls, text: str) -> str:
        """Uncomment all lines in *text*, assuming they are commented by
        single-line comments.

        :raises CommentParseError: if *text* could not be parsed.
        """
        text = text.strip()
        result = []
        for line in text.splitlines():
            if not line.startswith(cls.SINGLE_LINE):
                raise CommentParseError(
                    "'{}' does not start with a comment marker".format(line)
                )
            line = line.lstrip(cls.SINGLE_LINE)
            result.append(line)
        result = "\n".join(result)
        return dedent(result)

    @classmethod
    def parse_comment_multi(cls, text: str) -> str:
        """Uncomment all lines in *text*, assuming they are commented by
        multi-line comments.

        :raises CommentParseError: if *text* could not be parsed.
        """
        text = text.strip()
        # TODO
        raise CommentParseError()


class PythonCommentStyle(CommentStyle):
    """Python comment style"""

    SINGLE_LINE = "#"


class CCommentStyle(CommentStyle):
    """C comment style"""

    SINGLE_LINE = "//"
    MULTI_LINE = ("/*", "*", "*/")
    INDENT_BEFORE_MIDDLE = " "
    INDENT_BEFORE_END = " "


def create_comment(
    text: str,
    style: CommentStyle = PythonCommentStyle,
    force_multi: bool = False,
) -> str:
    """Convenience function that calls :func:`create_comment` of a given style.
    """
    return style.create_comment(text, force_multi=force_multi)


def parse_comment(
    text: str, style: CommentParseError = PythonCommentStyle
) -> str:
    """Convenience function that calls :func:`parse_comment` of a given style.
    """
    return style.parse_comment(text)
