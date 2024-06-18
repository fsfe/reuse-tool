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


def test_toml_from_dep5_asterisks():
    """Single asterisks get converted to double asterisks. Double asterisks get
    left alone.
    """
    text = StringIO(
        cleandoc_nl(
            """
            Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/

            Files: */**/***
            Copyright: 2018 Jane Doe
            License: MIT
            """
        )
    )
    expected = cleandoc_nl(
        """
        version = 1

        [[annotations]]
        path = "**/**/***"
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
        path = ["hello.txt", "foo**.txt"]
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


def test_toml_from_dep5_comments():
    """Optionally include comments."""
    text = StringIO(
        cleandoc_nl(
            """
            Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/

            Files: hello.txt
            Copyright: 2018 Jane Doe
            License: MIT
            Comment: hello

            Files: world.txt
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
        SPDX-FileComment = "hello"

        [[annotations]]
        path = "world.txt"
        precedence = "aggregate"
        SPDX-FileCopyrightText = "2018 Jane Doe"
        SPDX-License-Identifier = "MIT"
        """
    )
    assert toml_from_dep5(Copyright(text)) == expected


def test_toml_from_dep5_header():
    """Optionally include header fields."""
    text = StringIO(
        cleandoc_nl(
            """
            Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
            Upstream-Name: Some project
            Upstream-Contact: Jane Doe
            Source: https://example.com/
            Disclaimer: Some rights reserved

            Files: hello.txt
            Copyright: 2018 Jane Doe
            License: MIT
            """
        )
    )
    expected = cleandoc_nl(
        """
        version = 1
        SPDX-PackageName = "Some project"
        SPDX-PackageSupplier = "Jane Doe"
        SPDX-PackageDownloadLocation = "https://example.com/"
        SPDX-PackageComment = "Some rights reserved"

        [[annotations]]
        path = "hello.txt"
        precedence = "aggregate"
        SPDX-FileCopyrightText = "2018 Jane Doe"
        SPDX-License-Identifier = "MIT"
        """
    )
    assert toml_from_dep5(Copyright(text)) == expected


def test_toml_from_dep5_header_multiple_contacts():
    """Return a list of contacts."""
    text = StringIO(
        cleandoc_nl(
            """
            Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
            Upstream-Contact: Jane Doe
                John Doe

            Files: hello.txt
            Copyright: 2018 Jane Doe
            License: MIT
            """
        )
    )
    expected = cleandoc_nl(
        """
        version = 1
        SPDX-PackageSupplier = ["Jane Doe", "John Doe"]

        [[annotations]]
        path = "hello.txt"
        precedence = "aggregate"
        SPDX-FileCopyrightText = "2018 Jane Doe"
        SPDX-License-Identifier = "MIT"
        """
    )
    assert toml_from_dep5(Copyright(text)) == expected


def test_toml_from_dep5_man_example():
    """Test the example from the man page."""
    text = StringIO(
        cleandoc_nl(
            """
            Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
            Upstream-Name: Some project
            Upstream-Contact: Jane Doe
            Source: https://example.com/
            Disclaimer: Some rights reserved

            Files: hello*.txt
            Copyright: 2018 Jane Doe
            License: MIT
            Comment: hello world

            Files: foo bar
            Copyright: 2018 Jane Doe
                2019 John Doe
            License: MIT
            """
        )
    )
    expected = cleandoc_nl(
        """
        version = 1
        SPDX-PackageName = "Some project"
        SPDX-PackageSupplier = "Jane Doe"
        SPDX-PackageDownloadLocation = "https://example.com/"
        SPDX-PackageComment = "Some rights reserved"

        [[annotations]]
        path = "hello**.txt"
        precedence = "aggregate"
        SPDX-FileCopyrightText = "2018 Jane Doe"
        SPDX-License-Identifier = "MIT"
        SPDX-FileComment = "hello world"

        [[annotations]]
        path = ["foo", "bar"]
        precedence = "aggregate"
        SPDX-FileCopyrightText = ["2018 Jane Doe", "2019 John Doe"]
        SPDX-License-Identifier = "MIT"
        """
    )
    assert toml_from_dep5(Copyright(text)) == expected
