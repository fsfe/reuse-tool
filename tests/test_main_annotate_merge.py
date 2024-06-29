# SPDX-FileCopyrightText: 2021 Liam Beguin <liambeguin@gmail.com>
# SPDX-FileCopyrightText: 2024 Rivos Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for reuse._main: annotate merge-copyrights option"""

from inspect import cleandoc

from reuse._main import main

# pylint: disable=unused-argument

# REUSE-IgnoreStart


def test_annotate_merge_copyrights_simple(fake_repository, stringio):
    """Add multiple headers to a file with merge copyrights."""
    simple_file = fake_repository / "foo.py"
    simple_file.write_text("pass")

    result = main(
        [
            "annotate",
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
    assert simple_file.read_text() == cleandoc(
        """
            # SPDX-FileCopyrightText: 2016 Mary Sue
            #
            # SPDX-License-Identifier: GPL-3.0-or-later

            pass
            """
    )

    result = main(
        [
            "annotate",
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
    assert simple_file.read_text() == cleandoc(
        """
            # SPDX-FileCopyrightText: 2016 - 2018 Mary Sue
            #
            # SPDX-License-Identifier: GPL-3.0-or-later

            pass
            """
    )


def test_annotate_merge_copyrights_multi_prefix(fake_repository, stringio):
    """Add multiple headers to a file with merge copyrights."""
    simple_file = fake_repository / "foo.py"
    simple_file.write_text("pass")

    for i in range(0, 3):
        result = main(
            [
                "annotate",
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
                "annotate",
                "--year",
                str(2015 + i),
                "--license",
                "GPL-3.0-or-later",
                "--copyright-prefix",
                "string-c",
                "--copyright",
                "Mary Sue",
                "foo.py",
            ],
            out=stringio,
        )

        assert result == 0

    assert simple_file.read_text() == cleandoc(
        """
            # Copyright (C) 2015 Mary Sue
            # Copyright (C) 2016 Mary Sue
            # Copyright (C) 2017 Mary Sue
            # Copyright (C) 2018 Mary Sue
            # Copyright (C) 2019 Mary Sue
            # SPDX-FileCopyrightText: 2010 Mary Sue
            # SPDX-FileCopyrightText: 2011 Mary Sue
            # SPDX-FileCopyrightText: 2012 Mary Sue
            #
            # SPDX-License-Identifier: GPL-3.0-or-later

            pass
            """
    )

    result = main(
        [
            "annotate",
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
    assert simple_file.read_text() == cleandoc(
        """
            # Copyright (C) 2010 - 2019 Mary Sue
            #
            # SPDX-License-Identifier: GPL-3.0-or-later

            pass
            """
    )


def test_annotate_merge_copyrights_no_year_in_existing(
    fake_repository, stringio, mock_date_today
):
    """This checks the issue reported in
    <https://github.com/fsfe/reuse-tool/issues/866>. If an existing copyright
    line doesn't have a year, everything should still work.
    """
    (fake_repository / "foo.py").write_text(
        cleandoc(
            """
            # SPDX-FileCopyrightText: Jane Doe
            """
        )
    )
    main(
        [
            "annotate",
            "--merge-copyrights",
            "--copyright",
            "John Doe",
            "foo.py",
        ]
    )
    assert (
        cleandoc(
            """
            # SPDX-FileCopyrightText: 2018 John Doe
            # SPDX-FileCopyrightText: Jane Doe
            """
        )
        in (fake_repository / "foo.py").read_text()
    )


# REUSE-IgnoreEnd
