# SPDX-FileCopyrightText: 2023 Carmen Bianca BAKKER <carmenbianca@fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for some core components."""

import pytest

from reuse import ReuseInfo, SourceType

# REUSE-IgnoreStart


def test_reuse_info_contains_copyright_or_licensing():
    """If either spdx_expressions or copyright_lines is truthy, expect True."""
    arguments = [
        ({"GPL-3.0-or-later"}, set()),
        (set(), "SPDX-FileCopyrightText: 2017 Jane Doe"),
        ({"GPL-3.0-or-later"}, "SPDX-FileCopyrightText: 2017 Jane Doe"),
    ]
    for args in arguments:
        info = ReuseInfo(*args)
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
        spdx_expressions={"MIT"}, copyright_lines={"Copyright Jane Doe"}
    ).contains_copyright_xor_licensing()
    assert ReuseInfo(
        spdx_expressions={"MIT"}
    ).contains_copyright_xor_licensing()
    assert ReuseInfo(
        copyright_lines={"Copyright Jane Doe"}
    ).contains_copyright_xor_licensing()


def test_reuse_info_contains_info_simple():
    """If any of the non-source files are truthy, expect True."""
    assert ReuseInfo(spdx_expressions={"MIT"}).contains_info()
    assert ReuseInfo(
        copyright_lines={"SPDX-FileCopyrightText: 2017 Jane Doe"}
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
        spdx_expressions={"GPL-3.0-or-later"},
        copyright_lines={"2017 Jane Doe"},
        source_path="foo",
    )
    new_info = info.copy(source_path="bar")
    assert info != new_info
    assert info.spdx_expressions == new_info.spdx_expressions
    assert info.copyright_lines == new_info.copyright_lines
    assert info.source_path != new_info.source_path
    assert new_info.source_path == "bar"


def test_reuse_info_copy_nonexistent_attribute():
    """
    Expect a KeyError when trying to copy a nonexistent field into ReuseInfo.
    """
    info = ReuseInfo()
    with pytest.raises(KeyError):
        info.copy(foo="bar")


def test_reuse_info_union_simple():
    """
    Get a union of ReuseInfo with one field merged and one remaining equal.
    """
    info1 = ReuseInfo(
        copyright_lines={"2017 Jane Doe"},
        source_path="foo",
    )
    info2 = ReuseInfo(copyright_lines={"2017 John Doe"}, source_path="bar")
    new_info = info1 | info2
    # union and __or__ are equal
    assert new_info == info1.union(info2)
    assert sorted(new_info.copyright_lines) == [
        "2017 Jane Doe",
        "2017 John Doe",
    ]
    assert new_info.source_path == "foo"


# REUSE-IgnoreEnd
