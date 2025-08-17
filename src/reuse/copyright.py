# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2021 Alliander N.V.
# SPDX-FileCopyrightText: 2023 Carmen Bianca BAKKER <carmenbianca@fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Utilities related to the parsing and storing of copyright notices."""

import difflib
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, unique
from io import StringIO
from typing import Any, Iterable, Literal, NewType, Optional, Union, cast

from boolean.boolean import Expression

from .exceptions import CopyrightNoticeParseError, YearRangeParseError
from .i18n import _

_LOGGER = logging.getLogger(__name__)

#: A string that is four digits long.
FourDigitString = NewType("FourDigitString", str)
#: A range separator between two years.
YearRangeSeparator = Literal[
    "--",  # ascii en dash
    "–",  # en dash
    "-",  # ascii dash
]


def is_four_digits(value: str) -> Union[FourDigitString, Literal[False]]:
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
    """
    if not (result := is_four_digits(value)):
        raise ValueError(f"'{value}' is not a four-digit year.")
    return result


_YEAR_RANGE_PATTERN = re.compile(
    r"(?P<start>\d{4})"
    r"("
    r"(?P<separator>("
    + "|".join(YearRangeSeparator.__args__)  # type: ignore
    + r"))"
    r"(?P<end>\S+)?"
    r")?"
)
_YEAR_RANGE_PATTERN_ANONYMISED = re.sub(
    r"\(\?P<\w+>", "(", _YEAR_RANGE_PATTERN.pattern
)
_SYMBOL_OR_C_SUBPATTERN = r"(©|\([Cc]\))"
_STRING_SUBPATTERN = (
    r"(Copyright((\s*" + _SYMBOL_OR_C_SUBPATTERN + r")|(?=\s)))"
)
_COPYRIGHT_PATTERN = re.compile(
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
    r"((?P<years>"
    + _YEAR_RANGE_PATTERN_ANONYMISED
    + r"((\s*,\s*|\s+)"
    + _YEAR_RANGE_PATTERN_ANONYMISED
    + r")*),?\s+)?"
    r"\s*"
    r"(?P<name>.+?)"
    r"(\s+<(?P<contact>.*)>)?"
)


# TODO: In Python 3.11, turn this into a StrEnum
@unique
class CopyrightPrefix(Enum):
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


@dataclass(frozen=True)
class YearRange:
    """Represents a year range, such as '2017-2025', or '2017'. This only
    represents a single range; multiple separated ranges should be put in a
    collection.
    """

    #: The first year in the range. If it is only a single year, this is the
    #: only relevant value.
    start: FourDigitString
    #: The separator between :attr:`start` and :attr:`end`. If no value for
    #: :attr:`end` is provided, a range into infinity is implied, and
    #: :attr:`end` becomes an empty string.
    separator: Optional[YearRangeSeparator] = field(default=None, compare=False)
    #: The second year in the range. This can also be a word like 'Present'.
    #: This is bad practice, but still supported.
    end: Optional[Union[FourDigitString, str]] = None

    #: If parsed from a string, this contains the original string.
    original: Optional[str] = field(
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
        re_result = _YEAR_RANGE_PATTERN.fullmatch(value)
        if not re_result:
            raise YearRangeParseError(f"'{value}' is not a valid year range.")
        # Mypy is disabled for this because the values are enforced by the
        # regex. This could be cleaner, but would require a lot of useless code
        # to validate what the regex already enforces.
        result = cls(**re_result.groupdict())  # type: ignore
        object.__setattr__(result, "original", value)
        return result

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
    def compact(cls, ranges: Iterable["YearRange"]) -> list["YearRange"]:
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
            return []

        # TODO: In Python 3.11, use Self
        def filter_same_end(ranges: Iterable[YearRange]) -> list[YearRange]:
            """If some year ranges have the same end, then only take the ones
            with the lowest start.
            """
            result: list[YearRange] = []
            ends: defaultdict[Union[str, None], list[YearRange]] = defaultdict(
                list
            )
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
            start: int, end: str, next_range: Optional[YearRange]
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

        next_start: Optional[int] = None
        next_end: Optional[str] = None
        for next_range in ranges[1:]:
            next_start = int(next_range.start)
            next_end = (
                next_range.end
                if next_range.end is not None
                else next_range.start
            )

            current_end_int: Optional[int] = (
                int(current_end) if is_four_digits(current_end) else None
            )
            next_end_int: Optional[int] = (
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
        return compacted


@dataclass(frozen=True)
class CopyrightNotice:
    """Represents a single copyright statement."""

    #: The copyright holder.
    name: str
    #: The prefix with which the copyright statement begins.
    prefix: CopyrightPrefix = CopyrightPrefix.SPDX
    #: The dates associated with the copyright notice.
    years: tuple[YearRange, ...] = field(default_factory=tuple)
    #: The contact address of the copyright holder. This is added between
    #: brackets at the end.
    contact: Optional[str] = None

    #: If parsed from a string, this contains the original string.
    original: Optional[str] = field(
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
        re_result = _COPYRIGHT_PATTERN.fullmatch(value)
        if not re_result:
            raise CopyrightNoticeParseError(
                f"'{value}' is not a copyright notice."
            )
        re_prefix = re_result.group("prefix")
        re_prefix_lower = re_prefix.lower()
        # String-match the prefix.
        for prefix in (
            cast(CopyrightPrefix, item) for item in reversed(CopyrightPrefix)
        ):
            # lower() is used to match (C) as well as (c).
            if re_prefix_lower == prefix.value.lower():
                break
        else:
            # The prefix could not be string-matched, most likely because there
            # was unexpected spacing in the prefix. Get a close match using
            # difflib.
            matches = difflib.get_close_matches(
                re_prefix,
                # TODO: In Python 3.11, this list comprehension is not needed.
                [item.value for item in CopyrightPrefix],
                n=1,
                cutoff=0.2,
            )
            if matches:
                prefix = CopyrightPrefix(matches[0])
            else:
                # This shouldn't happen, but if no prefix could be found,
                # default to SPDX.
                prefix = CopyrightPrefix.SPDX
        years = []
        re_years = re_result.group("years")
        re_name = re_result.group("name")
        if re_years:
            # Split on comma and whitespace.
            for year in re.split(r"[,\s]", re_years):
                if not year:
                    continue
                try:
                    years.append(YearRange.from_string(year))
                except YearRangeParseError:
                    _LOGGER.exception(
                        _(
                            "Could not parse '{range}' in '{years}'."
                            " This is not supposed to happen."
                            " The program safely recovers from this with"
                            " slightly limited functionality in recognising"
                            " the year range(s)."
                        ).format(range=year, years=re_years)
                    )
                    years = []
                    re_name = f"{re_years} {re_name}"
                    break
        result = cls(
            name=re_name,
            prefix=prefix,
            years=tuple(years),
            contact=re_result.group("contact"),
        )
        object.__setattr__(result, "original", value)
        return result

    def __str__(self) -> str:
        result = StringIO()
        result.write(self.prefix.value)
        if self.years:
            result.write(" ")
            result.write(
                ", ".join((str(date_range) for date_range in self.years))
            )
        result.write(f" {self.name}")
        if self.contact:
            result.write(f" <{self.contact}>")
        return result.getvalue()

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


# TODO: In Python 3.10+, add kw_only=True
@dataclass(frozen=True)
class ReuseInfo:
    """Simple dataclass holding licensing and copyright information"""

    spdx_expressions: set[Expression] = field(default_factory=set)
    copyright_lines: set[str] = field(default_factory=set)
    contributor_lines: set[str] = field(default_factory=set)
    path: Optional[str] = None
    source_path: Optional[str] = None
    source_type: Optional[SourceType] = None

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

    def union(self, value: "ReuseInfo") -> "ReuseInfo":
        """Return a new instance of ReuseInfo where all set attributes are equal
        to the union of the set in *self* and the set in *value*.

        All non-set attributes are set to their values in *self*.

        >>> one = ReuseInfo(copyright_lines={"Jane Doe"}, source_path="foo.py")
        >>> two = ReuseInfo(copyright_lines={"John Doe"}, source_path="bar.py")
        >>> result = one.union(two)
        >>> print(sorted(result.copyright_lines))
        ['Jane Doe', 'John Doe']
        >>> print(result.source_path)
        foo.py
        """
        new_kwargs = {}
        for key, attr_val in self.__dict__.items():
            if isinstance(attr_val, set) and (other_val := getattr(value, key)):
                new_kwargs[key] = attr_val.union(other_val)
            else:
                new_kwargs[key] = attr_val
        return self.__class__(**new_kwargs)  # type: ignore

    def contains_copyright_or_licensing(self) -> bool:
        """Either *spdx_expressions* or *copyright_lines* is non-empty."""
        return bool(self.spdx_expressions or self.copyright_lines)

    def contains_copyright_xor_licensing(self) -> bool:
        """One of *spdx_expressions* or *copyright_lines* is non-empty."""
        return bool(self.spdx_expressions) ^ bool(self.copyright_lines)

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
