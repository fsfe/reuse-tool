# SPDX-FileCopyrightText: 2024 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Utilities related to the parsing and storing of copyright notices."""

import re
from collections import Counter
from enum import StrEnum, unique
from typing import Optional

from .extract import _COPYRIGHT_PATTERNS  # TODO: Get rid of this import.


@unique
class CopyrightPrefix(StrEnum):
    """The prefix used for a copyright statement."""

    SPDX = "SPDX-FileCopyrightText:"
    SPDX_C = "SPDX-FileCopyrightText: (C)"
    SPDX_SYMBOL = "SPDX-FileCopyrightText: ©"
    SPDX_STRING = "SPDX-FileCopyrightText: Copyright"
    SPDX_STRING_C = "SPDX-FileCopyrightText: Copyright (C)"
    SPDX_STRING_SYMBOL = "SPDX-FileCopyrightText: Copyright ©"
    SNIPPET = "SPDX-SnippetCopyrightText:"
    SNIPPET_C = "SPDX-SnippetCopyrightText: (C)"
    SNIPPET_SYMBOL = "SPDX-SnippetCopyrightText: ©"
    SNIPPET_STRING = "SPDX-SnippetCopyrightText: Copyright"
    SNIPPET_STRING_C = "SPDX-SnippetCopyrightText: Copyright (C)"
    SNIPPET_STRING_SYMBOL = "SPDX-SnippetCopyrightText: Copyright ©"
    STRING = "Copyright"
    STRING_C = "Copyright (C)"
    STRING_SYMBOL = "Copyright ©"
    SYMBOL = "©"

    @staticmethod
    def lowercase_name(name: str) -> str:
        """Given an uppercase NAME, return name. Underscores are converted to
        dashes.

        >>> CopyrightPrefix.lowercase_name("SPDX_STRING")
        'spdx-string'
        """
        return name.lower().replace("_", "-")

    @staticmethod
    def uppercase_name(name: str) -> str:
        """Given a lowercase name, return NAME. Dashes are converted to
        underscores.

        >>> CopyrightPrefix.uppercase_name("spdx-string")
        'SPDX_STRING'
        """
        return name.upper().replace("-", "_")


def merge_copyright_lines(copyright_lines: set[str]) -> set[str]:
    """Parse all copyright lines and merge identical statements making years
    into a range.

    If a same statement uses multiple prefixes, use only the most frequent one.
    """
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
                break

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
        prefix = CopyrightPrefix.SPDX
        for enum in CopyrightPrefix:
            if most_common == enum.value:
                prefix = enum
                break

        # get year range if any
        years: list[str] = []
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


def make_copyright_line(
    statement: str,
    year: Optional[str] = None,
    prefix: CopyrightPrefix = CopyrightPrefix.SPDX,
) -> str:
    """Given a statement, prefix it with ``SPDX-FileCopyrightText:`` if it is
    not already prefixed with some manner of copyright tag.
    """
    if "\n" in statement:
        raise RuntimeError(f"Unexpected newline in '{statement}'")

    for pattern in _COPYRIGHT_PATTERNS:
        match = pattern.search(statement)
        if match is not None:
            return statement
    if year is not None:
        return f"{prefix.value} {year} {statement}"
    return f"{prefix.value} {statement}"


def _parse_copyright_year(year: Optional[str]) -> list[str]:
    """Parse copyright years and return list."""
    ret: list[str] = []
    if not year:
        return ret
    if re.match(r"\d{4}$", year):
        ret = [year]
    elif re.match(r"\d{4} ?- ?\d{4}$", year):
        ret = [year[:4], year[-4:]]
    return ret
