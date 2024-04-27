# SPDX-FileCopyrightText: 2024 Carmen Bianca BAKKER <carmenbianca@fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for convert_dep5."""

# pylint: disable=line-too-long

from io import StringIO

from debian.copyright import Copyright

from reuse._util import cleandoc_nl
from reuse.convert_dep5 import toml_from_dep5


def test_toml_from_dep5_single_file():
    """Correctly convert a DEP5 file with a single file."""
    text = StringIO(
        cleandoc_nl(
            """
            Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
            Upstream-Name: test
            Upstream-Contact: test
            Source: test

            Files: hello.txt
            Copyright: 2018 Jane Doe
            License: MIT
            """
        )
    )
    expected = cleandoc_nl(
        """
        version = 1

        [[annotations]]
        path = "hello.txt"
        precedence = "aggregate"
        SPDX-FileCopyrightText = "2018 Jane Doe"
        SPDX-License-Identifier = "MIT"
        """
    )
    assert toml_from_dep5(Copyright(text)) == expected


def test_toml_from_dep5_multiple_files_in_paragraph():
    """Correctly convert a DEP5 file with a more files in a paragraph."""
    text = StringIO(
        cleandoc_nl(
            """
            Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
            Upstream-Name: test
            Upstream-Contact: test
            Source: test

            Files: hello.txt foo*.txt
            Copyright: 2018 Jane Doe
            License: MIT
            """
        )
    )
    expected = cleandoc_nl(
        """
        version = 1

        [[annotations]]
        path = ["hello.txt", "foo*.txt"]
        precedence = "aggregate"
        SPDX-FileCopyrightText = "2018 Jane Doe"
        SPDX-License-Identifier = "MIT"
        """
    )
    assert toml_from_dep5(Copyright(text)) == expected


def test_toml_from_dep5_multiple_paragraphs():
    """Correctly convert a DEP5 file with multiple paragraphs."""
    text = StringIO(
        cleandoc_nl(
            """
            Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
            Upstream-Name: test
            Upstream-Contact: test
            Source: test

            Files: hello.txt
            Copyright: 2018 Jane Doe
            License: MIT

            Files: world.txt
            Copyright: 2018 John Doe
            License: 0BSD
            """
        )
    )
    expected = cleandoc_nl(
        """
        version = 1

        [[annotations]]
        path = "hello.txt"
        precedence = "aggregate"
        SPDX-FileCopyrightText = "2018 Jane Doe"
        SPDX-License-Identifier = "MIT"

        [[annotations]]
        path = "world.txt"
        precedence = "aggregate"
        SPDX-FileCopyrightText = "2018 John Doe"
        SPDX-License-Identifier = "0BSD"
        """
    )
    assert toml_from_dep5(Copyright(text)) == expected


def test_toml_from_dep5_multiple_copyright():
    """Correctly convert a DEP5 file with multiple copyright holders."""
    text = StringIO(
        cleandoc_nl(
            """
            Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
            Upstream-Name: test
            Upstream-Contact: test
            Source: test

            Files: hello.txt
            Copyright: 2018 Jane Doe
                2018 John Doe
            License: MIT
            """
        )
    )
    expected = cleandoc_nl(
        """
        version = 1

        [[annotations]]
        path = "hello.txt"
        precedence = "aggregate"
        SPDX-FileCopyrightText = ["2018 Jane Doe", "2018 John Doe"]
        SPDX-License-Identifier = "MIT"
        """
    )
    assert toml_from_dep5(Copyright(text)) == expected
