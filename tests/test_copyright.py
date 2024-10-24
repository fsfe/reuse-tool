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

import pytest

from reuse.copyright import make_copyright_line

# REUSE-IgnoreStart


def test_make_copyright_line_simple():
    """Given a simple statement, make it a copyright line."""
    assert make_copyright_line("hello") == "SPDX-FileCopyrightText: hello"


def test_make_copyright_line_year():
    """Given a simple statement and a year, make it a copyright line."""
    assert (
        make_copyright_line("hello", year="2019")
        == "SPDX-FileCopyrightText: 2019 hello"
    )


def test_make_copyright_line_prefix_spdx():
    """Given a simple statement and prefix, make it a copyright line."""
    statement = make_copyright_line("hello", copyright_prefix="spdx")
    assert statement == "SPDX-FileCopyrightText: hello"


def test_make_copyright_line_prefix_spdx_year():
    """Given a simple statement, prefix and a year, make it a copyright line."""
    statement = make_copyright_line("hello", year=2019, copyright_prefix="spdx")
    assert statement == "SPDX-FileCopyrightText: 2019 hello"


def test_make_copyright_line_prefix_spdx_c_year():
    """Given a simple statement, prefix and a year, make it a copyright line."""
    statement = make_copyright_line(
        "hello", year=2019, copyright_prefix="spdx-c"
    )
    assert statement == "SPDX-FileCopyrightText: (C) 2019 hello"


def test_make_copyright_line_prefix_spdx_symbol_year():
    """Given a simple statement, prefix and a year, make it a copyright line."""
    statement = make_copyright_line(
        "hello", year=2019, copyright_prefix="spdx-symbol"
    )
    assert statement == "SPDX-FileCopyrightText: © 2019 hello"


def test_make_copyright_line_prefix_string_year():
    """Given a simple statement, prefix and a year, make it a copyright line."""
    statement = make_copyright_line(
        "hello", year=2019, copyright_prefix="string"
    )
    assert statement == "Copyright 2019 hello"


def test_make_copyright_line_prefix_string_c_year():
    """Given a simple statement, prefix and a year, make it a copyright line."""
    statement = make_copyright_line(
        "hello", year=2019, copyright_prefix="string-c"
    )
    assert statement == "Copyright (C) 2019 hello"


def test_make_copyright_line_prefix_spdx_string_c_year():
    """Given a simple statement, prefix and a year, make it a copyright line."""
    statement = make_copyright_line(
        "hello", year=2019, copyright_prefix="spdx-string-c"
    )
    assert statement == "SPDX-FileCopyrightText: Copyright (C) 2019 hello"


def test_make_copyright_line_prefix_spdx_string_year():
    """Given a simple statement, prefix and a year, make it a copyright line."""
    statement = make_copyright_line(
        "hello", year=2019, copyright_prefix="spdx-string"
    )
    assert statement == "SPDX-FileCopyrightText: Copyright 2019 hello"


def test_make_copyright_line_prefix_spdx_string_symbol_year():
    """Given a simple statement, prefix and a year, make it a copyright line."""
    statement = make_copyright_line(
        "hello", year=2019, copyright_prefix="spdx-string-symbol"
    )
    assert statement == "SPDX-FileCopyrightText: Copyright © 2019 hello"


def test_make_copyright_line_prefix_string_symbol_year():
    """Given a simple statement, prefix and a year, make it a copyright line."""
    statement = make_copyright_line(
        "hello", year=2019, copyright_prefix="string-symbol"
    )
    assert statement == "Copyright © 2019 hello"


def test_make_copyright_line_prefix_symbol_year():
    """Given a simple statement, prefix and a year, make it a copyright line."""
    statement = make_copyright_line(
        "hello", year=2019, copyright_prefix="symbol"
    )
    assert statement == "© 2019 hello"


def test_make_copyright_line_existing_spdx_copyright():
    """Given a copyright line, do nothing."""
    value = "SPDX-FileCopyrightText: hello"
    assert make_copyright_line(value) == value


def test_make_copyright_line_existing_other_copyright():
    """Given a non-SPDX copyright line, do nothing."""
    value = "© hello"
    assert make_copyright_line(value) == value


def test_make_copyright_line_multine_error():
    """Given a multiline argument, expect an error."""
    with pytest.raises(RuntimeError):
        make_copyright_line("hello\nworld")


# REUSE-IgnoreEnd
