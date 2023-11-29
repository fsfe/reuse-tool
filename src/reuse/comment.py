# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2019 Kirill Elagin
# SPDX-FileCopyrightText: 2020 Dmitry Bogatov
# SPDX-FileCopyrightText: 2021-2022 Alliander N.V. <https://alliander.com>
# SPDX-FileCopyrightText: 2021 Alvar Penning
# SPDX-FileCopyrightText: 2021 Robin Vobruba <hoijui.quaero@gmail.com>
# SPDX-FileCopyrightText: 2021 Matija Šuklje <matija@suklje.name>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2022 Nico Rikken <nico.rikken@fsfe.org>
# SPDX-FileCopyrightText: 2022 Stefan Hynek <stefan.hynek@uni-goettingen.de>
# SPDX-FileCopyrightText: 2022 Carmen Bianca Bakker <carmenbianca@fsfe.org>
# SPDX-FileCopyrightText: 2022 Sebastian Crane <seabass@fsfe.org>
# SPDX-FileCopyrightText: 2023 Redradix S.L. <info@redradix.com>
# SPDX-FileCopyrightText: 2023 Kevin Meagher
# SPDX-FileCopyrightText: 2023 Mathias Dannesbo <md@magenta.dk>
# SPDX-FileCopyrightText: 2023 Shun Sakai <sorairolake@protonmail.ch>
# SPDX-FileCopyrightText: 2023 Juelich Supercomputing Centre, Forschungszentrum Juelich GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Module for parsing and creating comments. Just enough to deal with comment
headers, in any case.
"""

import logging
import operator
from textwrap import dedent
from typing import List, NamedTuple, Type

_LOGGER = logging.getLogger(__name__)


class CommentParseError(Exception):
    """An error occurred during the parsing of a comment."""


class CommentCreateError(Exception):
    """An error occurred during the creation of a comment."""


class MultiLineSegments(NamedTuple):
    """Components that make up a multi-line comment style, e.g. '/*', '*', and
    '*/'.
    """

    start: str
    middle: str
    end: str


class CommentStyle:
    """Base class for comment style."""

    SHORTHAND = ""
    SINGLE_LINE = ""
    INDENT_AFTER_SINGLE = ""
    # (start, middle, end)
    # e.g., ("/*", "*", "*/")
    MULTI_LINE = MultiLineSegments("", "", "")
    INDENT_BEFORE_MIDDLE = ""
    INDENT_AFTER_MIDDLE = ""
    INDENT_BEFORE_END = ""
    SHEBANGS: List[str] = []

    @classmethod
    def can_handle_single(cls) -> bool:
        """Whether the :class:`CommentStyle` can handle single-line comments."""
        return bool(cls.SINGLE_LINE)

    @classmethod
    def can_handle_multi(cls) -> bool:
        """Whether the :class:`CommentStyle` can handle multi-line comments."""
        return all((cls.MULTI_LINE.start, cls.MULTI_LINE.end))

    @classmethod
    def create_comment(cls, text: str, force_multi: bool = False) -> str:
        """Comment all lines in *text*. Single-line comments are preferred over
        multi-line comments, unless *force_multi* is provided.

        Raises:
            CommentCreateError: if *text* could not be commented.
        """
        if force_multi or not cls.can_handle_single():
            return cls._create_comment_multi(text)
        return cls._create_comment_single(text)

    @classmethod
    def _create_comment_single(cls, text: str) -> str:
        """Comment all lines in *text*, using single-line comments.

        Raises:
            CommentCreateError: if *text* could not be commented.
        """
        if not cls.can_handle_single():
            raise CommentCreateError(
                f"{cls} cannot create single-line comments"
            )
        result = []
        for line in text.split("\n"):
            line_result = cls.SINGLE_LINE
            if line:
                line_result += cls.INDENT_AFTER_SINGLE + line
            result.append(line_result)
        return "\n".join(result)

    @classmethod
    def _create_comment_multi(cls, text: str) -> str:
        """Comment all lines in *text*, using multi-line comments.

        Raises:
            CommentCreateError: if *text* could not be commented.
        """
        if not cls.can_handle_multi():
            raise CommentCreateError(f"{cls} cannot create multi-line comments")
        result = []
        result.append(cls.MULTI_LINE.start)
        for line in text.split("\n"):
            if cls.MULTI_LINE.end in text:
                raise CommentCreateError(
                    f"'{line}' contains a premature comment delimiter"
                )
            line_result = ""
            if cls.MULTI_LINE.middle:
                line_result += cls.INDENT_BEFORE_MIDDLE + cls.MULTI_LINE.middle
            if line:
                line_result += cls.INDENT_AFTER_MIDDLE + line
            result.append(line_result)
        result.append(cls.INDENT_BEFORE_END + cls.MULTI_LINE.end)
        return "\n".join(result)

    @classmethod
    def parse_comment(cls, text: str) -> str:
        """Uncomment all lines in *text*.

        Raises:
            CommentParseError: if *text* could not be parsed.
        """
        try:
            # Attempt to parse multi-line comments first, in case of comment
            # styles like Julia, where '#=' starts a multi-line comment, and '#'
            # starts a single-line comment. If we parsed single-line comments
            # first, '#=' would be a valid single-line comment.
            return cls._parse_comment_multi(text)
        except CommentParseError:
            return cls._parse_comment_single(text)

    @classmethod
    def _parse_comment_single(cls, text: str) -> str:
        """Uncomment all lines in *text*, assuming they are commented by
        single-line comments.

        Raises:
            CommentParseError: if *text* could not be parsed.
        """
        if not cls.can_handle_single():
            raise CommentParseError(f"{cls} cannot parse single-line comments")
        result_lines = []

        for line in text.splitlines():
            if not line.startswith(cls.SINGLE_LINE):
                raise CommentParseError(
                    f"'{line}' does not start with a comment marker"
                )
            line = line.lstrip(cls.SINGLE_LINE)
            result_lines.append(line)
        result = "\n".join(result_lines)
        return dedent(result)

    @classmethod
    def _remove_middle_marker(cls, line: str) -> str:
        if cls.MULTI_LINE.middle:
            possible_line = line.lstrip()
            prefix = cls.MULTI_LINE.middle
            if possible_line.startswith(prefix):
                line = possible_line.lstrip(prefix)
                # Note to future self: line.removeprefix would be preferable
                # here.
                if line.startswith(cls.INDENT_AFTER_MIDDLE):
                    line = line.replace(cls.INDENT_AFTER_MIDDLE, "", 1)
            else:
                _LOGGER.debug(
                    "'%s' does not contain a middle comment marker", line
                )
        return line

    @classmethod
    def _parse_comment_multi(cls, text: str) -> str:
        """Uncomment all lines in *text*, assuming they are commented by
        multi-line comments.

        Raises:
            CommentParseError: if *text* could not be parsed.
        """
        if not cls.can_handle_multi():
            raise CommentParseError(f"{cls} cannot parse multi-line comments")

        result_lines = []
        try:
            first, *lines, last = text.splitlines()
            last_is_first = False
        except ValueError:
            first = text
            lines = []
            last = ""  # Set this later.
            last_is_first = True

        if not first.startswith(cls.MULTI_LINE.start):
            raise CommentParseError(
                f"'{first}' does not start with a comment marker"
            )
        first = first.lstrip(cls.MULTI_LINE.start)
        first = first.lstrip()

        for line in lines:
            line = cls._remove_middle_marker(line)
            result_lines.append(line)

        if last_is_first:
            last = first
            first = ""
        if not last.endswith(cls.MULTI_LINE.end):
            raise CommentParseError(
                f"'{last}' does not end with a comment delimiter"
            )
        last = last.rstrip(cls.MULTI_LINE.end)
        last = last.rstrip()
        last = cls._remove_middle_marker(last)

        result = "\n".join(result_lines)
        result = dedent(result)

        return "\n".join(item for item in (first, result, last) if item)

    @classmethod
    def comment_at_first_character(cls, text: str) -> str:
        """Return the comment block that starts at the first character of
        *text*. This is chiefly handy to get the header comment of a file,
        assuming that the header comment starts at the first character in the
        file.

        Raises:
            CommentParseError: if *text* does not start with a parseable
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
        if cls.can_handle_multi() and text.startswith(cls.MULTI_LINE.start):
            end = 0
            for i, line in enumerate(lines):
                end = i
                if line.endswith(cls.MULTI_LINE.end):
                    break
            else:
                raise CommentParseError("Comment block never delimits")
            return "\n".join(lines[0 : end + 1])

        raise CommentParseError(
            "Could not find a parseable comment block at the first character"
        )


class AppleScriptCommentStyle(CommentStyle):
    """AppleScript comment style."""

    SHORTHAND = "applescript"

    SINGLE_LINE = "--"
    INDENT_AFTER_SINGLE = " "
    MULTI_LINE = MultiLineSegments("(*", "", "*)")


class AspxCommentStyle(CommentStyle):
    """ASPX comment style."""

    SHORTHAND = "aspx"

    MULTI_LINE = MultiLineSegments("<%--", "", "--%>")


class BatchFileCommentStyle(CommentStyle):
    """Windows batch file comment style."""

    SHORTHAND = "bat"

    SINGLE_LINE = "REM"
    INDENT_AFTER_SINGLE = " "


class BibTexCommentStyle(CommentStyle):
    """BibTex comment style."""

    SHORTHAND = "bibtex"

    MULTI_LINE = MultiLineSegments("@Comment{", "", "}")


class CCommentStyle(CommentStyle):
    """C comment style."""

    SHORTHAND = "c"

    SINGLE_LINE = "//"
    INDENT_AFTER_SINGLE = " "
    MULTI_LINE = MultiLineSegments("/*", "*", "*/")
    INDENT_BEFORE_MIDDLE = " "
    INDENT_AFTER_MIDDLE = " "
    INDENT_BEFORE_END = " "
    SHEBANGS = [
        "#!",  #  V-Lang
        "<?php",  # PHP
    ]


class CssCommentStyle(CommentStyle):
    """CSS comment style."""

    SHORTHAND = "css"

    MULTI_LINE = MultiLineSegments("/*", "*", "*/")
    INDENT_BEFORE_MIDDLE = " "
    INDENT_AFTER_MIDDLE = " "
    INDENT_BEFORE_END = " "


class EmptyCommentStyle(CommentStyle):
    """Hacky comment style for files that have no comments."""

    @classmethod
    def create_comment(cls, text: str, force_multi: bool = False) -> str:
        return text

    @classmethod
    def parse_comment(cls, text: str) -> str:
        return text

    @classmethod
    def comment_at_first_character(cls, text: str) -> str:
        return text


class FortranCommentStyle(CommentStyle):
    """Fortran (fixed form) comment style."""

    SHORTHAND = "f"

    SINGLE_LINE = "c"
    INDENT_AFTER_SINGLE = " "


class ModernFortranCommentStyle(CommentStyle):
    """Fortran (free form) comment style."""

    SHORTHAND = "f90"

    SINGLE_LINE = "!"
    INDENT_AFTER_SINGLE = " "


class FtlCommentStyle(CommentStyle):
    """FreeMarker Template Language comment style."""

    SHORTHAND = "ftl"

    MULTI_LINE = MultiLineSegments("<#--", "", "-->")


class HandlebarsCommentStyle(CommentStyle):
    """Handlebars comment style."""

    SHORTHAND = "handlebars"

    MULTI_LINE = MultiLineSegments("{{!--", "", "--}}")


class HaskellCommentStyle(CommentStyle):
    """Haskell comment style."""

    SHORTHAND = "haskell"

    SINGLE_LINE = "--"
    INDENT_AFTER_SINGLE = " "


class HtmlCommentStyle(CommentStyle):
    """HTML comment style."""

    SHORTHAND = "html"

    MULTI_LINE = MultiLineSegments("<!--", "", "-->")
    SHEBANGS = ["<?xml"]


class JinjaCommentStyle(CommentStyle):
    """Jinja2 comment style."""

    SHORTHAND = "jinja"

    MULTI_LINE = MultiLineSegments("{#", "", "#}")


class JuliaCommentStyle(CommentStyle):
    """Julia comment style."""

    SHORTHAND = "julia"

    SINGLE_LINE = "#"
    INDENT_AFTER_SINGLE = " "
    MULTI_LINE = MultiLineSegments("#=", "", "=#")
    SHEBANGS = ["#!"]


class LispCommentStyle(CommentStyle):
    """Lisp comment style."""

    SHORTHAND = "lisp"

    SINGLE_LINE = ";"
    INDENT_AFTER_SINGLE = " "


class M4CommentStyle(CommentStyle):
    """M4 (autoconf) comment style."""

    SHORTHAND = "m4"

    SINGLE_LINE = "dnl"
    INDENT_AFTER_SINGLE = " "


class MlCommentStyle(CommentStyle):
    """ML comment style."""

    SHORTHAND = "ml"

    MULTI_LINE = MultiLineSegments("(*", "*", "*)")
    INDENT_BEFORE_MIDDLE = " "
    INDENT_AFTER_MIDDLE = " "
    INDENT_BEFORE_END = " "


class PlantUmlCommentStyle(CommentStyle):
    """PlantUML comment style."""

    SHORTHAND = "plantuml"

    SINGLE_LINE = "'"
    INDENT_AFTER_SINGLE = " "
    MULTI_LINE = MultiLineSegments("/'", "'", "'/")
    INDENT_BEFORE_MIDDLE = " "
    INDENT_AFTER_MIDDLE = " "
    INDENT_BEFORE_END = " "


class PythonCommentStyle(CommentStyle):
    """Python comment style."""

    SHORTHAND = "python"

    SINGLE_LINE = "#"
    INDENT_AFTER_SINGLE = " "
    SHEBANGS = ["#!"]


class ReStructedTextCommentStyle(CommentStyle):
    """reStructuredText comment style."""

    SHORTHAND = "rst"

    SINGLE_LINE = ".."
    INDENT_AFTER_SINGLE = " "


class TexCommentStyle(CommentStyle):
    """TeX comment style."""

    SHORTHAND = "tex"

    SINGLE_LINE = "%"
    INDENT_AFTER_SINGLE = " "


class UncommentableCommentStyle(EmptyCommentStyle):
    """A pseudo comment style to indicate that this file is uncommentable. This
    results in an external .license file for binaries and --force-dot-license.
    """


class VelocityCommentStyle(CommentStyle):
    """Apache Velocity Template Language comment style."""

    SHORTHAND = "vst"

    # TODO: SINGLE_LINE requires refactor to support trailing `**`.
    MULTI_LINE = MultiLineSegments("#*", "  ", "*#")


class VimCommentStyle(CommentStyle):
    """Vim(Script|Config) style."""

    SHORTHAND = "vim"

    SINGLE_LINE = '"'
    INDENT_AFTER_SINGLE = " "


class XQueryCommentStyle(CommentStyle):
    """XQuery comment style."""

    SHORTHAND = "xquery"

    MULTI_LINE = MultiLineSegments("(:", ":", ":)")
    INDENT_BEFORE_MIDDLE = " "
    INDENT_AFTER_MIDDLE = " "
    INDENT_BEFORE_END = " "


#: A map of (common) file extensions against comment types.
EXTENSION_COMMENT_STYLE_MAP = {
    ".adb": HaskellCommentStyle,
    ".adoc": CCommentStyle,
    ".ads": HaskellCommentStyle,
    ".aes": UncommentableCommentStyle,
    ".ahk": LispCommentStyle,
    ".ahkl": LispCommentStyle,
    ".aidl": CCommentStyle,
    ".applescript": AppleScriptCommentStyle,
    ".arb": UncommentableCommentStyle,
    ".asax": AspxCommentStyle,
    ".asc": CCommentStyle,
    ".asciidoc": CCommentStyle,
    ".ashx": AspxCommentStyle,
    ".asmx": AspxCommentStyle,
    ".aspx": AspxCommentStyle,
    ".aux": TexCommentStyle,
    ".awk": PythonCommentStyle,
    ".axd": AspxCommentStyle,
    ".bash": PythonCommentStyle,
    ".bat": BatchFileCommentStyle,
    ".bb": PythonCommentStyle,
    ".bbappend": PythonCommentStyle,
    ".bbclass": PythonCommentStyle,
    ".bib": BibTexCommentStyle,
    ".bzl": PythonCommentStyle,
    ".c": CCommentStyle,
    ".cc": CCommentStyle,
    ".cjs": CCommentStyle,
    ".cl": LispCommentStyle,
    ".clj": LispCommentStyle,
    ".cljc": LispCommentStyle,
    ".cljs": LispCommentStyle,
    ".cmake": PythonCommentStyle,  # TODO: Bracket comments not supported.
    ".code-workspace": CCommentStyle,
    ".coffee": PythonCommentStyle,
    ".cpp": CCommentStyle,
    ".cs": CCommentStyle,
    ".csl": HtmlCommentStyle,  # Bibliography (XML based)
    ".css": CssCommentStyle,
    ".csv": UncommentableCommentStyle,
    ".cxx": CCommentStyle,
    ".d": CCommentStyle,
    ".dart": CCommentStyle,
    ".di": CCommentStyle,
    ".doc": UncommentableCommentStyle,
    ".docx": UncommentableCommentStyle,
    ".dotx": UncommentableCommentStyle,
    ".dts": CCommentStyle,
    ".dtsi": CCommentStyle,
    ".el": LispCommentStyle,
    ".erl": TexCommentStyle,
    ".ex": PythonCommentStyle,
    ".exs": PythonCommentStyle,
    ".f": FortranCommentStyle,
    ".f03": ModernFortranCommentStyle,
    ".f08": ModernFortranCommentStyle,
    ".f90": ModernFortranCommentStyle,
    ".f95": ModernFortranCommentStyle,
    ".fish": PythonCommentStyle,
    ".fnl": LispCommentStyle,
    ".fodp": UncommentableCommentStyle,
    ".fods": UncommentableCommentStyle,
    ".fodt": UncommentableCommentStyle,
    ".for": FortranCommentStyle,
    ".ftn": FortranCommentStyle,
    ".fpp": FortranCommentStyle,
    ".fs": CCommentStyle,
    ".ftl": FtlCommentStyle,
    ".gemspec": PythonCommentStyle,
    ".go": CCommentStyle,
    ".gradle": CCommentStyle,
    ".graphql": PythonCommentStyle,
    ".groovy": CCommentStyle,
    ".h": CCommentStyle,
    ".ha": CCommentStyle,
    ".hbs": HandlebarsCommentStyle,
    ".hcl": PythonCommentStyle,
    ".hh": CCommentStyle,
    ".hpp": CCommentStyle,
    ".hrl": TexCommentStyle,
    ".hs": HaskellCommentStyle,
    ".html": HtmlCommentStyle,
    ".hx": CCommentStyle,
    ".hxsl": CCommentStyle,
    ".ini": LispCommentStyle,
    ".ino": CCommentStyle,
    ".ipynb": UncommentableCommentStyle,
    ".iuml": PlantUmlCommentStyle,
    ".java": CCommentStyle,
    ".jinja": JinjaCommentStyle,
    ".jinja2": JinjaCommentStyle,
    ".jl": JuliaCommentStyle,
    ".jpg": UncommentableCommentStyle,
    ".jpeg": UncommentableCommentStyle,
    ".js": CCommentStyle,
    ".json": UncommentableCommentStyle,
    ".jsp": AspxCommentStyle,
    ".jsx": CCommentStyle,
    ".jy": PythonCommentStyle,
    ".ksh": PythonCommentStyle,
    ".kt": CCommentStyle,
    ".kts": CCommentStyle,
    ".l": LispCommentStyle,
    ".latex": TexCommentStyle,
    ".ld": CCommentStyle,
    ".less": CssCommentStyle,
    ".license": EmptyCommentStyle,
    ".lisp": LispCommentStyle,
    ".lsp": LispCommentStyle,
    ".lua": HaskellCommentStyle,
    ".m4": M4CommentStyle,
    ".markdown": HtmlCommentStyle,
    ".md": HtmlCommentStyle,
    ".mjs": CCommentStyle,
    ".mk": PythonCommentStyle,
    ".ml": MlCommentStyle,
    ".mli": MlCommentStyle,
    ".nim.cfg": PythonCommentStyle,  # Nim-lang build config parameters/settings
    ".nim": PythonCommentStyle,
    ".nimble": PythonCommentStyle,  # Nim-lang build config
    ".nimrod": PythonCommentStyle,
    ".nix": PythonCommentStyle,
    ".odb": UncommentableCommentStyle,
    ".odf": UncommentableCommentStyle,
    ".odg": UncommentableCommentStyle,
    ".odm": UncommentableCommentStyle,
    ".odp": UncommentableCommentStyle,
    ".ods": UncommentableCommentStyle,
    ".odt": UncommentableCommentStyle,
    ".org": PythonCommentStyle,
    ".otp": UncommentableCommentStyle,
    ".ots": UncommentableCommentStyle,
    ".ott": UncommentableCommentStyle,
    ".pdf": UncommentableCommentStyle,
    ".pem": UncommentableCommentStyle,
    ".php": CCommentStyle,
    ".php3": CCommentStyle,
    ".php4": CCommentStyle,
    ".php5": CCommentStyle,
    ".pl": PythonCommentStyle,
    ".plantuml": PlantUmlCommentStyle,
    ".png": UncommentableCommentStyle,
    ".po": PythonCommentStyle,
    ".pod": PythonCommentStyle,
    ".pot": PythonCommentStyle,
    ".ppt": UncommentableCommentStyle,
    ".pptx": UncommentableCommentStyle,
    ".pri": PythonCommentStyle,
    ".pro": PythonCommentStyle,
    ".proto": CCommentStyle,
    ".ps1": PythonCommentStyle,  # TODO: Multiline comments
    ".psm1": PythonCommentStyle,  # TODO: Multiline comments
    ".pu": PlantUmlCommentStyle,
    ".puml": PlantUmlCommentStyle,
    ".pxd": PythonCommentStyle,
    ".py": PythonCommentStyle,
    ".pyi": PythonCommentStyle,
    ".pyw": PythonCommentStyle,
    ".pyx": PythonCommentStyle,
    ".qbs": CCommentStyle,
    ".qml": CCommentStyle,
    ".qrc": UncommentableCommentStyle,
    ".qss": CssCommentStyle,
    ".R": PythonCommentStyle,
    ".rake": PythonCommentStyle,
    ".rb": PythonCommentStyle,
    ".rbw": PythonCommentStyle,
    ".rbx": PythonCommentStyle,
    ".rkt": LispCommentStyle,
    ".Rmd": HtmlCommentStyle,
    ".rs": CCommentStyle,
    ".rss": HtmlCommentStyle,
    ".rst": ReStructedTextCommentStyle,
    ".s": LispCommentStyle,
    ".sass": CssCommentStyle,
    ".sbt": CCommentStyle,
    ".sc": CCommentStyle,  # SuperCollider source file
    ".scad": CCommentStyle,
    ".scala": CCommentStyle,
    ".scm": LispCommentStyle,
    ".scpt": AppleScriptCommentStyle,
    ".scptd": AppleScriptCommentStyle,
    ".scss": CssCommentStyle,
    # SuperCollider synth definition (binary)
    ".scsyndef": UncommentableCommentStyle,
    ".sh": PythonCommentStyle,
    ".sml": MlCommentStyle,
    ".soy": CCommentStyle,
    ".sql": HaskellCommentStyle,
    ".sty": TexCommentStyle,
    ".svg": UncommentableCommentStyle,
    ".svelte": HtmlCommentStyle,
    ".swift": CCommentStyle,
    ".tcl": PythonCommentStyle,
    ".tex": TexCommentStyle,
    ".textile": HtmlCommentStyle,
    ".tf": PythonCommentStyle,
    ".tfvars": PythonCommentStyle,
    ".thy": MlCommentStyle,
    ".toc": TexCommentStyle,
    ".toml": PythonCommentStyle,
    ".ts": CCommentStyle,
    ".tsx": CCommentStyle,
    ".ttl": PythonCommentStyle,  # Turtle/RDF
    ".typ": CCommentStyle,  # typst files
    ".ui": UncommentableCommentStyle,
    ".v": CCommentStyle,  # V-Lang source code
    ".vala": CCommentStyle,
    ".vim": VimCommentStyle,
    ".vm": VelocityCommentStyle,
    ".vsh": CCommentStyle,  # V-Lang script
    ".vtl": VelocityCommentStyle,
    ".vue": HtmlCommentStyle,
    ".webp": UncommentableCommentStyle,
    ".xls": UncommentableCommentStyle,
    ".xlsx": UncommentableCommentStyle,
    ".xml": HtmlCommentStyle,
    ".xq": XQueryCommentStyle,
    ".xql": XQueryCommentStyle,
    ".xqm": XQueryCommentStyle,
    ".xqy": XQueryCommentStyle,
    ".xquery": XQueryCommentStyle,
    ".xsd": HtmlCommentStyle,
    ".xsh": PythonCommentStyle,
    ".xsl": HtmlCommentStyle,
    ".yaml": PythonCommentStyle,
    ".yml": PythonCommentStyle,
    ".zsh": PythonCommentStyle,
}

EXTENSION_COMMENT_STYLE_MAP_LOWERCASE = {
    key.lower(): value for key, value in EXTENSION_COMMENT_STYLE_MAP.items()
}

FILENAME_COMMENT_STYLE_MAP = {
    ".bashrc": PythonCommentStyle,
    ".bazelignore": PythonCommentStyle,
    ".bazelrc": PythonCommentStyle,
    ".browserslist": PythonCommentStyle,
    ".clang-format": PythonCommentStyle,
    ".coveragerc": PythonCommentStyle,
    ".dockerignore": PythonCommentStyle,
    ".editorconfig": PythonCommentStyle,
    ".empty": EmptyCommentStyle,
    ".eslintignore": PythonCommentStyle,
    ".eslintrc": UncommentableCommentStyle,
    ".gitattributes": PythonCommentStyle,
    ".gitignore": PythonCommentStyle,
    ".gitmodules": PythonCommentStyle,
    ".mailmap": PythonCommentStyle,
    ".metadata": UncommentableCommentStyle,
    ".mdlrc": PythonCommentStyle,  # Markdown-linter config
    ".npmignore": PythonCommentStyle,
    ".prettierrc": UncommentableCommentStyle,  # could either be JSON or YAML
    ".prettierignore": PythonCommentStyle,
    ".pylintrc": PythonCommentStyle,
    ".Renviron": PythonCommentStyle,
    ".Rprofile": PythonCommentStyle,
    ".shellcheckrc": PythonCommentStyle,
    ".vimrc": VimCommentStyle,
    ".yarnrc": PythonCommentStyle,
    "ansible.cfg": PythonCommentStyle,
    "archive.sctxar": UncommentableCommentStyle,  # SuperCollider global archive
    "CMakeLists.txt": PythonCommentStyle,
    "CODEOWNERS": PythonCommentStyle,
    "configure.ac": M4CommentStyle,
    "Containerfile": PythonCommentStyle,
    "Dockerfile": PythonCommentStyle,
    "Doxyfile": PythonCommentStyle,
    "Gemfile": PythonCommentStyle,
    "go.mod": CCommentStyle,
    "go.sum": UncommentableCommentStyle,
    "gradle-wrapper.properties": PythonCommentStyle,
    "gradlew": PythonCommentStyle,
    "Jenkinsfile": CCommentStyle,
    "Makefile.am": PythonCommentStyle,
    "Makefile": PythonCommentStyle,
    "MANIFEST.in": PythonCommentStyle,
    "manifest": PythonCommentStyle,  # used by cdist
    "meson.build": PythonCommentStyle,
    "meson_options.txt": PythonCommentStyle,
    "pubspec.lock": UncommentableCommentStyle,
    "pylintrc": PythonCommentStyle,
    "Rakefile": PythonCommentStyle,
    "requirements.txt": PythonCommentStyle,
    "ROOT": MlCommentStyle,
    "setup.cfg": PythonCommentStyle,
    "sonar-project.properties": PythonCommentStyle,
    "yarn.lock": UncommentableCommentStyle,
}

FILENAME_COMMENT_STYLE_MAP_LOWERCASE = {
    key.lower(): value for key, value in FILENAME_COMMENT_STYLE_MAP.items()
}


def _all_style_classes() -> List[Type[CommentStyle]]:
    """Return a list of all defined style classes, excluding the base class."""
    result = []
    for key, value in globals().items():
        if key.endswith("CommentStyle") and key != "CommentStyle":
            result.append(value)
    return sorted(result, key=operator.attrgetter("__name__"))


_result = _all_style_classes()
_result.remove(EmptyCommentStyle)
_result.remove(UncommentableCommentStyle)

#: A map of human-friendly names against style classes.
NAME_STYLE_MAP = {style.SHORTHAND: style for style in _result}
