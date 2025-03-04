# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2021 Alliander N.V.
# SPDX-FileCopyrightText: 2023 Carmen Bianca BAKKER <carmenbianca@fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Deprecated utilities related to the parsing and storing of copyright notices.

This module will soon be removed in favour of :mod:`reuse.copyright`.
"""

import re
from collections import Counter
from typing import Optional

from .copyright import CopyrightPrefix
from .extract import _COPYRIGHT_PATTERNS

# TODO: Everything below this comment will be removed in a future refactoring.


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
