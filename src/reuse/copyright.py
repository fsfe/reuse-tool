# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2021 Alliander N.V.
# SPDX-FileCopyrightText: 2023 Carmen Bianca BAKKER <carmenbianca@fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Utilities related to the parsing and storing of copyright notices."""

import difflib
import logging
import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import InitVar, dataclass, field
from enum import Enum, unique
from functools import cached_property
from io import StringIO
from itertools import chain
from typing import Any, Literal, NewType, cast

from license_expression import (
    ExpressionError,
    LicenseExpression,
    Licensing,
    combine_expressions,
)

from .exceptions import CopyrightNoticeParseError, YearRangeParseError

# REUSE-IgnoreStart

_LOGGER = logging.getLogger(__name__)

_LICENSING = Licensing()

#: A string that is four digits long.
FourDigitString = NewType("FourDigitString", str)
#: A range separator between two years.
YearRangeSeparator = Literal[
    "--",  # ascii en dash
    "–",  # en dash
    "-",  # ascii dash
]


def is_four_digits(value: str) -> FourDigitString | Literal[False]:
    """Identify a string as a four-digit string. Return the string as
    :type:`FourDigitString` if it is one.

    >>> is_four_digits("1234")
    '1234'
    >>> is_four_digits("abcd")
    False
    >>> is_four_digits("12345")
    False
    """
    if value.isdigit() and len(value) == 4:
        return FourDigitString(value)
    return False


def validate_four_digits(value: str) -> FourDigitString:
    """Validate whether a given string is a :type:`FourDigitString`.

    >>> validate_four_digits("1234")
    '1234'
    >>> validate_four_digits("abcd")
    Traceback (most recent call last):
        ...
    ValueError: 'abcd' is not a four-digit year.
    >>> validate_four_digits("12345")
    Traceback (most recent call last):
        ...
    ValueError: '12345' is not a four-digit year.

    Raises:
        ValueError: The string is not four digits.
    """
    if not (result := is_four_digits(value)):
        raise ValueError(f"'{value}' is not a four-digit year.")
    return result


_ANY_SEPARATOR = (
    r"(?:" + r"|".join(YearRangeSeparator.__args__) + r")"  # type: ignore
)
#: A regex pattern to match e.g. '2017-2020'.
YEAR_RANGE_PATTERN = re.compile(
    r"(?P<start>\d{4})"
    r"(?:"
    r"(?:(?P<separator_nonspaced>" + _ANY_SEPARATOR + r")"
    r"(?P<end_nonspaced>\S+)?)"
    r"|"
    r"(?:\s+(?P<separator_spaced>" + _ANY_SEPARATOR + r")"
    r"\s+(?P<end_spaced>\d{4}))"
    r")?"
)
_YEAR_RANGE_PATTERN_ANONYMISED = re.sub(
    r"\(\?P<\w+>", r"(?:", YEAR_RANGE_PATTERN.pattern
)
_SYMBOL_OR_C_SUBPATTERN = r"(©|\([Cc]\))"
_STRING_SUBPATTERN = (
    r"(Copyright((\s*" + _SYMBOL_OR_C_SUBPATTERN + r")|(?=\s)))"
)
#: A regex pattern to match a complete and valid REUSE copyright notice.
COPYRIGHT_NOTICE_PATTERN = re.compile(
    r"(?P<prefix>("
    r"SPDX-(File|Snippet)CopyrightText:"
    + r"(\s*("
    + _SYMBOL_OR_C_SUBPATTERN
    + "|"
    + _STRING_SUBPATTERN
    + "))?"
    + r"|"
    + _STRING_SUBPATTERN
    + r"|"
    r"©"
    r"))"
    r"\s*"
    r"(?P<text>.*?)"
    r"\s*"
)
_YEARS_PATTERN = re.compile(
    r"(?P<prefix>(^|,?\s+))(?P<years>"
    + _YEAR_RANGE_PATTERN_ANONYMISED
    + r"((\s*,\s*|\s+)"
    + _YEAR_RANGE_PATTERN_ANONYMISED
    + r")*)(?P<suffix>,?(\s+|$))"
)
_COMMA_SPACE_PATTERN = re.compile(r"^,?\s+")

_LOOKBEHINDS = "".join(
    rf"(?<!\s{separator})"
    for separator in YearRangeSeparator.__args__  # type: ignore
)
_YEAR_RANGE_SPLIT_REGEX = re.compile(
    # Separated by comma (plus any whitespace)
    r",\s*|" +
    # Separated by whitespace only. However, we cannot split on
    # whitespace that is itself part of a year range (e.g. ``2017 -
    # 2019``). The lookbehinds and lookahead take care of that. There
    # are multiple lookbehinds because lookbehinds cannot be
    # variable-width.
    _LOOKBEHINDS + r"\s+"
    rf"(?!{_ANY_SEPARATOR}\s)"
)


# TODO: In Python 3.11, turn this into a StrEnum
@unique
class CopyrightPrefix(Enum):
    """The prefix used for a copyright notice."""

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


@dataclass(frozen=True)
class YearRange:
    """Represents a year range, such as '2017-2025', or '2017'. This only
    represents a single range; multiple separated ranges should be put in a
    collection (typically a tuple).
    """

    #: The first year in the range. If it is only a single year, this is the
    #: only relevant value.
    start: FourDigitString
    #: The separator between :attr:`start` and :attr:`end`. If no value for
    #: :attr:`end` is provided, a range into infinity is implied, and
    #: :attr:`end` becomes an empty string.
    separator: YearRangeSeparator | None = field(default=None, compare=False)
    #: The second year in the range. This can also be a word like 'Present'.
    #: This is bad practice, but still supported.
    end: FourDigitString | str | None = None

    #: If parsed from a string, this contains the original string.
    original: str | None = field(
        default=None, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if self.separator is not None and self.end is None:
            object.__setattr__(self, "end", "")

    # TODO: In Python 3.11, return Self
    @classmethod
    def from_string(cls, value: str) -> "YearRange":
        """Create a :class:`YearRange` object from a string.

        Raises:
            YearRangeParseError: The string is not a valid year range.
        """
        re_result = YEAR_RANGE_PATTERN.fullmatch(value)
        if not re_result:
            raise YearRangeParseError(f"'{value}' is not a valid year range.")

        groups = re_result.groupdict()
        start = groups["start"]
        separator = groups["separator_nonspaced"] or groups["separator_spaced"]
        end = groups["end_nonspaced"] or groups["end_spaced"]

        # Mypy is disabled for this because the values are enforced by the
        # regex. This could be cleaner, but would require a lot of useless code
        # to validate what the regex already enforces.
        result = cls(start, separator, end)  # type: ignore
        object.__setattr__(result, "original", value)
        return result

    @classmethod
    def tuple_from_string(cls, value: str) -> tuple["YearRange", ...]:
        """Create a tuple of :class:`YearRange` objects from a string containing
        multiple ranges.

        Raises:
            YearRangeParseError: The substring is not a valid year range.
        """
        years: list[YearRange] = []
        for year in _YEAR_RANGE_SPLIT_REGEX.split(value):
            if not year:
                continue
            years.append(YearRange.from_string(year))
        return tuple(years)

    def __str__(self) -> str:
        result = StringIO()
        result.write(self.start)
        if self.separator:
            result.write(self.separator)
        if self.end:
            # Use a default separator if one is not defined.
            if not self.separator:
                result.write("-")
            result.write(self.end)
        return result.getvalue()

    def to_string(self, original: bool = False) -> str:
        """Converts the internal representation of the date range into a
        string. If *original* is :const:`True`, :attr:`original` is returned if
        it exists.

        If :attr:`start` and :attr:`end` are provided without :attr:`separator`,
        ``-`` will be used as default separator in the output.

        This method is identical to calling :func:`str` on this object, provided
        *original* is :const:`False`.
        """
        if original and self.original is not None:
            return self.original
        return str(self)

    def __lt__(self, other: Any) -> bool:
        # pylint: disable=too-many-return-statements
        if not isinstance(other, YearRange):
            return NotImplemented
        # Start year determines most of the storting.
        if self.start < other.start:
            return True
        if self.start > other.start:
            return False
        # Ranges with end dates are sorted after those who don't.
        if self.end is None and other.end is not None:
            return True
        if self.end is not None and other.end is not None:
            # Non-digit ends are sorted after digit ends.
            if not is_four_digits(self.end) and is_four_digits(other.end):
                return False
            if is_four_digits(self.end) and not is_four_digits(other.end):
                return True
            return self.end < other.end
        # No comparing on separators.
        return False

    # TODO: In Python 3.11, use Self
    @classmethod
    def compact(cls, ranges: Iterable["YearRange"]) -> tuple["YearRange", ...]:
        """Given an iterable of :class:`YearRange`, compact them such that a new
        more concise list is returne without losing information. This process
        also sorts the ranges, such that ranges with lower starts come before
        ranges with higher starts.

        - Consecutive years (e.g. 2017, 2018, 2019) are turned into a single
          range (2017-2019).
        - Two consecutive years (e.g. 2017, 2018) are NOT turned turned into a
          single range.
        - Consecutive ranges (e.g. 2017-2019, 2020-2022) are turned into a
          single range (2017-2022).
        - Overlapping ranges (e.g. 2017-2022, 2019-2021) are turned into a
          single range (2017-2022).
        - Repeated ranges are removed.
        - Ranges with non-year ends (e.g. 2017-Present, 2020-Present) are only
          turned into a single range with ranges that have identical ends
          (2017-Present).
        """
        ranges = sorted(ranges)
        compacted: list[YearRange] = []

        if not ranges:
            return tuple()

        # TODO: In Python 3.11, use Self
        def filter_same_end(ranges: Iterable[YearRange]) -> list[YearRange]:
            """If some year ranges have the same end, then only take the ones
            with the lowest start.
            """
            result: list[YearRange] = []
            ends: defaultdict[str | None, list[YearRange]] = defaultdict(list)
            for item in ranges:
                ends[item.end].append(item)
            for key, range_list in ends.items():
                if key is None:
                    for item in range_list:
                        result.append(item)
                else:
                    # *ranges* is sorted, so take the first item with the lowest
                    # start.
                    result.append(range_list[0])
            return sorted(result)

        ranges = filter_same_end(ranges)

        current_start: int = int(ranges[0].start)
        current_end: str = (
            ranges[0].end if ranges[0].end is not None else ranges[0].start
        )

        # TODO: In Python 3.11, use Self
        def add_to_compacted(
            start: int, end: str, next_range: YearRange | None
        ) -> None:
            nonlocal compacted
            if is_four_digits(end):
                if int(end) - start == 0:
                    compacted.append(cls(validate_four_digits(str(start))))
                elif int(end) - start == 1:
                    compacted.append(cls(validate_four_digits(str(start))))
                    compacted.append(cls(validate_four_digits(end)))
                else:
                    compacted.append(
                        cls(
                            validate_four_digits(str(start)),
                            end=end,
                        )
                    )
            else:
                compacted.append(cls(validate_four_digits(str(start)), end=end))
            nonlocal current_start
            nonlocal current_end
            if next_range is not None:
                current_start = int(next_range.start)
                current_end = (
                    next_range.end
                    if next_range.end is not None
                    else next_range.start
                )

        next_start: int | None = None
        next_end: str | None = None
        for next_range in ranges[1:]:
            next_start = int(next_range.start)
            next_end = (
                next_range.end
                if next_range.end is not None
                else next_range.start
            )

            current_end_int: int | None = (
                int(current_end) if is_four_digits(current_end) else None
            )
            next_end_int: int | None = (
                int(next_end) if is_four_digits(next_end) else None
            )
            # The end lines up with next start.
            if (
                current_end_int is not None
                and current_end_int + 1 >= next_start
            ):
                if next_end_int is not None:
                    # In a strange scenario where the next range's end is BEFORE
                    # its start, just save our progress and continue the loop.
                    if next_end_int < next_start:
                        add_to_compacted(current_start, current_end, next_range)
                    # Increment the end.
                    elif next_end_int >= current_end_int:
                        current_end = next_end
            else:
                add_to_compacted(current_start, current_end, next_range)

        add_to_compacted(current_start, current_end, None)
        # If the beforelast range's end was int-y, and the last range's end is
        # string-y, we need to separately add the last range.
        if (
            next_end is not None
            and is_four_digits(current_end)
            and not is_four_digits(next_end)
        ):
            add_to_compacted(cast(int, next_start), next_end, None)
        return tuple(compacted)


def _most_common_prefix(
    copyright_notices: Iterable["CopyrightNotice"],
) -> CopyrightPrefix:
    """Given a number of :class:`CopyrightNotice`s, find the most common one. If
    there is a tie for the most common prefix, return enum which is defined
    before all others in :class:`CopyrightPrefix`.
    """
    counter = Counter(notice.prefix for notice in copyright_notices)
    max_count = max(counter.values())
    most_common = {key for key, value in counter.items() if value == max_count}
    # One prefix is more common than all others.
    if len(most_common) == 1:
        return next(iter(most_common))
    # Enums preserve order of their members. Return the first match.
    for prefix in CopyrightPrefix:
        if prefix in most_common:
            return prefix
    # This shouldn't be reached.
    return CopyrightPrefix.SPDX


@dataclass(frozen=True)
class CopyrightNotice:
    """Represents a single copyright notice."""

    #: The copyright holder. Strictly, this is all text in the copyright notice
    #: which is not part of *years*.
    name: str
    #: The prefix with which the copyright statement begins.
    prefix: CopyrightPrefix = CopyrightPrefix.SPDX
    #: The dates associated with the copyright notice.
    years: tuple[YearRange, ...] = field(default_factory=tuple)

    #: If parsed from a string, this contains the original string.
    original: str | None = field(
        default=None, init=False, repr=False, compare=False
    )

    # TODO: In Python 3.11, return Self.
    @classmethod
    def from_string(cls, value: str) -> "CopyrightNotice":
        """Create a :class:`CopyrightNotice` object from a string.

        Raises:
            CopyrightNoticeParseError: The string is not a valid copyright
                notice.
        """
        re_result = COPYRIGHT_NOTICE_PATTERN.fullmatch(value)
        if not re_result:
            raise CopyrightNoticeParseError(
                f"'{value}' is not a copyright notice."
            )
        return cls.from_match(re_result)

    @staticmethod
    def _detect_prefix(prefix: str) -> CopyrightPrefix:
        """Given a matched prefix from :const:`COPYRIGHT_NOTICE_PATTERN`, detect
        the associated prefix.
        """
        prefix_lower = prefix.lower()
        # String-match the prefix.
        for prefix_enum in (
            cast(CopyrightPrefix, item) for item in reversed(CopyrightPrefix)
        ):
            # lower() is used to match (C) as well as (c).
            if prefix_lower == prefix_enum.value.lower():
                return prefix_enum
        # The prefix could not be string-matched, most likely because there
        # was unexpected spacing in the prefix. Get a close match using
        # difflib.
        matches = difflib.get_close_matches(
            prefix,
            # TODO: In Python 3.11, this list comprehension is not needed.
            [item.value for item in CopyrightPrefix],
            n=1,
            cutoff=0.2,
        )
        if matches:
            return CopyrightPrefix(matches[0])
        # This shouldn't happen, but if no prefix could be found,
        # default to SPDX.
        return CopyrightPrefix.SPDX

    @classmethod
    def from_match(cls, value: re.Match) -> "CopyrightNotice":
        """Create a :class:`CopyrightNotice` object from a regular expression
        match using the :const:`COPYRIGHT_NOTICE_PATTERN` :class:`re.Pattern`.
        """
        prefix = cls._detect_prefix(value.group("prefix"))

        re_text = value.group("text")
        year_ranges_substrings = list(_YEARS_PATTERN.finditer(re_text))
        start_ends: list[tuple[int, int]] = [
            (match.start("prefix"), match.end("years"))
            for match in year_ranges_substrings
        ]
        name_parts: list[str] = []
        last = 0
        for start, end in start_ends:
            name_parts.append(re_text[last:start])
            last = end
        name_parts.append(re_text[last:])

        name = "".join(name_parts)
        # Remove ', ' from the start of the name, which appears in e.g.
        # 'Copyright 2017, Jane Doe'.
        name = _COMMA_SPACE_PATTERN.sub("", name)
        years: tuple[YearRange, ...] = tuple()
        if year_ranges_substrings:
            years = tuple(
                chain.from_iterable(
                    YearRange.tuple_from_string(match.group("years"))
                    for match in year_ranges_substrings
                )
            )
        result = cls(
            name=name,
            prefix=prefix,
            years=years,
        )
        object.__setattr__(result, "original", value.string)
        return result

    @classmethod
    def merge(
        cls, copyright_notices: Iterable["CopyrightNotice"]
    ) -> set["CopyrightNotice"]:
        """Given an iterable of :class:`CopyrightNotice`, merge all notices
        which have the same name. The years are compacted, and from the
        :class:`CopyrightPrefix` prefixes in *copyright_notices*, the most
        common is chosen. If there is a tie in frequency, choose the one which
        appears first in the enum.
        """
        matches: defaultdict[str, list[CopyrightNotice]] = defaultdict(list)
        result: set[CopyrightNotice] = set()
        for notice in copyright_notices:
            matches[notice.name].append(notice)
        for key, value in matches.items():
            result.add(
                cls(
                    key,
                    prefix=_most_common_prefix(value),
                    years=YearRange.compact(
                        chain.from_iterable(notice.years for notice in value)
                    ),
                )
            )
        return result

    def __str__(self) -> str:
        result = StringIO()
        result.write(self.prefix.value)
        if self.years:
            result.write(" ")
            result.write(
                ", ".join(str(date_range) for date_range in self.years)
            )
        result.write(f" {self.name}")
        return result.getvalue()

    def __lt__(self, other: "CopyrightNotice") -> bool:
        def norm(item: Any | None) -> tuple[int, Any]:
            """If no item is defined, return a tuple that sorts _after_
            items that are defined.
            """
            return (0, item) if item else (1, "")

        return (
            norm(self.years),
            self.name,
            self.prefix.value,
        ) < (
            norm(other.years),
            other.name,
            other.prefix.value,
        )

    def to_string(self, original: bool = False) -> str:
        """Converts the internal representation of the copyright notice into a
        string. If *original* is :const:`True`, :attr:`original` is returned if
        it exists.

        This method is identical to calling :func:`str` on this object, provided
        *original* is :const:`False`.
        """
        if original and self.original is not None:
            return self.original
        return str(self)


@dataclass(frozen=True)
class SpdxExpression:
    """A simple dataclass that contains an SPDX License Expression.

    Use :meth:`SpdxExpression.__str__` to get a string representation of the
    expression.
    """

    #: A string representing an SPDX License Expression. It may be invalid.
    text: InitVar[str]
    _text: str = field(init=False, repr=True)

    def __post_init__(self, text: str) -> None:
        object.__setattr__(self, "_text", text)

    @cached_property
    def is_valid(self) -> bool:
        """If :attr:`text` is a valid SPDX License Expression, this property is
        :const:`True`.

        To be 'valid', it has to follow the grammar and syntax of the SPDX
        specification. The licenses and exceptions need not appear on the
        license list.
        """
        return self._expression is not None

    @cached_property
    def _expression(self) -> LicenseExpression | None:
        """A parsed :class:`LicenseExpression` from :attr:`text`. If
        :attr:`text` could not be parsed, *_expression*'s value is
        :const:`None`.
        """
        try:
            return _LICENSING.parse(self._text, simple=True)
        except ExpressionError:
            return None

    @cached_property
    def licenses(self) -> list[str]:
        """Return a list of licenses used in the expression, in order of
        appearance, without duplicates.

        If the expression is invalid, the list contains a single item
        :attr:`text`.
        """
        if self._expression is not None:
            return _LICENSING.license_keys(self._expression)
        return [self._text]

    @classmethod
    def combine(
        cls,
        spdx_expressions: Iterable["SpdxExpression"],
    ) -> "SpdxExpression":
        """Combine the *spdx_expressions* into a single :class:`SpdxExpression`,
        joined by AND operators.
        """
        is_valid = True
        for expression in spdx_expressions:
            if not expression.is_valid:
                is_valid = False
        if is_valid:
            return cls(
                str(
                    combine_expressions(
                        list(
                            # pylint: disable=protected-access
                            expression._expression
                            for expression in spdx_expressions
                        )
                    )
                )
            )
        return cls(
            " AND ".join(f"({expression})" for expression in spdx_expressions)
        )

    def simplify(self) -> "SpdxExpression":
        """If the expression is valid, return a new :class:`SpdxExpression`
        which is 'simplified', meaning that boolean operators are collapsed.
        'MIT OR MIT' simplifies to 'MIT', and so forth.

        If the expression is not valid, ``self`` is returned.
        """
        if self.is_valid:
            return self.__class__(
                str(cast(LicenseExpression, self._expression).simplify())
            )
        return self

    def __str__(self) -> str:
        """Return a string representation of the expression if it is valid.
        Otherwise, return :attr:`text`.
        """
        if self._expression is not None:
            return str(self._expression)
        return self._text

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, SpdxExpression):
            return NotImplemented
        if self._expression is not None and other._expression is not None:
            return self._expression == other._expression
        return self._text == other._text

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, SpdxExpression):
            return NotImplemented
        return str(self) < str(other)


class SourceType(Enum):
    """
    An enumeration representing the types of sources for license information.
    """

    #: A .license file containing license information.
    DOT_LICENSE = "dot-license"
    #: A file header containing license information.
    FILE_HEADER = "file-header"
    #: A .reuse/dep5 file containing license information.
    DEP5 = "dep5"
    #: A REUSE.toml file containing license information.
    REUSE_TOML = "reuse-toml"


@dataclass(frozen=True, kw_only=True)
class ReuseInfo:
    """Simple dataclass holding licensing and copyright information"""

    spdx_expressions: set[SpdxExpression] = field(default_factory=set)
    copyright_notices: set[CopyrightNotice] = field(default_factory=set)
    contributor_lines: set[str] = field(default_factory=set)
    path: str | None = None
    source_path: str | None = None
    source_type: SourceType | None = None

    def _check_nonexistent(self, **kwargs: Any) -> None:
        nonexistent_attributes = set(kwargs) - set(self.__dict__)
        if nonexistent_attributes:
            raise KeyError(
                f"The following attributes do not exist in"
                f" {self.__class__}: {', '.join(nonexistent_attributes)}"
            )

    def copy(self, **kwargs: Any) -> "ReuseInfo":
        """Return a copy of ReuseInfo, replacing the values of attributes with
        the values from *kwargs*.
        """
        self._check_nonexistent(**kwargs)
        new_kwargs = {}
        for key, value in self.__dict__.items():
            new_kwargs[key] = kwargs.get(key, value)
        return self.__class__(**new_kwargs)  # type: ignore

    def union(self, *other: "ReuseInfo") -> "ReuseInfo":
        """Return a new instance of ReuseInfo where all set attributes are equal
        to the union of the set in *self* and the set(s) in *other*.

        All non-set attributes are set to their values in *self*.

        >>> one = ReuseInfo(copyright_notices={CopyrightNotice("Jane Doe")},
        ...           source_path="foo.py")
        >>> two = ReuseInfo(copyright_notices={CopyrightNotice("John Doe")},
        ...           source_path="bar.py")
        >>> result = one.union(two)
        >>> print([notice.name for notice in sorted(result.copyright_notices)])
        ['Jane Doe', 'John Doe']
        >>> print(result.source_path)
        foo.py
        """
        if not other:
            return self
        new_kwargs = {}
        for key, attr_val in self.__dict__.items():
            if isinstance(attr_val, set):
                new_kwargs[key] = attr_val.union(
                    *(getattr(info, key) for info in other)
                )
            else:
                new_kwargs[key] = attr_val
        return self.__class__(**new_kwargs)  # type: ignore

    def contains_copyright_or_licensing(self) -> bool:
        """Either *spdx_expressions* or *copyright_notices* is non-empty."""
        return bool(self.spdx_expressions or self.copyright_notices)

    def contains_copyright_xor_licensing(self) -> bool:
        """One of *spdx_expressions* or *copyright_notices* is non-empty."""
        return bool(self.spdx_expressions) ^ bool(self.copyright_notices)

    def contains_info(self) -> bool:
        """Any field except *path*, *source_path* and *source_type* is
        non-empty.
        """
        keys = {
            key
            for key in self.__dict__
            if key not in ("path", "source_path", "source_type")
        }
        return any(self.__dict__[key] for key in keys)

    def __bool__(self) -> bool:
        return any(self.__dict__.values())

    def __or__(self, value: "ReuseInfo") -> "ReuseInfo":
        return self.union(value)


# REUSE-IgnoreEnd
