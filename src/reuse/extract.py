# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2020 Tuomas Siipola <tuomas@zpl.fi>
# SPDX-FileCopyrightText: 2022 Carmen Bianca Bakker <carmenbianca@fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2022 Nico Rikken <nico.rikken@fsfe.org>
# SPDX-FileCopyrightText: 2022 Pietro Albini <pietro.albini@ferrous-systems.com>
# SPDX-FileCopyrightText: 2023 DB Systel GmbH
# SPDX-FileCopyrightText: 2023 Johannes Zarl-Zierl <johannes@zarl-zierl.at>
# SPDX-FileCopyrightText: 2024 Rivos Inc.
# SPDX-FileCopyrightText: 2024 Skyler Grey <sky@a.starrysky.fyi>
# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Utilities related to the extraction of REUSE information out of files."""

import logging
import os
import re
from itertools import chain
from pathlib import Path
from typing import BinaryIO, Iterator, Optional

from boolean.boolean import ParseError
from license_expression import ExpressionError

from . import _LICENSING, ReuseInfo, SourceType
from ._util import relative_from_root
from .comment import _all_style_classes
from .i18n import _
from .types import StrPath

REUSE_IGNORE_START = "REUSE-IgnoreStart"
REUSE_IGNORE_END = "REUSE-IgnoreEnd"

# REUSE-IgnoreStart

SPDX_SNIPPET_INDICATOR = b"SPDX-SnippetBegin"

_LOGGER = logging.getLogger(__name__)

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
_SPDX_TAGS: dict[str, re.Pattern] = {
    "spdx_expressions": _LICENSE_IDENTIFIER_PATTERN,
    "contributor_lines": _CONTRIBUTOR_PATTERN,
}

_COPYRIGHT_PATTERNS = [
    re.compile(
        r"(?P<copyright>(?P<prefix>SPDX-(File|Snippet)CopyrightText:"
        r"(\s(\([Cc]\)|©|Copyright(\s(©|\([Cc]\)))?))?)\s+"
        r"((?P<year>\d{4} ?- ?\d{4}|\d{4}),?\s+)?"
        r"(?P<statement>.*?))" + _END_PATTERN
    ),
    re.compile(
        r"(?P<copyright>(?P<prefix>Copyright(\s(\([Cc]\)|©))?)\s+"
        r"((?P<year>\d{4} ?- ?\d{4}|\d{4}),?\s+)?"
        r"(?P<statement>.*?))" + _END_PATTERN
    ),
    re.compile(
        r"(?P<copyright>(?P<prefix>©)\s+"
        r"((?P<year>\d{4} ?- ?\d{4}|\d{4}),?\s+)?"
        r"(?P<statement>.*?))" + _END_PATTERN
    ),
]

_LICENSEREF_PATTERN = re.compile("LicenseRef-[a-zA-Z0-9-.]+$")

# Amount of bytes that we assume will be big enough to contain the entire
# comment header (including SPDX tags), so that we don't need to read the
# entire file.
_HEADER_BYTES = 4096


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


def _contains_snippet(binary_file: BinaryIO) -> bool:
    """Check if a file seems to contain a SPDX snippet"""
    # Assumes that if SPDX_SNIPPET_INDICATOR (SPDX-SnippetBegin) is found in a
    # file, the file contains a snippet
    content = binary_file.read()
    if SPDX_SNIPPET_INDICATOR in content:
        return True
    return False


def extract_reuse_info(text: str) -> ReuseInfo:
    """Extract REUSE information from comments in a string.

    Raises:
        ExpressionError: if an SPDX expression could not be parsed.
        ParseError: if an SPDX expression could not be parsed.
    """
    text = filter_ignore_block(text)
    spdx_tags: dict[str, set[str]] = {}
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


def detect_line_endings(text: str) -> str:
    """Return one of '\n', '\r' or '\r\n' depending on the line endings used in
    *text*. Return os.linesep if there are no line endings.
    """
    line_endings = ["\r\n", "\r", "\n"]
    for line_ending in line_endings:
        if line_ending in text:
            return line_ending
    return os.linesep


# REUSE-IgnoreEnd
