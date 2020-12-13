# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2019 Kirill Elagin
# SPDX-FileCopyrightText: 2020 Dmitry Bogatov
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Module for parsing and creating comments. Just enough to deal with comment
headers, in any case.
"""

import logging
import operator
from textwrap import dedent
from typing import List

_LOGGER = logging.getLogger(__name__)


class CommentParseError(Exception):
    """An error occurred during the parsing of a comment."""


class CommentCreateError(Exception):
    """An error occurred during the creation of a comment."""


class CommentStyle:
    """Base class for comment style."""

    SINGLE_LINE = ""
    INDENT_AFTER_SINGLE = ""
    # (start, middle, end)
    # e.g., ("/*", "*", "*/")
    MULTI_LINE = ("", "", "")
    INDENT_BEFORE_MIDDLE = ""
    INDENT_AFTER_MIDDLE = ""
    INDENT_BEFORE_END = ""

    @classmethod
    def can_handle_single(cls) -> bool:
        """Whether the :class:`CommentStyle` can handle single-line comments."""
        return bool(cls.SINGLE_LINE)

    @classmethod
    def can_handle_multi(cls) -> bool:
        """Whether the :class:`CommentStyle` can handle multi-line comments."""
        return all((cls.MULTI_LINE[0], cls.MULTI_LINE[2]))

    @classmethod
    def create_comment(cls, text: str, force_multi: bool = False) -> str:
        """Comment all lines in *text*. Single-line comments are preferred over
        multi-line comments, unless *force_multi* is provided.

        :raises CommentCreateError: if *text* could not be commented.
        """
        text = text.strip("\n")
        if force_multi or not cls.can_handle_single():
            return cls._create_comment_multi(text)
        return cls._create_comment_single(text)

    @classmethod
    def _create_comment_single(cls, text: str) -> str:
        """Comment all lines in *text*, using single-line comments.

        :raises CommentCreateError: if *text* could not be commented.
        """
        if not cls.can_handle_single():
            raise CommentCreateError(
                f"{cls} cannot create single-line comments"
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
        if not cls.can_handle_multi():
            raise CommentCreateError(
                f"{cls} cannot create multi-line comments"
            )
        text = text.strip("\n")
        result = []
        result.append(cls.MULTI_LINE[0])
        for line in text.splitlines():
            if cls.MULTI_LINE[2] in text:
                raise CommentCreateError(
                    f"'{line}' contains a premature comment delimiter"
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
        if not cls.can_handle_single():
            raise CommentParseError(f"{cls} cannot parse single-line comments")
        text = text.strip("\n")
        result = []

        for line in text.splitlines():
            if not line.startswith(cls.SINGLE_LINE):
                raise CommentParseError(
                    f"'{line}' does not start with a comment marker"
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
        if not cls.can_handle_multi():
            raise CommentParseError(f"{cls} cannot parse multi-line comments")

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
                f"'{first}' does not start with a comment marker"
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
                f"'{last}' does not end with a comment delimiter"
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
        if not any((cls.can_handle_single(), cls.can_handle_multi())):
            raise CommentParseError(f"{cls} cannot parse comments")

        lines = text.splitlines()

        if cls.can_handle_single() and text.startswith(cls.SINGLE_LINE):
            end = 0
            for i, line in enumerate(lines):
                if not line.startswith(cls.SINGLE_LINE):
                    break
                end = i
            return "\n".join(lines[0 : end + 1])
        if cls.can_handle_multi() and text.startswith(cls.MULTI_LINE[0]):
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


class AppleScriptCommentStyle(CommentStyle):
    """AppleScript comment style."""

    _shorthand = "applescript"

    SINGLE_LINE = "--"
    INDENT_AFTER_SINGLE = " "
    MULTI_LINE = ("(*", "", "*)")


class AspxCommentStyle(CommentStyle):
    """ASPX comment style."""

    _shorthand = "aspx"

    MULTI_LINE = ("<%--", "", "--%>")


class BatchFileCommentStyle(CommentStyle):
    """Windows batch file comment style."""

    _shorthand = "bat"

    SINGLE_LINE = "REM"
    INDENT_AFTER_SINGLE = " "


class BibTexCommentStyle(CommentStyle):
    """BibTex comment style."""

    _shorthand = "bibtex"

    MULTI_LINE = ("@Comment{", "", "}")


class CCommentStyle(CommentStyle):
    """C comment style."""

    _shorthand = "c"

    SINGLE_LINE = "//"
    INDENT_AFTER_SINGLE = " "
    MULTI_LINE = ("/*", "*", "*/")
    INDENT_BEFORE_MIDDLE = " "
    INDENT_AFTER_MIDDLE = " "
    INDENT_BEFORE_END = " "


class CssCommentStyle(CommentStyle):
    """CSS comment style."""

    _shorthand = "css"

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


class FortranCommentStyle(CommentStyle):
    """Fortran comment style."""

    _shorthand = "f"

    SINGLE_LINE = "c"
    INDENT_AFTER_SINGLE = " "


class HaskellCommentStyle(CommentStyle):
    """Haskell comment style."""

    _shorthand = "haskell"

    SINGLE_LINE = "--"
    INDENT_AFTER_SINGLE = " "


class HtmlCommentStyle(CommentStyle):
    """HTML comment style."""

    _shorthand = "html"

    MULTI_LINE = ("<!--", "", "-->")


class JinjaCommentStyle(CommentStyle):
    """Jinja2 comment style."""

    _shorthand = "jinja"

    MULTI_LINE = ("{#", "", "#}")


class JsxCommentStyle(CommentStyle):
    """JSX comment style."""

    _shorthand = "jsx"

    MULTI_LINE = ("{/*", "", "*/}")


class LispCommentStyle(CommentStyle):
    """Lisp comment style."""

    _shorthand = "lisp"

    SINGLE_LINE = ";"
    INDENT_AFTER_SINGLE = " "


class M4CommentStyle(CommentStyle):
    """M4 (autoconf) comment style."""

    _shorthand = "m4"

    SINGLE_LINE = "dnl"
    INDENT_AFTER_SINGLE = " "


class MlCommentStyle(CommentStyle):
    """ML comment style."""

    _shorthand = "ml"

    MULTI_LINE = ("(*", "*", "*)")
    INDENT_BEFORE_MIDDLE = " "
    INDENT_AFTER_MIDDLE = " "
    INDENT_BEFORE_END = " "


class PlantUmlCommentStyle(CommentStyle):
    """PlantUML comment style."""

    _shorthand = "plantuml"

    SINGLE_LINE = "'"
    INDENT_AFTER_SINGLE = " "
    MULTI_LINE = ("/'", "'", "'/")
    INDENT_BEFORE_MIDDLE = " "
    INDENT_AFTER_MIDDLE = " "
    INDENT_BEFORE_END = " "


class PythonCommentStyle(CommentStyle):
    """Python comment style."""

    _shorthand = "python"

    SINGLE_LINE = "#"
    INDENT_AFTER_SINGLE = " "


class ReStructedTextCommentStyle(CommentStyle):
    """reStructuredText comment style."""

    _shorthand = "rst"

    SINGLE_LINE = ".."
    INDENT_AFTER_SINGLE = " "


class TexCommentStyle(CommentStyle):
    """TeX comment style."""

    _shorthand = "tex"

    SINGLE_LINE = "%"
    INDENT_AFTER_SINGLE = " "


#: A map of (common) file extensions against comment types.
EXTENSION_COMMENT_STYLE_MAP = {
    ".adb": HaskellCommentStyle,
    ".ads": HaskellCommentStyle,
    ".ahk": LispCommentStyle,
    ".ahkl": LispCommentStyle,
    ".asax": AspxCommentStyle,
    ".ashx": AspxCommentStyle,
    ".asmx": AspxCommentStyle,
    ".aspx": AspxCommentStyle,
    ".aux": TexCommentStyle,
    ".awk": PythonCommentStyle,
    ".axd": AspxCommentStyle,
    ".applescript": AppleScriptCommentStyle,
    ".bash": PythonCommentStyle,
    ".bat": BatchFileCommentStyle,
    ".bib": BibTexCommentStyle,
    ".c": CCommentStyle,
    ".cl": LispCommentStyle,
    ".clj": LispCommentStyle,
    ".cljc": LispCommentStyle,
    ".cljs": LispCommentStyle,
    ".cmake": PythonCommentStyle,  # TODO: Bracket comments not supported.
    ".coffee": PythonCommentStyle,
    ".cpp": CCommentStyle,
    ".cs": CCommentStyle,
    ".css": CssCommentStyle,
    ".d": CCommentStyle,
    ".dart": CCommentStyle,
    ".di": CCommentStyle,
    ".el": LispCommentStyle,
    ".erl": TexCommentStyle,
    ".ex": PythonCommentStyle,
    ".exs": PythonCommentStyle,
    ".F": FortranCommentStyle,
    ".F90": FortranCommentStyle,
    ".f90": FortranCommentStyle,
    ".f95": FortranCommentStyle,
    ".f03": FortranCommentStyle,
    ".f": FortranCommentStyle,
    ".for": FortranCommentStyle,
    ".fish": PythonCommentStyle,
    ".fs": CCommentStyle,
    ".gemspec": PythonCommentStyle,
    ".go": CCommentStyle,
    ".gradle": CCommentStyle,
    ".groovy": CCommentStyle,
    ".h": CCommentStyle,
    ".hpp": CCommentStyle,
    ".hrl": TexCommentStyle,
    ".hs": HaskellCommentStyle,
    ".html": HtmlCommentStyle,
    ".hx": CCommentStyle,
    ".hxsl": CCommentStyle,
    ".ini": LispCommentStyle,
    ".ino": CCommentStyle,
    ".iuml": PlantUmlCommentStyle,
    ".java": CCommentStyle,
    ".jinja": JinjaCommentStyle,
    ".jinja2": JinjaCommentStyle,
    ".js": CCommentStyle,
    ".jsx": JsxCommentStyle,
    ".jy": PythonCommentStyle,
    ".ksh": PythonCommentStyle,
    ".kt": CCommentStyle,
    ".l": LispCommentStyle,
    ".latex": TexCommentStyle,
    ".license": EmptyCommentStyle,
    ".lisp": LispCommentStyle,
    ".lsp": LispCommentStyle,
    ".lua": HaskellCommentStyle,
    ".m4": M4CommentStyle,
    ".markdown": HtmlCommentStyle,
    ".md": HtmlCommentStyle,
    ".mk": PythonCommentStyle,
    ".ml": MlCommentStyle,
    ".ML": MlCommentStyle,
    ".mli": MlCommentStyle,
    ".nim": PythonCommentStyle,
    ".nimrod": PythonCommentStyle,
    ".nix": PythonCommentStyle,
    ".php": CCommentStyle,
    ".php3": CCommentStyle,
    ".php4": CCommentStyle,
    ".php5": CCommentStyle,
    ".pl": PythonCommentStyle,
    ".plantuml": PlantUmlCommentStyle,
    ".po": PythonCommentStyle,
    ".pot": PythonCommentStyle,
    ".ps1": PythonCommentStyle,  # TODO: Multiline comments
    ".psm1": PythonCommentStyle,  # TODO: Multiline comments
    ".pu": PlantUmlCommentStyle,
    ".puml": PlantUmlCommentStyle,
    ".py": PythonCommentStyle,
    ".pyi": PythonCommentStyle,
    ".pyw": PythonCommentStyle,
    ".pyx": PythonCommentStyle,
    ".pxd": PythonCommentStyle,
    ".qbs": CCommentStyle,
    ".qml": CCommentStyle,
    ".R": PythonCommentStyle,
    ".Rmd": HtmlCommentStyle,
    ".rake": PythonCommentStyle,
    ".rb": PythonCommentStyle,
    ".rbw": PythonCommentStyle,
    ".rbx": PythonCommentStyle,
    ".rs": CCommentStyle,
    ".rss": HtmlCommentStyle,
    ".rst": ReStructedTextCommentStyle,
    ".sass": CssCommentStyle,
    ".scala": PythonCommentStyle,
    ".scm": LispCommentStyle,
    ".scpt": AppleScriptCommentStyle,
    ".scptd": AppleScriptCommentStyle,
    ".scss": CssCommentStyle,
    ".sh": PythonCommentStyle,
    ".sml": MlCommentStyle,
    ".sql": HaskellCommentStyle,
    ".swift": CCommentStyle,
    ".tex": TexCommentStyle,
    ".thy": MlCommentStyle,
    ".toc": TexCommentStyle,
    ".toml": PythonCommentStyle,
    ".ts": CCommentStyle,
    ".tsx": JsxCommentStyle,
    ".vala": CCommentStyle,
    ".xml": HtmlCommentStyle,
    ".xsh": PythonCommentStyle,
    ".xsl": PythonCommentStyle,
    ".yaml": PythonCommentStyle,
    ".yml": PythonCommentStyle,
    ".zsh": PythonCommentStyle,
}

FILENAME_COMMENT_STYLE_MAP = {
    ".dockerignore": PythonCommentStyle,
    ".editorconfig": PythonCommentStyle,
    ".gitattributes": PythonCommentStyle,
    ".gitignore": PythonCommentStyle,
    ".gitmodules": PythonCommentStyle,
    ".mailmap": PythonCommentStyle,
    ".pylintrc": PythonCommentStyle,
    ".Renviron": PythonCommentStyle,
    ".Rprofile": PythonCommentStyle,
    "CMakeLists.txt": PythonCommentStyle,
    "Dockerfile": PythonCommentStyle,
    "Gemfile": PythonCommentStyle,
    "Makefile": PythonCommentStyle,
    "Makefile.am": PythonCommentStyle,
    "Manifest.in": PythonCommentStyle,
    "Rakefile": PythonCommentStyle,
    "ROOT": MlCommentStyle,
    "configure.ac": M4CommentStyle,
    "go.mod": CCommentStyle,
    "manifest": PythonCommentStyle,  # used by cdist
    "meson.build": PythonCommentStyle,
    "requirements.txt": PythonCommentStyle,
    "setup.cfg": PythonCommentStyle,
}


def _all_style_classes() -> List[CommentStyle]:
    """Return a list of all defined style classes, excluding the base class."""
    result = []
    for key, value in globals().items():
        if key.endswith("CommentStyle") and key != "CommentStyle":
            result.append(value)
    return sorted(result, key=operator.attrgetter("__name__"))


# pylint: disable=invalid-name,protected-access

_result = _all_style_classes()
_result.remove(EmptyCommentStyle)

#: A map of human-friendly names against style classes.
NAME_STYLE_MAP = {style._shorthand: style for style in _result}
