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
from typing import BinaryIO, Generator, NamedTuple

from boolean.boolean import Expression, ParseError
from license_expression import ExpressionError

from . import _LICENSING
from .comment import _all_style_classes
from .copyright import COPYRIGHT_NOTICE_PATTERN, CopyrightNotice, ReuseInfo
from .i18n import _

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

#: Default chunk size for reading files.
CHUNK_SIZE = 1024 * 64
#: Default line size for reading files.
LINE_SIZE = 1024


class FilterBlock(NamedTuple):
    """A simple tuple that holds a block of text, and whether that block of text
    is in an ignore block.
    """

    text: str
    in_ignore_block: bool


def filter_ignore_block(
    text: str, in_ignore_block: bool = False
) -> FilterBlock:
    """Filter out blocks beginning with REUSE_IGNORE_START and ending with
    REUSE_IGNORE_END to remove lines that should not be treated as copyright and
    licensing information.

    Args:
        text: The text out of which the ignore blocks must be filtered.
        in_ignore_block: Whether the text is already in an ignore block. This is
            useful when you parse subsequent chunks of text, and one chunk does
            not close the ignore block.

    Returns:
        A :class:`FilterBlock` tuple that contains the filtered text and a
        boolean that signals whether the ignore block is still open.
    """
    ignore_start: int | None = None if not in_ignore_block else 0
    ignore_end: int | None = None
    if REUSE_IGNORE_START in text:
        ignore_start = text.index(REUSE_IGNORE_START)
    if REUSE_IGNORE_END in text:
        ignore_end = text.index(REUSE_IGNORE_END) + len(REUSE_IGNORE_END)
    if ignore_start is None:
        return FilterBlock(text, False)
    if ignore_end is None:
        return FilterBlock(text[:ignore_start], True)
    if ignore_end > ignore_start:
        text_before_block = text[:ignore_start]
        text_after_block, in_ignore_block = filter_ignore_block(
            text[ignore_end:], False
        )
        return FilterBlock(
            text_before_block + text_after_block, in_ignore_block
        )
    rest = text[ignore_start + len(REUSE_IGNORE_START) :]
    if REUSE_IGNORE_END in rest:
        ignore_end = rest.index(REUSE_IGNORE_END) + len(REUSE_IGNORE_END)
        text_before_block = text[:ignore_start]
        text_after_block, in_ignore_block = filter_ignore_block(
            rest[ignore_end:]
        )
        return FilterBlock(
            text_before_block + text_after_block, in_ignore_block
        )
    return FilterBlock(text[:ignore_start], True)


def extract_reuse_info(text: str) -> ReuseInfo:
    """Extract REUSE information from a multi-line text block.

    Raises:
        ExpressionError: if an SPDX expression could not be parsed.
        ParseError: if an SPDX expression could not be parsed.
    """
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


def _read_chunks(
    fp: BinaryIO,
    chunk_size: int = CHUNK_SIZE,
    line_size: int = LINE_SIZE,
) -> Generator[bytes, None, None]:
    """Read and yield somewhat equal-sized chunks from (realistically) a file.
    The chunks always split at a newline where possible.

    An amount of bytes equal to *chunk_size* is always read into the chunk if
    *fp* contains that many bytes. An additional *line_size* or lesser amount of
    bytes is also read into the chunk, up to the next newline character.
    """
    while True:
        chunk = fp.read(chunk_size)
        if not chunk:
            break
        remainder = fp.readline(line_size)
        if remainder:
            chunk += remainder
        yield chunk


def _process_chunk(chunk: bytes, in_ignore_block: bool = False) -> FilterBlock:
    """Decode and clean up a chunk."""
    # TODO: Not everything is UTF-8.
    text = chunk.decode("utf-8", errors="replace")
    # TODO: Better newline handling.
    text = text.replace("\r\n", "\n")
    return filter_ignore_block(text, in_ignore_block)


def reuse_info_of_file(
    fp: BinaryIO,
    chunk_size: int = CHUNK_SIZE,
    line_size: int = LINE_SIZE,
) -> ReuseInfo:
    """Read from *fp* to extract REUSE information. It is read in chunks of
    *chunk_size*, additionally reading up to *line_size* until the next newline.

    This function decodes the binary data into UTF-8 and removes REUSE ignore
    blocks before attempting to extract the REUSE information.
    """
    in_ignore_block = False
    reuse_infos: list[ReuseInfo] = []
    for chunk in _read_chunks(fp, chunk_size=chunk_size, line_size=line_size):
        text, in_ignore_block = _process_chunk(
            chunk, in_ignore_block=in_ignore_block
        )
        reuse_infos.append(extract_reuse_info(text))
    return ReuseInfo().union(*reuse_infos)


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
