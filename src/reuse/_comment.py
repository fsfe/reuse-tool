# SPDX-Copyright: 2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Module for parsing and creating comments. Just enough to deal with comment
headers, in any case.
"""


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
        result = ""
        for line in text.splitlines():
            result += cls.SINGLE_LINE
            if line:
                result += " " + line
            result += "\n"
        return result.strip()

    @classmethod
    def parse_comment(cls, text: str) -> str:
        """Uncomment all lines in *text*."""
        # TODO


class PythonCommentStyle(CommentStyle):
    """Python comment style"""

    SINGLE_LINE = "#"
    MULTI_LINE = (None, None, None)


def create_comment(text: str, style: CommentStyle = PythonCommentStyle) -> str:
    """Convenience function that calls :func:`create_comment` of a given style.
    """
    return style.create_comment(text)
