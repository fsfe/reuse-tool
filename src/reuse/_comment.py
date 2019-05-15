# SPDX-Copyright: 2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Module for parsing and creating comments. Just enough to deal with comment
headers, in any case.
"""

from textwrap import dedent


class CommentParseError(Exception):
    """An error occurred during the parsing of a comment."""


class CommentStyle:
    """Base class for comment style."""

    SINGLE_LINE = None
    # (start, middle, end)
    # e.g., ("/*", "*", "*/")
    MULTI_LINE = (None, None, None)

    @classmethod
    def create_comment(cls, text: str) -> str:
        """Comment all lines in *text*. Single-line comments are preferred over
        multi-line comments.
        """
        text = text.strip()
        result = []
        for line in text.splitlines():
            line_result = cls.SINGLE_LINE
            if line:
                line_result += " " + line
            result.append(line_result)
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


def create_comment(text: str, style: CommentStyle = PythonCommentStyle) -> str:
    """Convenience function that calls :func:`create_comment` of a given style.
    """
    return style.create_comment(text)


def parse_comment(
    text: str, style: CommentParseError = PythonCommentStyle
) -> str:
    """Convenience function that calls :func:`parse_comment` of a given style.
    """
    return style.parse_comment(text)
