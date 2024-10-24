# SPDX-FileCopyrightText: 2024 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Utilities related to the parsing and storing of copyright notices."""

import re
from collections import Counter
from typing import Optional

from .extract import _COPYRIGHT_PATTERNS  # TODO: Get rid of this import.

_COPYRIGHT_PREFIXES = {
    "spdx": "SPDX-FileCopyrightText:",
    "spdx-c": "SPDX-FileCopyrightText: (C)",
    "spdx-string-c": "SPDX-FileCopyrightText: Copyright (C)",
    "spdx-string": "SPDX-FileCopyrightText: Copyright",
    "spdx-string-symbol": "SPDX-FileCopyrightText: Copyright ©",
    "spdx-symbol": "SPDX-FileCopyrightText: ©",
    "string": "Copyright",
    "string-c": "Copyright (C)",
    "string-symbol": "Copyright ©",
    "symbol": "©",
}


def merge_copyright_lines(copyright_lines: set[str]) -> set[str]:
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
        prefix = "spdx"
        for key, value in _COPYRIGHT_PREFIXES.items():
            if most_common == value:
                prefix = key
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
