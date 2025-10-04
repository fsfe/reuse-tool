# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2022 Carmen Bianca Bakker <carmenbianca@fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2022 Nico Rikken <nico.rikken@fsfe.org>
# SPDX-FileCopyrightText: 2022 Pietro Albini <pietro.albini@ferrous-systems.com>
# SPDX-FileCopyrightText: 2024 Rivos Inc.
# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for reuse.copyright"""

import re
from typing import cast
from unittest import mock

import pytest

from reuse.copyright import (
    _LICENSING,
    COPYRIGHT_NOTICE_PATTERN,
    CopyrightNotice,
    CopyrightPrefix,
    FourDigitString,
    ReuseInfo,
    SourceType,
    SpdxExpression,
    YearRange,
    YearRangeSeparator,
)
from reuse.exceptions import CopyrightNoticeParseError, YearRangeParseError

# pylint: disable=too-many-lines

F = FourDigitString

# REUSE-IgnoreStart


class TestYearRangeInit:
    """Tests for YearRange initialisation."""

    def test_no_start(self):
        """It is invalid to have no start year."""
        # pylint: disable=no-value-for-parameter
        with pytest.raises(TypeError):
            YearRange(end="2017")  # type: ignore[call-arg]

    def test_populate_end_if_separator(self):
        """If a separator is defined, but end is not defined, set end to an
        empty string.
        """
        years = YearRange(F("2017"), "-")
        assert years.end == ""


class TestYearRangeFromString:
    """Tests for YearRange.from_string."""

    def test_one_year(self):
        """The simple case, given a four-digit string."""
        years = YearRange.from_string("2017")
        assert years == YearRange(F("2017"))
        assert years.original == "2017"

    @pytest.mark.parametrize(
        "separator",
        YearRangeSeparator.__args__,  # type: ignore
    )
    def test_full_range(self, separator):
        """For all available separators, parse a range."""
        value = f"2017{separator}2020"
        years = YearRange.from_string(value)
        assert years.start == "2017"
        assert years.separator == separator
        assert years.end == "2020"
        assert years.original == value

    @pytest.mark.parametrize(
        "separator",
        YearRangeSeparator.__args__,  # type: ignore
    )
    def test_spacing_around_separator(self, separator):
        """If there is spacing around the separator, ignore that."""
        value = f"2017 {separator} 2020"
        years = YearRange.from_string(value)
        assert years.start == "2017"
        assert years.separator == separator
        assert years.end == "2020"
        assert years.original == value

    def test_end_is_word(self):
        """The end date is a word like 'Present'."""
        years = YearRange.from_string("2017--Present")
        assert years == YearRange(F("2017"), "--", "Present")
        assert years.original == "2017--Present"

    def test_start_and_separator(self):
        """Parse start and separator."""
        years = YearRange.from_string("2017--")
        assert years == YearRange(F("2017"), "--")
        assert years.original == "2017--"

    @pytest.mark.parametrize(
        "text",
        [
            "0",
            "123",
            "12345",
            "12345678",
            "-",
            "--",
            "a 1234",
            "abcd",
            "Present-2017",
            "1234 a",
            "1234 5678",
            "123-4",
            "-1234",
            "2017- 2019",
            "2017 -2019",
            "2017 - ",
            "2017- ",
            "2017 -",
            # This one is tricky. I disallow it because it would otherwise catch
            # something like: Copyright Jane Doe 2017 - some rights reserved.
            "2017 - Present",
        ],
    )
    def test_invalid_ranges(self, text):
        """Invalid ranges cannot be parsed."""
        with pytest.raises(YearRangeParseError):
            YearRange.from_string(text)  # type: ignore[arg-type]


class TestYearRangeTupleFromString:
    """Tests for YearRange.tuple_from_string."""

    def test_simple(self):
        """Try various ways of separating year ranges."""
        text = (
            "2017, 2018,, 2019 2020 ,2021 , 2022  2023\t2024,,2025 2026--2027"
        )
        result = YearRange.tuple_from_string(text)
        assert result == tuple(
            [YearRange(F(str(num))) for num in range(2017, 2026)]
            + [YearRange(F("2026"), "--", "2027")]
        )

    @pytest.mark.parametrize(
        "separator",
        YearRangeSeparator.__args__,  # type: ignore
    )
    def test_spacing_around_separator(self, separator):
        """A year range with a separator surrounded by whitespace is not split
        into two year ranges.
        """
        result = YearRange.tuple_from_string(f"2017 {separator} 2019")
        assert result == (YearRange(F("2017"), separator, "2019"),)

    def test_ambiguous_year_range(self):
        """Sometimes the spacing around the year range does not make it clear
        what the intended range is. For extracting from tuples, the spacing must
        _always_ be on both sides.
        """
        result = YearRange.tuple_from_string("2017- 2019")
        assert result == (YearRange(F("2017"), "-"), YearRange(F("2019")))
        with pytest.raises(YearRangeParseError):
            YearRange.tuple_from_string("2017 -2019")


class TestYearRangeToString:
    """Tests for YearRange.to_string."""

    def test_one_year(self):
        """Create a string for a single-item year range."""
        years = YearRange(F("2017"))
        assert years.to_string() == "2017"

    def test_year_and_separator(self):
        """Create a string for a year and a separator, with no end date."""
        years = YearRange(F("2017"), "--")
        assert years.to_string() == "2017--"

    def test_full_range(self):
        """Given a range between two years, create a full string."""
        years = YearRange(F("2017"), "-", "2025")
        assert years.to_string() == "2017-2025"

    def test_no_separator(self):
        """Given two years but no separator, add a separator anyway."""
        years = YearRange(F("2017"), end="2025")
        assert years.to_string() == "2017-2025"

    def test_end_is_word(self):
        """The end year can be a word like 'Present'."""
        years = YearRange(F("2017"), "--", "Present")
        assert years.to_string() == "2017--Present"

    def test_original(self):
        """If an original string exists, return it."""
        years = YearRange(F("2017"))
        object.__setattr__(years, "original", "Foo")
        assert years.to_string() != "Foo"
        assert years.to_string(original=True) == "Foo"

    def test_str(self):
        """str() is identical to to_string."""
        years = YearRange(F("2017"), "-", "2025")
        object.__setattr__(years, "original", "Foo")
        assert str(years) == years.to_string()


class TestYearRangeSorting:
    """Test whether YearRange sorts correctly."""

    def test_no_type_mixing(self):
        """Can only compare YearRange objects."""
        with pytest.raises(TypeError):
            _ = YearRange(F("2017")) > "2018"  # type: ignore[operator]

    @pytest.mark.parametrize(
        "first,second",
        [
            ("2017", "2018"),
            ("0001", "2017"),
            ("2017-2019", "2018"),
            ("2017", "2017-2019"),
            ("2017", "2017-"),
            ("2017-2018", "2017-2019"),
            ("2017-2022", "2019-2021"),
            ("2017-2022", "2019-2025"),
            ("2017-2019", "2017-Present"),
            ("2017-2019", "2017-0abcd"),
        ],
    )
    def test_less_than(self, first, second):
        """First is less than second."""
        first = YearRange.from_string(first)
        second = YearRange.from_string(second)
        assert first.__lt__(second)  # pylint: disable=unnecessary-dunder-call
        assert not second.__lt__(  # pylint: disable=unnecessary-dunder-call
            first
        )
        assert first < second
        assert second > first

    @pytest.mark.parametrize(
        "first,second",
        [
            ("2017", "2017"),
            ("2017-2018", "2017-2018"),
            ("2017-Present", "2017-Present"),
            ("2017-2018", "2017--2018"),
            ("2017-", "2017--"),
        ],
    )
    def test_equal(self, first, second):
        """First is equal to second."""
        first = YearRange.from_string(first)
        second = YearRange.from_string(second)
        assert first == second


class TestYearRangeCompact:
    """Tests for YearRange.compact."""

    def test_three_subsequent(self):
        """A simple case where three years compact into a single range."""
        result = YearRange.compact(
            [YearRange(F("2017")), YearRange(F("2018")), YearRange(F("2019"))]
        )
        assert result == (YearRange(F("2017"), end="2019"),)

    def test_two_subsequent(self):
        """Do not compact a two subsequent years into one range."""
        result = YearRange.compact([YearRange(F("2017")), YearRange(F("2018"))])
        assert result == (YearRange(F("2017")), YearRange(F("2018")))

    def test_unsorted(self):
        """An unsorted list is also compacted correctly."""
        result = YearRange.compact(
            [YearRange(F("2019")), YearRange(F("2017")), YearRange(F("2018"))]
        )
        assert result == (YearRange(F("2017"), end="2019"),)

    @pytest.mark.parametrize(
        "years",
        [
            ["2017", "2018-2016"],
            ["2017-2015", "2018"],
            ["2017-2015", "2018-2016"],
            ["2017-Present", "2018-2016"],
            ["2017-2016", "2019-Present"],
        ],
    )
    def test_end_less_than_start(self, years):
        """If the end of a range is less than the start, handle that case by not
        compacting it."""
        years = tuple(YearRange.from_string(item) for item in years)
        result = YearRange.compact(years)
        assert result == years

    def test_remove_useless_range(self):
        """If a range has a length of 0, compact it."""
        result = YearRange.compact([YearRange(F("2017"), end="2017")])
        assert result == (YearRange(F("2017")),)

    @pytest.mark.parametrize(
        "text",
        ["2017", "2017-2020", "2017-Present"],
    )
    def test_range_repeated(self, text):
        """If a range is repeated, only return one."""
        years = YearRange.from_string(text)
        result = YearRange.compact([years, years])
        assert result == (years,)

    def test_two_subsequent_ranges(self):
        """A case where two ranges can be glued together."""
        result = YearRange.compact(
            [YearRange(F("2017"), end="2019"), YearRange(F("2020"), end="2021")]
        )
        assert result == (YearRange(F("2017"), end="2021"),)

    def test_encompassed(self):
        """A case where a range is contained within another."""
        result = YearRange.compact(
            [YearRange(F("2017"), end="2022"), YearRange(F("2019"), end="2021")]
        )
        assert result == (YearRange(F("2017"), end="2022"),)

    def test_partial_overlap(self):
        """If there is partial overlap between ranges, compact them."""
        result = YearRange.compact(
            [YearRange(F("2017"), end="2022"), YearRange(F("2019"), end="2025")]
        )
        assert result == (YearRange(F("2017"), end="2025"),)

    @pytest.mark.parametrize(
        "text_list,expected",
        [
            (("2017-2022", "2020-2022"), "2017-2022"),
            (("2017-2022", "2018-2022", "2020-2022"), "2017-2022"),
            (("2017-Present", "2020-Present"), "2017-Present"),
            (
                ("2017-Present", "2018-Present", "2020-Present"),
                "2017-Present",
            ),
            (("2017-", "2019-"), "2017-"),
        ],
    )
    def test_same_end(self, text_list, expected):
        """If the end of various ranges is the same, pick the lowest start."""
        result = YearRange.compact(
            [YearRange.from_string(item) for item in text_list]
        )
        assert result == (YearRange.from_string(expected),)

    @pytest.mark.parametrize(
        "text_list",
        [
            ("2017-2020", "2018-Present"),
            ("2017-Present", "2018-2020"),
            ("2017", "2017-Present"),
            ("2017", "2017-"),
        ],
    )
    def test_leave_string_end_alone(self, text_list):
        """Don't really bother compacting int-y ends with string-y ends."""
        years = tuple(YearRange.from_string(item) for item in text_list)
        result = YearRange.compact(years)
        assert result == years

    def test_different_string_ends(self):
        """Do not compact ranges which have different string-y ends."""
        years = (
            YearRange(F("2017"), end="Present"),
            YearRange(F("2018"), end="Now"),
        )
        result = YearRange.compact(years)
        assert result == years


class TestCopyrightNoticeFromString:
    """Tests for CopyrightNotice.from_string."""

    def test_uses_from_match(self, monkeypatch):
        """from_string uses from_match under the hood for 99% of the logic."""
        text = "SPDX-FileCopyrightText: 2017 Jane Doe <jane@example.com>"
        expected = CopyrightNotice(
            "Jane Doe <jane@example.com>",
            years=(YearRange(F("2017")),),
        )

        from_match = mock.create_autospec(CopyrightNotice.from_match)
        from_match.return_value = expected
        monkeypatch.setattr(
            "reuse.copyright.CopyrightNotice.from_match", from_match
        )
        expected_match = cast(
            re.Match[str], COPYRIGHT_NOTICE_PATTERN.fullmatch(text)
        )

        notice = CopyrightNotice.from_string(text)

        # Now the problem is that two identical re.Matches do not equal each
        # other, so I will compare some of their values, which is just about
        # close enough.
        assert len(from_match.call_args_list) == 1  # Called once
        assert len(from_match.call_args_list[0].args) == 1  # with one argument.
        used_match = cast(re.Match[str], from_match.call_args_list[0].args[0])
        assert isinstance(used_match, re.Match)
        assert repr(used_match) == repr(expected_match)
        assert used_match.groups() == expected_match.groups()
        assert used_match.re == expected_match.re

        # Check for a correct output.
        assert notice == expected

    def test_simple(self):
        """A simple case of a prefix and a copyright holder."""
        notice = CopyrightNotice.from_string("SPDX-FileCopyrightText: Jane Doe")
        assert notice == CopyrightNotice(
            "Jane Doe", prefix=CopyrightPrefix.SPDX
        )
        assert notice.original == "SPDX-FileCopyrightText: Jane Doe"

    @pytest.mark.parametrize("prefix", CopyrightPrefix)
    def test_all_prefixes(self, prefix):
        """All prefixes are correctly recognised."""
        value = f"{prefix.value} Jane Doe"
        notice = CopyrightNotice.from_string(value)
        assert notice == CopyrightNotice("Jane Doe", prefix=prefix)
        assert notice.original == value

    @pytest.mark.parametrize("prefix", CopyrightPrefix)
    def test_spaces_after_copyright(self, prefix):
        """A space is not necessary after most copyright prefixex, like '©2017
        Jane Doe'. However, 'CopyrightJane Doe' is not valid.
        """
        if prefix == CopyrightPrefix.STRING:
            with pytest.raises(CopyrightNoticeParseError):
                CopyrightNotice.from_string(f"{prefix.value}Jane Doe")

        else:
            notice = CopyrightNotice.from_string(f"{prefix.value}Jane Doe")
            if prefix in {
                CopyrightPrefix.SPDX_STRING,
                CopyrightPrefix.SNIPPET_STRING,
            }:
                assert notice.name == "CopyrightJane Doe"
                assert notice.prefix in {
                    CopyrightPrefix.SPDX,
                    CopyrightPrefix.SNIPPET,
                }
            else:
                assert notice == CopyrightNotice("Jane Doe", prefix=prefix)

    def test_spacing_after_name(self):
        """Spacing after the name should be stripped."""
        value = "SPDX-FileCopyrightText: Jane Doe \t"
        notice = CopyrightNotice.from_string(value)
        assert notice == CopyrightNotice("Jane Doe")
        assert notice.original == value

    @pytest.mark.parametrize(
        "text,prefix",
        [
            ("SPDX-FileCopyrightText:(C)", CopyrightPrefix.SPDX_C),
            ("SPDX-FileCopyrightText:  (C)", CopyrightPrefix.SPDX_C),
            ("SPDX-FileCopyrightText:©", CopyrightPrefix.SPDX_SYMBOL),
            (
                "SPDX-FileCopyrightText:Copyright(C)",
                CopyrightPrefix.SPDX_STRING_C,
            ),
            (
                "SPDX-FileCopyrightText:  Copyright(C)",
                CopyrightPrefix.SPDX_STRING_C,
            ),
            (
                "SPDX-FileCopyrightText:  Copyright  (C)",
                CopyrightPrefix.SPDX_STRING_C,
            ),
            (
                "SPDX-FileCopyrightText:Copyright©",
                CopyrightPrefix.SPDX_STRING_SYMBOL,
            ),
            (
                "SPDX-FileCopyrightText:  Copyright©",
                CopyrightPrefix.SPDX_STRING_SYMBOL,
            ),
            (
                "SPDX-FileCopyrightText:  Copyright  ©",
                CopyrightPrefix.SPDX_STRING_SYMBOL,
            ),
            ("Copyright(C)", CopyrightPrefix.STRING_C),
            ("Copyright  (C)", CopyrightPrefix.STRING_C),
            ("Copyright©", CopyrightPrefix.STRING_SYMBOL),
            ("Copyright  ©", CopyrightPrefix.STRING_SYMBOL),
        ],
    )
    def test_unexpected_spacing_in_prefix(self, text, prefix):
        """When there is unexpected spacing in the prefix, recognise the prefix
        anyway.
        """
        notice = CopyrightNotice.from_string(f"{text} Jane Doe")
        assert notice == CopyrightNotice("Jane Doe", prefix=prefix)

    def test_with_year(self):
        """If a year is given, parse it correctly."""
        notice = CopyrightNotice.from_string("Copyright 2017 Jane Doe")
        assert notice == CopyrightNotice(
            "Jane Doe",
            prefix=CopyrightPrefix.STRING,
            years=(YearRange(F("2017")),),
        )

    @pytest.mark.parametrize(
        "year",
        [
            "2017, 2022",
            "2017,2022",
            "2017 2022",
            "2017 , 2022",
            "2017 2022,",
            "2017,2022,",
            "2017, 2022,",
        ],
    )
    def test_two_years_separated(self, year):
        """There are various ways of separating years with spaces and commas.
        They are all valid.
        """
        notice = CopyrightNotice.from_string(f"Copyright {year} Jane Doe")
        assert notice == CopyrightNotice(
            "Jane Doe",
            prefix=CopyrightPrefix.STRING,
            years=(YearRange(F("2017")), YearRange(F("2022"))),
        )

    @pytest.mark.parametrize(
        "text",
        [
            "12345678",
            "123",
            "12345",
            "1234.5678",
            "Present-1234",
        ],
    )
    def test_not_a_year_range(self, text):
        """If something is not a year range, do not recognise it as such."""
        notice = CopyrightNotice.from_string(f"Copyright {text} Jane Doe")
        assert notice == CopyrightNotice(
            f"{text} Jane Doe", prefix=CopyrightPrefix.STRING
        )

    @pytest.mark.parametrize(
        "text",
        [
            "(C) Jane Doe",
            "2017 Jane Doe",
            "Copyrighted Jane Doe",
            "copyright jane doe",
        ],
    )
    def test_not_a_notice(self, text):
        """If something is not a notice, do not recognise it as such."""
        with pytest.raises(CopyrightNoticeParseError):
            CopyrightNotice.from_string(text)

    @pytest.mark.parametrize("year", ["2017", "2017,"])
    def test_no_spaces_after_year(self, year):
        """If there is no space after the year, it is part of the name."""
        notice = CopyrightNotice.from_string(f"Copyright {year}Jane Doe")
        assert notice == CopyrightNotice(
            f"{year}Jane Doe", prefix=CopyrightPrefix.STRING
        )

    def test_year_range(self):
        """A simple test for making sure that year ranges are parsed. Otherwise
        assume that YearRange.from_string works correctly.
        """
        notice = CopyrightNotice.from_string(
            "Copyright 2017, 2020-2022, 2024--Present Jane Doe"
        )
        assert notice == CopyrightNotice(
            "Jane Doe",
            prefix=CopyrightPrefix.STRING,
            years=(
                YearRange(F("2017")),
                YearRange(F("2020"), "-", "2022"),
                YearRange(F("2024"), "--", "Present"),
            ),
        )

    @pytest.mark.parametrize("year", [" 2017", ", 2017"])
    def test_year_after_name(self, year):
        """The year can be at the end instead of at the beginning."""
        notice = CopyrightNotice.from_string(f"Copyright Jane Doe{year}")
        assert notice == CopyrightNotice(
            "Jane Doe",
            prefix=CopyrightPrefix.STRING,
            years=(YearRange(F("2017")),),
        )

    def test_years_around_name(self):
        """There could be years in multiple places in the notice."""
        notice = CopyrightNotice.from_string("Copyright 2017 Jane Doe 2019")
        assert notice == CopyrightNotice(
            "Jane Doe",
            prefix=CopyrightPrefix.STRING,
            years=(YearRange(F("2017")), YearRange(F("2019"))),
        )

    def test_name_around_years(self):
        """There could be name information around where the year appears."""
        notice = CopyrightNotice.from_string(
            "Copyright Jane Doe 2017, some rights reserved"
        )
        assert notice == CopyrightNotice(
            "Jane Doe, some rights reserved",
            prefix=CopyrightPrefix.STRING,
            years=(YearRange(F("2017")),),
        )

    def test_dash_after_year(self):
        """An isolated dash after a year should be part of the name, not the
        year.
        """
        notice = CopyrightNotice.from_string(
            "Copyright Jane Doe 2017 - All Rights Reserved"
        )
        assert notice == CopyrightNotice(
            "Jane Doe - All Rights Reserved",
            prefix=CopyrightPrefix.STRING,
            years=(YearRange(F("2017")),),
        )


class TestCopyrightNoticeToString:
    """Tests for CopyrightNotice.to_string."""

    def test_only_name(self):
        """The simple case where only a copyright holder is provided."""
        notice = CopyrightNotice("Jane Doe")
        assert notice.to_string() == "SPDX-FileCopyrightText: Jane Doe"

    def test_different_copyright_prefix(self):
        """When changing prefix, the resulting string is different."""
        notice = CopyrightNotice("Jane Doe", prefix=CopyrightPrefix.STRING)
        assert notice.to_string() == "Copyright Jane Doe"

    def test_single_year(self):
        """A simple case where there is one year range."""
        notice = CopyrightNotice("Jane Doe", years=(YearRange(F("2017")),))
        assert notice.to_string() == "SPDX-FileCopyrightText: 2017 Jane Doe"

    def test_two_years(self):
        """A case where there are two year ranges."""
        notice = CopyrightNotice(
            "Jane Doe",
            years=(
                YearRange(F("2017")),
                YearRange(F("2020"), "--", "2022"),
            ),
        )
        assert (
            notice.to_string()
            == "SPDX-FileCopyrightText: 2017, 2020--2022 Jane Doe"
        )

    def test_original(self):
        """If an original string exists, return it."""
        notice = CopyrightNotice("Jane Doe")
        object.__setattr__(notice, "original", "Foo")
        assert notice.to_string() != "Foo"
        assert notice.to_string(original=True) == "Foo"

    def test_str(self):
        """str() is identical to to_string."""
        notice = CopyrightNotice("Jane Doe")
        object.__setattr__(notice, "original", "Foo")
        assert str(notice) == notice.to_string()


class TestCopyrightNoticeOrder:
    """Tests for sorting CopyrightNotices."""

    def test_year_before_name(self):
        """The years have higher sorting priority than the names."""
        assert CopyrightNotice(
            "Alice", years=(YearRange(F("2025")),)
        ) > CopyrightNotice("Bob", years=(YearRange(F("2020")),))

    def test_only_names(self):
        """If there are only names, sort by names."""
        assert CopyrightNotice("Alice") < CopyrightNotice("Bob")

    def test_different_year_range_length(self):
        """If all is equal except one *years* has more items in the tuple,
        then the bigger tuple is greater than the smaller one.
        """
        assert CopyrightNotice(
            "Alice", years=(YearRange(F("2024")), YearRange(F("2025")))
        ) > CopyrightNotice(
            "Bob",
            years=(YearRange(F("2024")),),
        )

    def test_years_before_no_years(self):
        """If no years are defined, sort them at the end."""
        assert CopyrightNotice(
            "Alice", years=(YearRange(F("2025")),)
        ) < CopyrightNotice("Bob")

    def test_only_prefix_different(self):
        """If only the prefix is different, sort alphabetically by prefix."""
        assert CopyrightNotice(
            "Jane", prefix=CopyrightPrefix.STRING
        ) < CopyrightNotice("Jane", prefix=CopyrightPrefix.SPDX)


class TestCopyrightNoticeMerge:
    """Tests for CopyrightNotice.merge."""

    def test_single(self):
        """Given a single notice, return it."""
        notices = {CopyrightNotice("Jane Doe")}
        result = CopyrightNotice.merge(notices)
        assert result == notices

    def test_empty(self):
        """Given an empty iterable, return an empty set."""
        result = CopyrightNotice.merge([])
        assert result == set()

    def test_two_different(self):
        """Given two different notices, return them both."""
        notices = {CopyrightNotice("Jane Doe"), CopyrightNotice("John Doe")}
        result = CopyrightNotice.merge(notices)
        assert result == notices

    def test_two_with_years(self):
        """Given two identical notices apart from the years, return one with the
        years compacted.
        """
        notices = {
            CopyrightNotice.from_string("Copyright 2017 Jane Doe"),
            CopyrightNotice.from_string("Copyright 2018 Jane Doe"),
        }
        result = CopyrightNotice.merge(notices)
        assert result == {
            CopyrightNotice.from_string("Copyright 2017, 2018 Jane Doe")
        }

    def test_two_different_prefix(self):
        """If the prefixes of two notices are different, choose the highest
        priority prefix.
        """
        members = list(CopyrightPrefix)
        for i, prefix1 in enumerate(members):
            for prefix2 in members[i:]:
                notices = {
                    CopyrightNotice.from_string(f"{prefix1.value} Jane Doe"),
                    CopyrightNotice.from_string(f"{prefix2.value} Jane Doe"),
                }
                result = CopyrightNotice.merge(notices)
                assert result == {
                    CopyrightNotice.from_string(f"{prefix1.value} Jane Doe")
                }

    def test_two_same_prefix_one_different(self):
        """If two prefixes are identical, and one prefix is not, merge into the
        most common prefix.
        """
        for prefix1 in CopyrightPrefix:
            for prefix2 in CopyrightPrefix:
                notices = [
                    CopyrightNotice.from_string(f"{prefix1.value} Jane Doe"),
                    CopyrightNotice.from_string(f"{prefix1.value} Jane Doe"),
                    CopyrightNotice.from_string(f"{prefix2.value} Jane Doe"),
                ]
                result = CopyrightNotice.merge(notices)
                assert result == {
                    CopyrightNotice.from_string(f"{prefix1.value} Jane Doe")
                }


class TestSpdxExpressionGetExpressionAndIsValid:
    """Tests for the property :attr:`SpdxExpression._expression`.
    Simultaneously, test :attr:`SpdxExpression.is_valid`.
    """

    @pytest.mark.parametrize(
        "text",
        [
            "GPL-3.0-or-later",
            "GPL-3.0-or-later OR CC0-1.0",
            "Apache-2.0 AND 0BSD",
            "(MIT OR 0BSD) AND GPL-3.0-or-later",
        ],
    )
    def test_valid(self, text):
        """A valid expression is correctly parsed."""
        # pylint: disable=protected-access
        expression = SpdxExpression(text)
        assert expression._expression == _LICENSING.parse(text)
        assert expression.is_valid

    @pytest.mark.parametrize(
        "text",
        [
            "MIT OR",
            "MIT AND",
            "OR MIT",
            "AND MIT",
            "(MIT AND 0BSD",
            "<expression>",
            "MIT 0BSD",
        ],
    )
    def test_invalid(self, text):
        """An invalid expression returns None."""
        # pylint: disable=protected-access
        expression = SpdxExpression(text)
        assert expression._expression is None
        assert not expression.is_valid


class TestSpdxExpressionLicenses:
    """Tests for the property :attr:`SpdxExpression.licenses`."""

    def test_valid(self):
        """A valid expression returns all unique licenses in order of
        appearance.
        """
        expression = SpdxExpression("MIT AND MIT OR 0BSD")
        assert expression.licenses == ["MIT", "0BSD"]

    def test_invalid(self):
        """An invalid expression returns itself in a list."""
        expression = SpdxExpression("0BSD AND")
        assert expression.licenses == ["0BSD AND"]


class TestSpdxExpressionCombine:
    """Tests for :classmethod:`SpdxExpression.combine`."""

    def test_valid(self):
        """Valid expressions are smartly combined."""
        assert SpdxExpression.combine(
            [
                SpdxExpression("MIT"),
                SpdxExpression(" 0BSD  "),
                SpdxExpression("GPL-3.0-or-later  OR Apache-2.0"),
            ]
        ) == SpdxExpression("MIT AND 0BSD AND (GPL-3.0-or-later OR Apache-2.0)")

    def test_invalid(self):
        """Invalid expressions are simply combined by AND operators."""
        assert SpdxExpression.combine(
            [SpdxExpression("0BSD  OR"), SpdxExpression("MIT")]
        ) == SpdxExpression("(0BSD  OR) AND (MIT)")


class TestSpdxExpressionSimplify:
    """Tests for :meth:`SpdxExpression.simplify`."""

    def test_valid(self):
        """A valid expression is correctly simplified."""
        expression = SpdxExpression(
            "(MIT OR MIT) AND (GPL-3.0-or-later AND 0BSD) AND GPL-3.0-or-later"
        )
        assert expression.simplify() == SpdxExpression(
            "0BSD AND GPL-3.0-or-later AND MIT"
        )

    def test_invalid(self):
        """An invalid expression is returned as-is when simplified."""
        text = "MIT OR AND (0BSD OR 0BSD)"
        assert SpdxExpression(text) == SpdxExpression(text)


class TestSpdxExpressionStr:
    """Tests for SpdxExpression.__str__."""

    def test_valid(self):
        """A valid expression is returned as string."""
        expression = SpdxExpression("0BSD  AND    MIT OR CC0-1.0")
        assert str(expression) == "(0BSD AND MIT) OR CC0-1.0"

    def test_invalid(self):
        """An invalid expression is returned as-is."""
        expression = SpdxExpression("0BSD AND")
        assert str(expression) == "0BSD AND"


class TestSpdxExpressionEq:
    """Tests for SpdxExpression.__eq__."""

    def test_both_invalid(self):
        """If both expressions are invalid, their texts are simply compared."""
        assert SpdxExpression("MIT OR") != SpdxExpression("MIT OR ")
        assert SpdxExpression("MIT OR") == SpdxExpression("MIT OR")

    @pytest.mark.parametrize(
        "text",
        [
            "MIT AND 0BSD",
            "MIT  AND  0BSD ",
            "(MIT AND 0BSD)",
        ],
    )
    def test_valid(self, text):
        """If both expressions are valid, the expressions are compared."""
        assert SpdxExpression(text) == SpdxExpression("MIT AND 0BSD")

    def test_not_spdx_expression(self):
        """Something that isn't an SpdxExpression is never equal to it."""
        assert SpdxExpression("MIT") != "MIT"


class TestSpdxExpressionSort:
    """Tests for SpdxExpression.__lt__."""

    @pytest.mark.parametrize(
        "one,two",
        [
            ("0BSD", "MIT"),
            ("0BSD AND MIT", "MIT AND 0BSD"),
            ("0BSD AND", "MIT"),
            ("0BSD", "MIT AND"),
            ("0BSD AND", "MIT AND"),
        ],
    )
    def test_simple(self, one, two):
        """The strings of expressions are correctly compared."""
        assert SpdxExpression(one) < SpdxExpression(two)

    def test_not_spdx_expression(self):
        """Something that isn't an SpdxExpression can't be sorted relative to
        it.
        """
        with pytest.raises(TypeError):
            bool(SpdxExpression("MIT") < "MIT")


@pytest.mark.parametrize(
    "args",
    [
        {"spdx_expressions": {"GPL-3.0-or-later"}, "copyright_notices": set()},
        {
            "spdx_expressions": set(),
            "copyright_notices": {
                CopyrightNotice.from_string(
                    "SPDX-FileCopyrightText: 2017 Jane Doe"
                )
            },
        },
        {
            "spdx_expressions": {"GPL-3.0-or-later"},
            "copyright_notices": {
                CopyrightNotice.from_string(
                    "SPDX-FileCopyrightText: 2017 Jane Doe"
                )
            },
        },
    ],
)
def test_reuse_info_contains_copyright_or_licensing(args):
    """If either spdx_expressions or copyright_notices is truthy, then expect
    True.
    """
    info = ReuseInfo(**args)
    assert info.contains_copyright_or_licensing()


def test_reuse_info_contains_copyright_or_licensing_empty():
    """If the ReuseInfo object is completely empty, expect False."""
    info = ReuseInfo()
    assert not info.contains_copyright_or_licensing()


def test_reuse_info_contains_copyright_or_licensing_other_truthy():
    """If another attribute is truthy, still expect False."""
    info = ReuseInfo(contributor_lines={"SPDX-FileContributor: 2017 Jane Doe"})
    assert not info.contains_copyright_or_licensing()


def test_reuse_info_contains_copyright_xor_licensing():
    """A simple xor version of the previous function."""
    assert not ReuseInfo().contains_copyright_xor_licensing()
    assert not ReuseInfo(
        spdx_expressions={SpdxExpression("MIT")},
        copyright_notices={CopyrightNotice.from_string("Copyright Jane Doe")},
    ).contains_copyright_xor_licensing()
    assert ReuseInfo(
        spdx_expressions={SpdxExpression("MIT")}
    ).contains_copyright_xor_licensing()
    assert ReuseInfo(
        copyright_notices={CopyrightNotice.from_string("Copyright Jane Doe")}
    ).contains_copyright_xor_licensing()


def test_reuse_info_contains_info_simple():
    """If any of the non-source files are truthy, expect True."""
    assert ReuseInfo(spdx_expressions={SpdxExpression("MIT")}).contains_info()
    assert ReuseInfo(
        copyright_notices={
            CopyrightNotice.from_string("SPDX-FileCopyrightText: 2017 Jane Doe")
        }
    ).contains_info()
    assert ReuseInfo(
        contributor_lines={"SPDX-FileContributor: 2017 John Doe"}
    ).contains_info()


def test_reuse_info_contains_info_empty():
    """If the ReuseInfo object is empty, expect False."""
    info = ReuseInfo()
    assert not info.contains_info()


def test_reuse_info_contains_info_source_truthy():
    """If any of the source information is truthy, still expect False."""
    assert not ReuseInfo(source_path="foo.py").contains_info()
    assert not ReuseInfo(source_type=SourceType.FILE_HEADER).contains_info()


def test_reuse_info_copy_simple():
    """Get a copy of ReuseInfo with one field replaced."""
    info = ReuseInfo(
        spdx_expressions={SpdxExpression("GPL-3.0-or-later")},
        copyright_notices={
            CopyrightNotice.from_string("Copyright 2017 Jane Doe")
        },
        source_path="foo",
    )
    new_info = info.copy(source_path="bar")
    assert info != new_info
    assert info.spdx_expressions == new_info.spdx_expressions
    assert info.copyright_notices == new_info.copyright_notices
    assert info.source_path != new_info.source_path
    assert new_info.source_path == "bar"


def test_reuse_info_copy_nonexistent_attribute():
    """
    Expect a KeyError when trying to copy a nonexistent field into ReuseInfo.
    """
    info = ReuseInfo()
    with pytest.raises(KeyError):
        info.copy(foo="bar")


class TestReuseInfoUnion:
    """Tests for ReuseInfo.union."""

    def test_simple(self):
        """
        Get a union of ReuseInfo with one field merged and one remaining equal.
        """
        info1 = ReuseInfo(
            copyright_notices={
                CopyrightNotice.from_string("Copyright 2017 Jane Doe")
            },
            source_path="foo",
        )
        info2 = ReuseInfo(
            copyright_notices={
                CopyrightNotice.from_string("Copyright 2017 John Doe")
            },
            source_path="bar",
        )
        new_info = info1 | info2
        # union and __or__ are equal
        assert new_info == info1.union(info2)
        assert sorted(new_info.copyright_notices) == [
            CopyrightNotice.from_string("Copyright 2017 Jane Doe"),
            CopyrightNotice.from_string("Copyright 2017 John Doe"),
        ]
        assert new_info.source_path == "foo"

    def test_none(self):
        """If no argument is provided, nothing changes."""
        info = ReuseInfo(copyright_notices={CopyrightNotice("Jane Doe")})
        result = info.union()
        assert result == info

    def test_multiple(self):
        """If multi arguments are provided, merge them all."""
        copyright1 = CopyrightNotice("Jane Doe")
        copyright2 = CopyrightNotice("John Doe")
        copyright3 = CopyrightNotice("Alice")
        info1 = ReuseInfo(copyright_notices={copyright1})
        info2 = ReuseInfo(copyright_notices={copyright2})
        info3 = ReuseInfo(copyright_notices={copyright3})

        result = info1.union(info2, info3)
        assert result == ReuseInfo(
            copyright_notices={copyright1, copyright2, copyright3}
        )


# REUSE-IgnoreEnd
