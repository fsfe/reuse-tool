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
from typing import BinaryIO

from boolean.boolean import Expression, ParseError
from license_expression import ExpressionError

from . import _LICENSING
from ._util import relative_from_root
from .comment import _all_style_classes
from .copyright import (
    COPYRIGHT_NOTICE_PATTERN,
    CopyrightNotice,
    ReuseInfo,
    SourceType,
)
from .i18n import _
from .types import StrPath

REUSE_IGNORE_START = "REUSE-IgnoreStart"
REUSE_IGNORE_END = "REUSE-IgnoreEnd"

# REUSE-IgnoreStart

SPDX_SNIPPET_INDICATOR = b"SPDX-SnippetBegin"

_LOGGER = logging.getLogger(__name__)

_START_PATTERN = r"(?:^.*?)"
_END_PATTERN = r"(?:({})\s*)*$".format(
    "|".join(
        set(
            chain(
                (
                    re.escape(style.MULTI_LINE.end)
                    for style in _all_style_classes()
                    if style.MULTI_LINE.end
                ),
                # These are special endings which do not belong to specific
                # comment styles, but which we want to nonetheless strip away
                # while parsing.
                (
                    # ex: <tag value="Copyright Jane Doe">
                    r'"\s*/*>',
                    r"'\s*/*>",
                    # ex: [SPDX-License-Identifier: GPL-3.0-or-later] ::
                    r"\]\s*::",
                    # ex: ASCII art frames for comment headers. See #343 for a
                    # real-world example of a project doing this (LLVM).
                    r"\*",
                    r"\*\|",
                ),
            )
        )
    )
)
_COPYRIGHT_NOTICE_PATTERN = re.compile(
    _START_PATTERN + COPYRIGHT_NOTICE_PATTERN.pattern + _END_PATTERN,
    re.MULTILINE,
)
_LICENSE_IDENTIFIER_PATTERN = re.compile(
    _START_PATTERN
    + r"SPDX-License-Identifier:\s*(?P<value>.*?)"
    + _END_PATTERN,
    re.MULTILINE,
)
_CONTRIBUTOR_PATTERN = re.compile(
    _START_PATTERN + r"SPDX-FileContributor:\s*(?P<value>.*?)" + _END_PATTERN,
    re.MULTILINE,
)
# The keys match the relevant attributes of ReuseInfo.
_SPDX_TAGS: dict[str, re.Pattern] = {
    "spdx_expressions": _LICENSE_IDENTIFIER_PATTERN,
    "contributor_lines": _CONTRIBUTOR_PATTERN,
}
_LICENSEREF_PATTERN = re.compile("LicenseRef-[a-zA-Z0-9-.]+$")

# Amount of bytes that we assume will be big enough to contain the entire
# comment header (including SPDX tags), so that we don't need to read the
# entire file.
_HEADER_BYTES = 4096


def decoded_text_from_binary(
    binary_file: BinaryIO, size: int | None = None
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
    """Extract REUSE information from a multi-line text block.

    Raises:
        ExpressionError: if an SPDX expression could not be parsed.
        ParseError: if an SPDX expression could not be parsed.
    """
    # TODO: This function call should not be here. It should already be filtered
    # out before we get to this function.
    text = filter_ignore_block(text)

    notices: set[CopyrightNotice] = set()
    expressions: set[Expression] = set()
    contributors: set[str] = set()

    for notice in _COPYRIGHT_NOTICE_PATTERN.finditer(text):
        notices.add(CopyrightNotice.from_match(notice))

    for expression in _LICENSE_IDENTIFIER_PATTERN.finditer(text):
        try:
            expressions.add(_LICENSING.parse(expression.group("value")))
        except (ExpressionError, ParseError):
            _LOGGER.error(
                _("Could not parse '{expression}'").format(
                    expression=expression.group("value")
                )
            )
            raise

    # TODO: We can generalise this. But if we do, we shouldn't run a regex over
    # the entire file multiple times. We should check for `SPDX-.+:.*$`
    # (simplified), and further filter the results in a second pass.
    for contributor in _CONTRIBUTOR_PATTERN.finditer(text):
        contributors.add(contributor.group("value"))

    return ReuseInfo(
        spdx_expressions=expressions,
        copyright_notices=notices,
        contributor_lines=contributors,
    )


def reuse_info_of_file(
    path: StrPath, original_path: Path, root: Path
) -> ReuseInfo:
    """Open *path* and return its :class:`ReuseInfo`.

    Normally only the first few :const:`_HEADER_BYTES` are read. But if a
    snippet was detected, the entire file is read.
    """
    path = Path(path)
    with path.open("rb") as fp:
        try:
            read_limit: int | None = _HEADER_BYTES
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
