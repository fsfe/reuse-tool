# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2020 Tuomas Siipola <tuomas@zpl.fi>
# SPDX-FileCopyrightText: 2022 Carmen Bianca Bakker <carmenbianca@fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2022 Nico Rikken <nico.rikken@fsfe.org>
# SPDX-FileCopyrightText: 2022 Pietro Albini <pietro.albini@ferrous-systems.com>
# SPDX-FileCopyrightText: 2023 DB Systel GmbH
# SPDX-FileCopyrightText: 2023 Johannes Zarl-Zierl <johannes@zarl-zierl.at>
# SPDX-FileCopyrightText: 2024 Rivos Inc.
# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Misc. utilities for reuse."""


import logging
import os
import re
import shutil
import subprocess
import sys
from argparse import ArgumentTypeError
from collections import Counter
from difflib import SequenceMatcher
from gettext import gettext as _
from hashlib import sha1
from inspect import cleandoc
from itertools import chain
from os import PathLike
from pathlib import Path
from typing import (
    IO,
    Any,
    BinaryIO,
    Dict,
    Iterator,
    List,
    Optional,
    Set,
    Type,
    Union,
    cast,
)

from boolean.boolean import Expression, ParseError
from license_expression import ExpressionError, Licensing

from . import ReuseInfo, SourceType
from ._licenses import ALL_NON_DEPRECATED_MAP
from .comment import (
    EXTENSION_COMMENT_STYLE_MAP_LOWERCASE,
    FILENAME_COMMENT_STYLE_MAP_LOWERCASE,
    CommentStyle,
    UncommentableCommentStyle,
    _all_style_classes,
)

# TODO: When removing Python 3.8 support, use PathLike[str]
StrPath = Union[str, PathLike]

GIT_EXE = shutil.which("git")
HG_EXE = shutil.which("hg")
PIJUL_EXE = shutil.which("pijul")

REUSE_IGNORE_START = "REUSE-IgnoreStart"
REUSE_IGNORE_END = "REUSE-IgnoreEnd"

SPDX_SNIPPET_INDICATOR = b"SPDX-SnippetBegin"

_LOGGER = logging.getLogger(__name__)
_LICENSING = Licensing()

# REUSE-IgnoreStart

_END_PATTERN = r"{}$".format(
    "".join(
        {
            r"(?:{})*".format(item)  # pylint: disable=consider-using-f-string
            for item in chain(
                (
                    re.escape(style.MULTI_LINE.end)
                    for style in _all_style_classes()
                    if style.MULTI_LINE.end
                ),
                # These are special endings which do not belong to specific
                # comment styles, but which we want to nonetheless strip away
                # while parsing.
                (
                    ending
                    for ending in [
                        # ex: <tag value="Copyright Jane Doe">
                        r'"\s*/*>',
                        r"'\s*/*>",
                        # ex: [SPDX-License-Identifier: GPL-3.0-or-later] ::
                        r"\]\s*::",
                    ]
                ),
            )
        }
    )
)
_LICENSE_IDENTIFIER_PATTERN = re.compile(
    r"^(.*?)SPDX-License-Identifier:[ \t]+(.*?)" + _END_PATTERN, re.MULTILINE
)
_CONTRIBUTOR_PATTERN = re.compile(
    r"^(.*?)SPDX-FileContributor:[ \t]+(.*?)" + _END_PATTERN, re.MULTILINE
)
# The keys match the relevant attributes of ReuseInfo.
_SPDX_TAGS: Dict[str, re.Pattern] = {
    "spdx_expressions": _LICENSE_IDENTIFIER_PATTERN,
    "contributor_lines": _CONTRIBUTOR_PATTERN,
}

_COPYRIGHT_PATTERNS = [
    re.compile(
        r"(?P<copyright>(?P<prefix>SPDX-(File|Snippet)CopyrightText:)\s+"
        r"((?P<year>\d{4} ?- ?\d{4}|\d{4}),?\s+)?"
        r"(?P<statement>.*?))" + _END_PATTERN
    ),
    re.compile(
        r"(?P<copyright>(?P<prefix>Copyright(\s?\([cC]\))?)\s+"
        r"((?P<year>\d{4} ?- ?\d{4}|\d{4}),?\s+)?"
        r"(?P<statement>.*?))" + _END_PATTERN
    ),
    re.compile(
        r"(?P<copyright>(?P<prefix>©)\s+"
        r"((?P<year>\d{4} ?- ?\d{4}|\d{4}),?\s+)?"
        r"(?P<statement>.*?))" + _END_PATTERN
    ),
]
_COPYRIGHT_PREFIXES = {
    "spdx": "SPDX-FileCopyrightText:",
    "spdx-c": "SPDX-FileCopyrightText: (C)",
    "spdx-symbol": "SPDX-FileCopyrightText: ©",
    "string": "Copyright",
    "string-c": "Copyright (C)",
    "string-symbol": "Copyright ©",
    "symbol": "©",
}

_LICENSEREF_PATTERN = re.compile("LicenseRef-[a-zA-Z0-9-.]+$")

# Amount of bytes that we assume will be big enough to contain the entire
# comment header (including SPDX tags), so that we don't need to read the
# entire file.
_HEADER_BYTES = 4096


def setup_logging(level: int = logging.WARNING) -> None:
    """Configure logging for reuse.

    You can only call this function once.
    """
    # library_logger is the root logger for reuse. We configure logging solely
    # for reuse, not for any other libraries.
    library_logger = logging.getLogger("reuse")

    if not library_logger.hasHandlers():
        library_logger.setLevel(level)
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        library_logger.addHandler(handler)


def execute_command(
    command: List[str],
    logger: logging.Logger,
    cwd: Optional[StrPath] = None,
    **kwargs: Any,
) -> subprocess.CompletedProcess:
    """Run the given command with subprocess.run. Forward kwargs. Silence
    output into a pipe unless kwargs override it.
    """
    logger.debug("running '%s'", " ".join(command))

    stdout: Union[None, int, IO[Any]] = kwargs.get("stdout", subprocess.PIPE)
    stderr: Union[None, int, IO[Any]] = kwargs.get("stderr", subprocess.PIPE)

    return subprocess.run(
        list(map(str, command)),
        stdout=stdout,
        stderr=stderr,
        check=False,
        cwd=str(cwd),
        **kwargs,
    )


def find_licenses_directory(root: Optional[StrPath] = None) -> Path:
    """Find the licenses directory from CWD or *root*. In the following order:

    - LICENSES/ in *root*.

    - Current directory if its name is "LICENSES"

    - LICENSES/ in CWD.

    The returned LICENSES/ directory NEED NOT EXIST. It may still need to be
    created.
    """
    cwd = Path.cwd()
    licenses_path = cwd / "LICENSES"

    if root:
        licenses_path = Path(root) / "LICENSES"
    elif cwd.name == "LICENSES":
        licenses_path = cwd

    return licenses_path


def decoded_text_from_binary(
    binary_file: BinaryIO, size: Optional[int] = None
) -> str:
    """Given a binary file object, detect its encoding and return its contents
    as a decoded string. Do not throw any errors if the encoding contains
    errors:  Just replace the false characters.

    If *size* is specified, only read so many bytes.
    """
    if size is None:
        size = -1
    rawdata = binary_file.read(size)
    result = rawdata.decode("utf-8", errors="replace")
    return result.replace("\r\n", "\n")


def _determine_license_path(path: StrPath) -> Path:
    """Given a path FILE, return FILE.license if it exists, otherwise return
    FILE.
    """
    license_path = Path(f"{path}.license")
    if not license_path.exists():
        license_path = Path(path)
    return license_path


def _determine_license_suffix_path(path: StrPath) -> Path:
    """Given a path FILE or FILE.license, return FILE.license."""
    path = Path(path)
    if path.suffix == ".license":
        return path
    return Path(f"{path}.license")


def _parse_copyright_year(year: str) -> list:
    """Parse copyright years and return list."""
    if not year:
        ret = []
    elif re.match(r"\d{4}$", year):
        ret = [int(year)]
    elif re.match(r"\d{4} ?- ?\d{4}$", year):
        ret = [int(year[:4]), int(year[-4:])]
    return ret


def _contains_snippet(binary_file: BinaryIO) -> bool:
    """Check if a file seems to contain a SPDX snippet"""
    # Assumes that if SPDX_SNIPPET_INDICATOR (SPDX-SnippetBegin) is found in a
    # file, the file contains a snippet
    content = binary_file.read()
    if SPDX_SNIPPET_INDICATOR in content:
        return True
    return False


def _get_comment_style(path: StrPath) -> Optional[Type[CommentStyle]]:
    """Return value of CommentStyle detected for *path* or None."""
    path = Path(path)
    style = FILENAME_COMMENT_STYLE_MAP_LOWERCASE.get(path.name.lower())
    if style is None:
        style = cast(
            Optional[Type[CommentStyle]],
            EXTENSION_COMMENT_STYLE_MAP_LOWERCASE.get(path.suffix.lower()),
        )
    return style


def _is_uncommentable(path: Path) -> bool:
    """*path*'s extension has the UncommentableCommentStyle."""
    return _get_comment_style(path) == UncommentableCommentStyle


def _has_style(path: Path) -> bool:
    """*path*'s extension has a CommentStyle."""
    return _get_comment_style(path) is not None


def merge_copyright_lines(copyright_lines: Set[str]) -> Set[str]:
    """Parse all copyright lines and merge identical statements making years
    into a range.

    If a same statement uses multiple prefixes, use only the most frequent one.
    """
    # pylint: disable=too-many-locals
    # TODO: Rewrite this function. It's a bit of a mess.
    copyright_in = []
    for line in copyright_lines:
        for pattern in _COPYRIGHT_PATTERNS:
            match = pattern.search(line)
            if match is not None:
                copyright_in.append(
                    {
                        "statement": match.groupdict()["statement"],
                        "year": _parse_copyright_year(
                            match.groupdict()["year"]
                        ),
                        "prefix": match.groupdict()["prefix"],
                    }
                )

    copyright_out = set()
    for line_info in copyright_in:
        statement = str(line_info["statement"])
        copyright_list = [
            item for item in copyright_in if item["statement"] == statement
        ]

        # Get the most common prefix.
        most_common = str(
            Counter([item["prefix"] for item in copyright_list]).most_common(1)[
                0
            ][0]
        )
        prefix = "spdx"
        for key, value in _COPYRIGHT_PREFIXES.items():
            if most_common == value:
                prefix = key
                break

        # get year range if any
        years: List[str] = []
        for copy in copyright_list:
            years += copy["year"]

        year: Optional[str] = None
        if years:
            if min(years) == max(years):
                year = min(years)
            else:
                year = f"{min(years)} - {max(years)}"

        copyright_out.add(make_copyright_line(statement, year, prefix))
    return copyright_out


def extract_reuse_info(text: str) -> ReuseInfo:
    """Extract REUSE information from comments in a string.

    Raises:
        ExpressionError: if an SPDX expression could not be parsed.
        ParseError: if an SPDX expression could not be parsed.
    """
    text = filter_ignore_block(text)
    spdx_tags: Dict[str, Set[str]] = {}
    for tag, pattern in _SPDX_TAGS.items():
        spdx_tags[tag] = set(find_spdx_tag(text, pattern))
    # License expressions and copyright matches are special cases.
    expressions = set()
    copyright_matches = set()
    for expression in spdx_tags.pop("spdx_expressions"):
        try:
            expressions.add(_LICENSING.parse(expression))
        except (ExpressionError, ParseError):
            _LOGGER.error(
                _("Could not parse '{expression}'").format(
                    expression=expression
                )
            )
            raise
    for line in text.splitlines():
        for pattern in _COPYRIGHT_PATTERNS:
            match = pattern.search(line)
            if match is not None:
                copyright_matches.add(match.groupdict()["copyright"].strip())
                break

    return ReuseInfo(
        spdx_expressions=expressions,
        copyright_lines=copyright_matches,
        **spdx_tags,  # type: ignore
    )


def reuse_info_of_file(
    path: StrPath, original_path: StrPath, root: StrPath
) -> ReuseInfo:
    """Open *path* and return its :class:`ReuseInfo`.

    Normally only the first few :const:`_HEADER_BYTES` are read. But if a
    snippet was detected, the entire file is read.
    """
    path = Path(path)
    with path.open("rb") as fp:
        try:
            read_limit: Optional[int] = _HEADER_BYTES
            # Completely read the file once
            # to search for possible snippets
            if _contains_snippet(fp):
                _LOGGER.debug(f"'{path}' seems to contain an SPDX Snippet")
                read_limit = None
            # Reset read position
            fp.seek(0)
            # Scan the file for REUSE info, possibly limiting the read
            # length
            file_result = extract_reuse_info(
                decoded_text_from_binary(fp, size=read_limit)
            )
            if file_result.contains_copyright_or_licensing():
                source_type = SourceType.FILE_HEADER
                if path.suffix == ".license":
                    source_type = SourceType.DOT_LICENSE
                return file_result.copy(
                    path=relative_from_root(original_path, root).as_posix(),
                    source_path=relative_from_root(path, root).as_posix(),
                    source_type=source_type,
                )

        except (ExpressionError, ParseError):
            _LOGGER.error(
                _(
                    "'{path}' holds an SPDX expression that cannot be"
                    " parsed, skipping the file"
                ).format(path=path)
            )
    return ReuseInfo()


def relative_from_root(path: StrPath, root: StrPath) -> Path:
    """A helper function to get *path* relative to *root*."""
    path = Path(path)
    try:
        return path.relative_to(root)
    except ValueError:
        return Path(os.path.relpath(path, start=root))


def find_spdx_tag(text: str, pattern: re.Pattern) -> Iterator[str]:
    """Extract all the values in *text* matching *pattern*'s regex, taking care
    of stripping extraneous whitespace of formatting.
    """
    for prefix, value in pattern.findall(text):
        prefix, value = prefix.strip(), value.strip()

        # Some comment headers have ASCII art to "frame" the comment, like this:
        #
        # /***********************\
        # |*  This is a comment  *|
        # \***********************/
        #
        # To ensure we parse them correctly, if the line ends with the inverse
        # of the comment prefix, we strip that suffix. See #343 for a real
        # world example of a project doing this (LLVM).
        suffix = prefix[::-1]
        if suffix and value.endswith(suffix):
            value = value[: -len(suffix)]

        yield value.strip()


def filter_ignore_block(text: str) -> str:
    """Filter out blocks beginning with REUSE_IGNORE_START and ending with
    REUSE_IGNORE_END to remove lines that should not be treated as copyright and
    licensing information.
    """
    ignore_start = None
    ignore_end = None
    if REUSE_IGNORE_START in text:
        ignore_start = text.index(REUSE_IGNORE_START)
    if REUSE_IGNORE_END in text:
        ignore_end = text.index(REUSE_IGNORE_END) + len(REUSE_IGNORE_END)
    if not ignore_start:
        return text
    if not ignore_end:
        return text[:ignore_start]
    if ignore_end > ignore_start:
        return text[:ignore_start] + filter_ignore_block(text[ignore_end:])
    rest = text[ignore_start + len(REUSE_IGNORE_START) :]
    if REUSE_IGNORE_END in rest:
        ignore_end = rest.index(REUSE_IGNORE_END) + len(REUSE_IGNORE_END)
        return text[:ignore_start] + filter_ignore_block(rest[ignore_end:])
    return text[:ignore_start]


def contains_reuse_info(text: str) -> bool:
    """The text contains REUSE info."""
    try:
        return bool(extract_reuse_info(text))
    except (ExpressionError, ParseError):
        return False


def make_copyright_line(
    statement: str, year: Optional[str] = None, copyright_prefix: str = "spdx"
) -> str:
    """Given a statement, prefix it with ``SPDX-FileCopyrightText:`` if it is
    not already prefixed with some manner of copyright tag.
    """
    if "\n" in statement:
        raise RuntimeError(f"Unexpected newline in '{statement}'")

    prefix = _COPYRIGHT_PREFIXES.get(copyright_prefix)
    if prefix is None:
        # TODO: Maybe translate this. Also maybe reduce DRY here.
        raise RuntimeError(
            "Unexpected copyright prefix: Need 'spdx', 'spdx-c', "
            "'spdx-symbol', 'string', 'string-c', "
            "'string-symbol', or 'symbol'"
        )

    for pattern in _COPYRIGHT_PATTERNS:
        match = pattern.search(statement)
        if match is not None:
            return statement
    if year is not None:
        return f"{prefix} {year} {statement}"
    return f"{prefix} {statement}"


def _checksum(path: StrPath) -> str:
    path = Path(path)

    file_sha1 = sha1()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(128 * file_sha1.block_size), b""):
            file_sha1.update(chunk)

    return file_sha1.hexdigest()


class PathType:
    """Factory for creating Paths"""

    def __init__(
        self,
        mode: str = "r",
        force_file: bool = False,
        force_directory: bool = False,
    ):
        if mode in ("r", "r+", "w"):
            self._mode = mode
        else:
            raise ValueError(f"mode='{mode}' is not valid")
        self._force_file = force_file
        self._force_directory = force_directory
        if self._force_file and self._force_directory:
            raise ValueError(
                "'force_file' and 'force_directory' cannot both be True"
            )

    def _check_read(self, path: Path) -> None:
        if path.exists() and os.access(path, os.R_OK):
            if self._force_file and not path.is_file():
                raise ArgumentTypeError(_("'{}' is not a file").format(path))
            if self._force_directory and not path.is_dir():
                raise ArgumentTypeError(
                    _("'{}' is not a directory").format(path)
                )
            return
        raise ArgumentTypeError(_("can't open '{}'").format(path))

    def _check_write(self, path: Path) -> None:
        if path.is_dir():
            raise ArgumentTypeError(
                _("can't write to directory '{}'").format(path)
            )
        if path.exists() and os.access(path, os.W_OK):
            return
        if not path.exists() and os.access(path.parent, os.W_OK):
            return
        raise ArgumentTypeError(_("can't write to '{}'").format(path))

    def __call__(self, string: str) -> Path:
        path = Path(string)

        try:
            if self._mode in ("r", "r+"):
                self._check_read(path)
            if self._mode in ("w", "r+"):
                self._check_write(path)
            return path
        except OSError as error:
            raise ArgumentTypeError(
                _("can't read or write '{}'").format(path)
            ) from error


def spdx_identifier(text: str) -> Expression:
    """argparse factory for creating SPDX expressions."""
    try:
        return _LICENSING.parse(text)
    except (ExpressionError, ParseError) as error:
        raise ArgumentTypeError(
            _("'{}' is not a valid SPDX expression, aborting").format(text)
        ) from error


def similar_spdx_identifiers(identifier: str) -> List[str]:
    """Given an incorrect SPDX identifier, return a list of similar ones."""
    suggestions: List[str] = []
    if identifier in ALL_NON_DEPRECATED_MAP:
        return suggestions

    for valid_identifier in ALL_NON_DEPRECATED_MAP:
        distance = SequenceMatcher(
            a=identifier.lower(), b=valid_identifier[: len(identifier)].lower()
        ).ratio()
        if distance > 0.75:
            suggestions.append(valid_identifier)
    suggestions = sorted(suggestions)

    return suggestions


def print_incorrect_spdx_identifier(
    identifier: str, out: IO[str] = sys.stdout
) -> None:
    """Print out that *identifier* is not valid, and follow up with some
    suggestions.
    """
    out.write(
        _("'{}' is not a valid SPDX License Identifier.").format(identifier)
    )
    out.write("\n")

    suggestions = similar_spdx_identifiers(identifier)
    if suggestions:
        out.write("\n")
        out.write(_("Did you mean:"))
        out.write("\n")
        for suggestion in suggestions:
            out.write(f"* {suggestion}\n")
        out.write("\n")
    out.write(
        _(
            "See <https://spdx.org/licenses/> for a list of valid "
            "SPDX License Identifiers."
        )
    )


def detect_line_endings(text: str) -> str:
    """Return one of '\n', '\r' or '\r\n' depending on the line endings used in
    *text*. Return os.linesep if there are no line endings.
    """
    line_endings = ["\r\n", "\r", "\n"]
    for line_ending in line_endings:
        if line_ending in text:
            return line_ending
    return os.linesep


def cleandoc_nl(text: str) -> str:
    """Like :func:`inspect.cleandoc`, but with a newline at the end."""
    return cleandoc(text) + "\n"


# REUSE-IgnoreEnd
