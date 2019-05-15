# SPDX-Copyright: 2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Module for parsing and creating comments. Just enough to deal with comment
headers, in any case.
"""

import logging
from textwrap import dedent

_LOGGER = logging.getLogger(__name__)


class CommentParseError(Exception):
    """An error occurred during the parsing of a comment."""


class CommentCreateError(Exception):
    """An error occurred during the creation of a comment."""


class CommentStyle:
    """Base class for comment style."""

    SINGLE_LINE = "#"
    INDENT_AFTER_SINGLE = " "
    # (start, middle, end)
    # e.g., ("/*", "*", "*/")
    MULTI_LINE = (None, None, None)
    INDENT_BEFORE_MIDDLE = ""
    INDENT_AFTER_MIDDLE = ""
    INDENT_BEFORE_END = ""

    @classmethod
    def create_comment(cls, text: str, force_multi: bool = False) -> str:
        """Comment all lines in *text*. Single-line comments are preferred over
        multi-line comments, unless *force_multi* is provided.
        """
        text = text.strip("\n")
        if force_multi or cls.SINGLE_LINE is None:
            return cls._create_comment_multi(text)
        return cls._create_comment_single(text)

    @classmethod
    def _create_comment_single(cls, text: str) -> str:
        """Comment all lines in *text*, using single-line comments."""
        if not cls.SINGLE_LINE:
            raise CommentCreateError(
                "{} cannot create single-line comments".format(cls)
            )

        text = text.strip("\n")
        result = []
        for line in text.splitlines():
            line_result = cls.SINGLE_LINE
            if line:
                line_result += cls.INDENT_AFTER_SINGLE + line
            result.append(line_result)
        return "\n".join(result)

    @classmethod
    def _create_comment_multi(cls, text: str) -> str:
        """Comment all lines in *text*, using multi-line comments."""
        if not all((cls.MULTI_LINE[0], cls.MULTI_LINE[2])):
            raise CommentCreateError(
                "{} cannot create multi-line comments".format(cls)
            )

        text = text.strip("\n")
        result = []
        result.append(cls.MULTI_LINE[0])
        for line in text.splitlines():
            if cls.MULTI_LINE[2] in text:
                raise CommentCreateError(
                    "'{}' contains a premature comment delimiter".format(line)
                )
            line_result = ""
            if cls.MULTI_LINE[1]:
                line_result += cls.INDENT_BEFORE_MIDDLE + cls.MULTI_LINE[1]
            if line:
                line_result += cls.INDENT_AFTER_MIDDLE + line
            result.append(line_result)
        result.append(cls.INDENT_BEFORE_END + cls.MULTI_LINE[2])
        return "\n".join(result)

    @classmethod
    def parse_comment(cls, text: str) -> str:
        """Uncomment all lines in *text*.

        :raises CommentParseError: if *text* could not be parsed.
        """
        text = text.strip("\n")
        if cls.SINGLE_LINE is not None and text.startswith(cls.SINGLE_LINE):
            return cls._parse_comment_single(text)
        if cls.MULTI_LINE[0] is not None and text.startswith(
            cls.MULTI_LINE[0]
        ):
            return cls._parse_comment_multi(text)
        raise CommentParseError(
            "Text starts with neither a single- nor multi-line comment"
        )

    @classmethod
    def _parse_comment_single(cls, text: str) -> str:
        """Uncomment all lines in *text*, assuming they are commented by
        single-line comments.

        :raises CommentParseError: if *text* could not be parsed.
        """
        text = text.strip("\n")
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
    def _parse_comment_multi(cls, text: str) -> str:
        """Uncomment all lines in *text*, assuming they are commented by
        multi-line comments.

        :raises CommentParseError: if *text* could not be parsed.
        """
        text = text.strip("\n")
        result = []
        try:
            first, *lines, last = text.splitlines()
            last_is_first = False
        except ValueError:
            first = text
            lines = []
            last = None  # Set this later.
            last_is_first = True

        if not all((cls.MULTI_LINE[0], cls.MULTI_LINE[2])):
            raise CommentParseError(
                "{} cannot parse multi-line comments".format(cls)
            )

        if not first.startswith(cls.MULTI_LINE[0]):
            raise CommentParseError(
                "'{}' does not start with a comment marker".format(first)
            )
        first = first.lstrip(cls.MULTI_LINE[0])
        first = first.strip()

        for line in lines:
            if cls.MULTI_LINE[1]:
                possible_line = line.lstrip(cls.INDENT_BEFORE_MIDDLE)
                prefix = cls.MULTI_LINE[1]
                if possible_line.startswith(prefix):
                    line = possible_line.lstrip(prefix)
                else:
                    _LOGGER.debug(
                        "'%s' does not contain a middle comment marker", line
                    )
            result.append(line)

        if last_is_first:
            last = first
            first = ""
        if not last.endswith(cls.MULTI_LINE[2]):
            raise CommentParseError(
                "'{}' does not end with a comment delimiter".format(last)
            )
        last = last.rstrip(cls.MULTI_LINE[2])
        last = last.rstrip(cls.INDENT_BEFORE_END)
        last = last.strip()
        if cls.MULTI_LINE[1] and last.startswith(cls.MULTI_LINE[1]):
            last = last.lstrip(cls.MULTI_LINE[1])
            last = last.lstrip()

        result = "\n".join(result)
        result = dedent(result)

        if result:
            result = "\n".join((first, result, last))
        else:
            result = "\n".join((first, last))
        result = result.strip("\n")
        return result


class CCommentStyle(CommentStyle):
    """C comment style"""

    SINGLE_LINE = "//"
    MULTI_LINE = ("/*", "*", "*/")
    INDENT_BEFORE_MIDDLE = " "
    INDENT_AFTER_MIDDLE = " "
    INDENT_BEFORE_END = " "


class HtmlCommentStyle(CommentStyle):
    """HTML comment style"""

    SINGLE_LINE = None
    INDENT_AFTER_SINGLE = ""
    MULTI_LINE = ("<!--", None, "-->")


def create_comment(
    text: str, force_multi: bool = False, style: CommentStyle = CommentStyle
) -> str:
    """Convenience function that calls :func:`create_comment` of a given style.
    """
    return style.create_comment(text, force_multi=force_multi)


def parse_comment(text: str, style: CommentParseError = CommentStyle) -> str:
    """Convenience function that calls :func:`parse_comment` of a given style.
    """
    return style.parse_comment(text)
