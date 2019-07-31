# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V.
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

    SINGLE_LINE = None
    INDENT_AFTER_SINGLE = ""
    # (start, middle, end)
    # e.g., ("/*", "*", "*/")
    MULTI_LINE = (None, None, None)
    INDENT_BEFORE_MIDDLE = ""
    INDENT_AFTER_MIDDLE = ""
    INDENT_BEFORE_END = ""

    @classmethod
    def _can_handle_single(cls):
        return cls.SINGLE_LINE is not None

    @classmethod
    def _can_handle_multi(cls):
        return all((cls.MULTI_LINE[0], cls.MULTI_LINE[2]))

    @classmethod
    def create_comment(cls, text: str, force_multi: bool = False) -> str:
        """Comment all lines in *text*. Single-line comments are preferred over
        multi-line comments, unless *force_multi* is provided.

        :raises CommentCreateError: if *text* could not be commented.
        """
        text = text.strip("\n")
        if force_multi or not cls._can_handle_single():
            return cls._create_comment_multi(text)
        return cls._create_comment_single(text)

    @classmethod
    def _create_comment_single(cls, text: str) -> str:
        """Comment all lines in *text*, using single-line comments.

        :raises CommentCreateError: if *text* could not be commented.
        """
        if not cls._can_handle_single():
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
        """Comment all lines in *text*, using multi-line comments.

        :raises CommentCreateError: if *text* could not be commented.
        """
        if not cls._can_handle_multi():
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

        try:
            return cls._parse_comment_single(text)
        except CommentParseError:
            return cls._parse_comment_multi(text)

    @classmethod
    def _parse_comment_single(cls, text: str) -> str:
        """Uncomment all lines in *text*, assuming they are commented by
        single-line comments.

        :raises CommentParseError: if *text* could not be parsed.
        """
        if not cls._can_handle_single():
            raise CommentParseError(
                "{} cannot parse single-line comments".format(cls)
            )
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
        if not cls._can_handle_multi():
            raise CommentParseError(
                "{} cannot parse multi-line comments".format(cls)
            )

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

    @classmethod
    def comment_at_first_character(cls, text: str) -> str:
        """Return the comment block that starts at the first character of
        *text*. This is chiefly handy to get the header comment of a file,
        assuming that the header comment starts at the first character in the
        file.

        :raises CommentParseError: if *text* does not start with a parseable
        comment block.
        """
        if not any((cls._can_handle_single(), cls._can_handle_multi())):
            raise CommentParseError("{} cannot parse comments".format(cls))

        lines = text.splitlines()

        if cls._can_handle_single() and text.startswith(cls.SINGLE_LINE):
            end = 0
            for i, line in enumerate(lines):
                if not line.startswith(cls.SINGLE_LINE):
                    break
                end = i
            return "\n".join(lines[0 : end + 1])
        if cls._can_handle_multi() and text.startswith(cls.MULTI_LINE[0]):
            end = 0
            for i, line in enumerate(lines):
                end = i
                if line.endswith(cls.MULTI_LINE[2]):
                    break
            else:
                raise CommentParseError("Comment block never delimits")
            return "\n".join(lines[0 : end + 1])

        raise CommentParseError(
            "Could not find a parseable comment block at the first character"
        )


class CCommentStyle(CommentStyle):
    """C comment style."""

    SINGLE_LINE = "//"
    INDENT_AFTER_SINGLE = " "
    MULTI_LINE = ("/*", "*", "*/")
    INDENT_BEFORE_MIDDLE = " "
    INDENT_AFTER_MIDDLE = " "
    INDENT_BEFORE_END = " "


class CssCommentStyle(CommentStyle):
    """CSS comment style."""

    MULTI_LINE = ("/*", "*", "*/")
    INDENT_BEFORE_MIDDLE = " "
    INDENT_AFTER_MIDDLE = " "
    INDENT_BEFORE_END = " "


class EmptyCommentStyle(CommentStyle):
    """Hacky comment style for files that have no comments."""

    @classmethod
    def create_comment(cls, text: str, force_multi: bool = False) -> str:
        return text.strip("\n")

    @classmethod
    def parse_comment(cls, text: str) -> str:
        return text.strip("\n")

    @classmethod
    def comment_at_first_character(cls, text: str) -> str:
        return text


class HaskellCommentStyle(CommentStyle):
    """Haskell comment style."""

    SINGLE_LINE = "--"
    INDENT_AFTER_SINGLE = " "


class HtmlCommentStyle(CommentStyle):
    """HTML comment style."""

    MULTI_LINE = ("<!--", None, "-->")


class LispCommentStyle(CommentStyle):
    """Lisp comment style."""

    SINGLE_LINE = ";;"
    INDENT_AFTER_SINGLE = " "


class PythonCommentStyle(CommentStyle):
    """Python comment style."""

    SINGLE_LINE = "#"
    INDENT_AFTER_SINGLE = " "


#: A map of (common) file extensions against comment types.
COMMENT_STYLE_MAP = {
    ".c": CCommentStyle,
    ".cl": LispCommentStyle,
    ".clj": LispCommentStyle,
    ".coffee": PythonCommentStyle,
    ".cpp": CCommentStyle,
    ".cs": CCommentStyle,
    ".css": CssCommentStyle,
    ".d": CCommentStyle,
    ".fs": CCommentStyle,
    ".h": CCommentStyle,
    ".hs": HaskellCommentStyle,
    ".html": HtmlCommentStyle,
    ".java": CCommentStyle,
    ".js": CCommentStyle,
    ".l": LispCommentStyle,
    ".lisp": LispCommentStyle,
    ".lsp": LispCommentStyle,
    ".lua": HaskellCommentStyle,
    ".markdown": HtmlCommentStyle,
    ".md": HtmlCommentStyle,
    ".nim": PythonCommentStyle,
    ".php": CCommentStyle,
    ".pl": PythonCommentStyle,
    ".py": PythonCommentStyle,
    ".rb": PythonCommentStyle,
    ".rs": CCommentStyle,
    ".vala": CCommentStyle,
}

#: A map of human-friendly names against style classes.
NAME_STYLE_MAP = {
    "c": CCommentStyle,
    "css": CssCommentStyle,
    "haskell": HaskellCommentStyle,
    "html": HtmlCommentStyle,
    "python": PythonCommentStyle,
}
