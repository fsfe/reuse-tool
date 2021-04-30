# SPDX-FileCopyrightText: 2021 Liam Beguin <liambeguin@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for reuse._main: addheader merge-copyrights option"""

# pylint: disable=unused-argument

from inspect import cleandoc

from reuse._main import main


def test_addheader_merge_copyrights_simple(fake_repository, stringio):
    """Add multiple headers to a file with merge copyrights."""
    simple_file = fake_repository / "foo.py"
    simple_file.write_text("pass")

    result = main(
        [
            "addheader",
            "--year",
            "2016",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Mary Sue",
            "--merge-copyrights",
            "foo.py",
        ],
        out=stringio,
    )

    assert result == 0
    assert (
        simple_file.read_text()
        == cleandoc(
            """
            # spdx-FileCopyrightText: 2016 Mary Sue
            #
            # spdx-License-Identifier: GPL-3.0-or-later

            pass
            """
        ).replace("spdx", "SPDX")
    )

    result = main(
        [
            "addheader",
            "--year",
            "2018",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Mary Sue",
            "--merge-copyrights",
            "foo.py",
        ],
        out=stringio,
    )

    assert result == 0
    assert (
        simple_file.read_text()
        == cleandoc(
            """
            # spdx-FileCopyrightText: 2016 - 2018 Mary Sue
            #
            # spdx-License-Identifier: GPL-3.0-or-later

            pass
            """
        ).replace("spdx", "SPDX")
    )


def test_addheader_merge_copyrights_multi_prefix(fake_repository, stringio):
    """Add multiple headers to a file with merge copyrights."""
    simple_file = fake_repository / "foo.py"
    simple_file.write_text("pass")

    for i in range(0, 3):
        result = main(
            [
                "addheader",
                "--year",
                str(2010 + i),
                "--license",
                "GPL-3.0-or-later",
                "--copyright",
                "Mary Sue",
                "foo.py",
            ],
            out=stringio,
        )

        assert result == 0

    for i in range(0, 5):
        result = main(
            [
                "addheader",
                "--year",
                str(2015 + i),
                "--license",
                "GPL-3.0-or-later",
                "--copyright-style",
                "string-c",
                "--copyright",
                "Mary Sue",
                "foo.py",
            ],
            out=stringio,
        )

        assert result == 0

    assert (
        simple_file.read_text()
        == cleandoc(
            """
            # Copyright (C) 2015 Mary Sue
            # Copyright (C) 2016 Mary Sue
            # Copyright (C) 2017 Mary Sue
            # Copyright (C) 2018 Mary Sue
            # Copyright (C) 2019 Mary Sue
            # spdx-FileCopyrightText: 2010 Mary Sue
            # spdx-FileCopyrightText: 2011 Mary Sue
            # spdx-FileCopyrightText: 2012 Mary Sue
            #
            # spdx-License-Identifier: GPL-3.0-or-later

            pass
            """
        ).replace("spdx", "SPDX")
    )

    result = main(
        [
            "addheader",
            "--year",
            "2018",
            "--license",
            "GPL-3.0-or-later",
            "--copyright",
            "Mary Sue",
            "--merge-copyrights",
            "foo.py",
        ],
        out=stringio,
    )

    assert result == 0
    assert (
        simple_file.read_text()
        == cleandoc(
            """
            # Copyright (C) 2010 - 2019 Mary Sue
            #
            # spdx-License-Identifier: GPL-3.0-or-later

            pass
            """
        ).replace("spdx", "SPDX")
    )
