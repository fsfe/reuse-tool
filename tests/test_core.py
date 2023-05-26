# SPDX-FileCopyrightText: 2023 Carmen Bianca BAKKER <carmenbianca@fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for some core components."""

from reuse import ReuseInfo

# REUSE-IgnoreStart


def test_spdx_info_contains_copyright_or_licensing():
    """If either spdx_expressions or copyright_lines is truthy, expect True."""
    arguments = [
        ({"GPL-3.0-or-later"}, set()),
        (set(), "SPDX-FileCopyrightText: 2017 Jane Doe"),
        ({"GPL-3.0-or-later"}, "SPDX-FileCopyrightText: 2017 Jane Doe"),
    ]
    for args in arguments:
        info = ReuseInfo(*args)
        assert info.contains_copyright_or_licensing()


def test_spdx_info_contains_copyright_or_licensing_empty():
    """If the SpdxInfo object is completely empty, expect False."""
    info = ReuseInfo()
    assert not info.contains_copyright_or_licensing()


def test_spdx_info_contains_copyright_or_licensing_other_truthy():
    """If another attribute is truthy, still expect False."""
    info = ReuseInfo(contributor_lines={"SPDX-FileContributor: 2017 Jane Doe"})
    assert not info.contains_copyright_or_licensing()


# REUSE-IgnoreEnd
