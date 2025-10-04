# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2024 Carmen Bianca BAKKER <carmenbianca@fsfe.org>
# SPDX-FileCopyrightText: 2025 Rivos Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""All tests for reuse.header"""

from inspect import cleandoc

import pytest

from reuse.comment import CppCommentStyle
from reuse.copyright import CopyrightNotice, ReuseInfo, SpdxExpression
from reuse.exceptions import MissingReuseInfoError
from reuse.header import add_new_header, create_header, find_and_replace_header

# REUSE-IgnoreStart


def test_create_header_simple():
    """Create a super simple header."""
    info = ReuseInfo(
        spdx_expressions={SpdxExpression("GPL-3.0-or-later")},
        copyright_notices={
            CopyrightNotice.from_string("SPDX-FileCopyrightText: Jane Doe")
        },
    )
    expected = cleandoc(
        """
        # SPDX-FileCopyrightText: Jane Doe
        #
        # SPDX-License-Identifier: GPL-3.0-or-later
        """
    )

    assert create_header(info).strip() == expected


def test_create_header_simple_with_contributor():
    """Create a super simple header."""
    info = ReuseInfo(
        spdx_expressions={SpdxExpression("GPL-3.0-or-later")},
        copyright_notices={
            CopyrightNotice.from_string("SPDX-FileCopyrightText: Jane Doe")
        },
        contributor_lines={"John Doe"},
    )
    expected = cleandoc(
        """
        # SPDX-FileCopyrightText: Jane Doe
        # SPDX-FileContributor: John Doe
        #
        # SPDX-License-Identifier: GPL-3.0-or-later
        """
    )

    assert create_header(info).strip() == expected


def test_create_header_template_simple(template_simple):
    """Create a header with a simple template."""
    info = ReuseInfo(
        spdx_expressions={SpdxExpression("GPL-3.0-or-later")},
        copyright_notices={
            CopyrightNotice.from_string("SPDX-FileCopyrightText: Jane Doe")
        },
    )
    expected = cleandoc(
        """
        # Hello, world!
        #
        # SPDX-FileCopyrightText: Jane Doe
        #
        # SPDX-License-Identifier: GPL-3.0-or-later
        """
    )

    assert create_header(info, template=template_simple).strip() == expected


def test_create_header_template_no_spdx(template_no_spdx):
    """Create a header with a template that does not have all REUSE info."""
    info = ReuseInfo(
        spdx_expressions={SpdxExpression("GPL-3.0-or-later")},
        copyright_notices={
            CopyrightNotice.from_string("SPDX-FileCopyrightText: Jane Doe")
        },
    )

    with pytest.raises(MissingReuseInfoError):
        create_header(info, template=template_no_spdx)


def test_create_header_template_commented(template_commented):
    """Create a header with an already-commented template."""
    info = ReuseInfo(
        spdx_expressions={SpdxExpression("GPL-3.0-or-later")},
        copyright_notices={
            CopyrightNotice.from_string("SPDX-FileCopyrightText: Jane Doe")
        },
    )
    expected = cleandoc(
        """
        # Hello, world!
        #
        # SPDX-FileCopyrightText: Jane Doe
        #
        # SPDX-License-Identifier: GPL-3.0-or-later
        """
    )

    assert (
        create_header(
            info,
            template=template_commented,
            template_is_commented=True,
            style=CppCommentStyle,
        ).strip()
        == expected
    )


def test_create_header_already_contains_spdx():
    """Create a new header from a header that already contains REUSE info."""
    info = ReuseInfo(
        spdx_expressions={SpdxExpression("GPL-3.0-or-later")},
        copyright_notices={
            CopyrightNotice.from_string("SPDX-FileCopyrightText: Jane Doe")
        },
    )
    existing = cleandoc(
        """
        # SPDX-FileCopyrightText: John Doe
        #
        # SPDX-License-Identifier: MIT
        """
    )
    expected = cleandoc(
        """
        # SPDX-FileCopyrightText: Jane Doe
        # SPDX-FileCopyrightText: John Doe
        #
        # SPDX-License-Identifier: GPL-3.0-or-later
        # SPDX-License-Identifier: MIT
        """
    )

    assert create_header(info, header=existing).strip() == expected


def test_create_header_existing_is_wrong():
    """If the existing header contains errors, do not raise a
    CommentCreateError.
    """
    info = ReuseInfo(
        spdx_expressions={SpdxExpression("GPL-3.0-or-later")},
        copyright_notices={
            CopyrightNotice.from_string("SPDX-FileCopyrightText: Jane Doe")
        },
    )
    existing = cleandoc(
        """
        # SPDX-FileCopyrightText: John Doe
        #
        # SPDX-License-Identifier: MIT AND OR 0BSD
        """
    )
    expected = cleandoc(
        """
        # SPDX-FileCopyrightText: Jane Doe
        # SPDX-FileCopyrightText: John Doe
        #
        # SPDX-License-Identifier: GPL-3.0-or-later
        # SPDX-License-Identifier: MIT AND OR 0BSD
        """
    )

    assert create_header(info, header=existing) == expected


def test_create_header_old_syntax():
    """Old copyright syntax is preserved when creating a new header."""
    info = ReuseInfo(spdx_expressions={SpdxExpression("GPL-3.0-or-later")})
    existing = cleandoc(
        """
        # Copyright John Doe
        """
    )
    expected = cleandoc(
        """
        # Copyright John Doe
        #
        # SPDX-License-Identifier: GPL-3.0-or-later
        """
    )

    assert create_header(info, header=existing).strip() == expected


def test_create_header_remove_fluff():
    """Any stuff that isn't REUSE info is removed when using create_header."""
    info = ReuseInfo(spdx_expressions={SpdxExpression("GPL-3.0-or-later")})
    existing = cleandoc(
        """
        # SPDX-FileCopyrightText: John Doe
        #
        # Hello, world!

        pass
        """
    )
    expected = cleandoc(
        """
        # SPDX-FileCopyrightText: John Doe
        #
        # SPDX-License-Identifier: GPL-3.0-or-later
        """
    )

    assert create_header(info, header=existing).strip() == expected


def test_add_new_header_simple():
    """Given text that already contains a header, create a new one, and preserve
    the old one.
    """
    info = ReuseInfo(
        spdx_expressions={SpdxExpression("GPL-3.0-or-later")},
        copyright_notices={
            CopyrightNotice.from_string("SPDX-FileCopyrightText: Jane Doe")
        },
    )
    text = cleandoc(
        """
        # SPDX-FileCopyrightText: John Doe
        #
        # SPDX-License-Identifier: MIT

        pass
        """
    )
    expected = cleandoc(
        """
        # SPDX-FileCopyrightText: Jane Doe
        #
        # SPDX-License-Identifier: GPL-3.0-or-later

        # SPDX-FileCopyrightText: John Doe
        #
        # SPDX-License-Identifier: MIT

        pass
        """
    )
    assert add_new_header(text, info) == expected


def test_find_and_replace_no_header():
    """Given text without header, add a header."""
    info = ReuseInfo(
        spdx_expressions={SpdxExpression("GPL-3.0-or-later")},
        copyright_notices={
            CopyrightNotice.from_string("SPDX-FileCopyrightText: Jane Doe")
        },
    )
    text = "pass"
    expected = cleandoc(
        """
        # SPDX-FileCopyrightText: Jane Doe
        #
        # SPDX-License-Identifier: GPL-3.0-or-later

        pass
        """
    )

    assert (
        find_and_replace_header(text, info)
        == add_new_header(text, info)
        == expected
    )


def test_find_and_replace_no_header_with_newline():
    """Given text that starts with a newline but no header, add a header."""
    info = ReuseInfo(
        spdx_expressions={SpdxExpression("GPL-3.0-or-later")},
        copyright_notices={
            CopyrightNotice.from_string("SPDX-FileCopyrightText: Jane Doe")
        },
    )
    text = "\npass"
    expected = cleandoc(
        """
        # SPDX-FileCopyrightText: Jane Doe
        #
        # SPDX-License-Identifier: GPL-3.0-or-later

        pass
        """
    )

    assert (
        find_and_replace_header(text, info)
        == add_new_header(text, info)
        == expected
    )


def test_find_and_replace_no_header_multiple_newlines():
    """Given text that starts with multiple newlines but no header, add a
    header."""
    info = ReuseInfo(
        spdx_expressions={SpdxExpression("GPL-3.0-or-later")},
        copyright_notices={
            CopyrightNotice.from_string("SPDX-FileCopyrightText: Jane Doe")
        },
    )
    text = "\n\npass"
    expected = cleandoc(
        """
        # SPDX-FileCopyrightText: Jane Doe
        #
        # SPDX-License-Identifier: GPL-3.0-or-later


        pass
        """
    )

    assert (
        find_and_replace_header(text, info)
        == add_new_header(text, info)
        == expected
    )


def test_find_and_replace_verbatim():
    """Replace a header with itself."""
    info = ReuseInfo()
    text = cleandoc(
        """
        # SPDX-FileCopyrightText: Jane Doe
        #
        # SPDX-License-Identifier: GPL-3.0-or-later

        pass
        """
    )

    assert find_and_replace_header(text, info) == text


def test_find_and_replace_verbatim_no_newline():
    """Do not add an empty line after existing headers."""
    info = ReuseInfo()
    text = cleandoc(
        """
        # SPDX-FileCopyrightText: Jane Doe
        #
        # SPDX-License-Identifier: GPL-3.0-or-later
        pass
        """
    )

    assert find_and_replace_header(text, info) == text


def test_find_and_replace_preserve_indentation():
    """If the first thing in a file is indented, do not change that thing's
    indentation.
    """
    info = ReuseInfo(
        spdx_expressions={SpdxExpression("GPL-3.0-or-later")},
        copyright_notices={
            CopyrightNotice.from_string("SPDX-FileCopyrightText: Jane Doe")
        },
    )
    text = '    # Hello\n    print("world")'

    assert find_and_replace_header(text, info) == cleandoc(
        """
        # SPDX-FileCopyrightText: Jane Doe
        #
        # SPDX-License-Identifier: GPL-3.0-or-later

            # Hello
            print("world")
        """
    )


def test_find_and_replace_newline_before_header():
    """In a scenario where the header is preceded by whitespace, remove the
    preceding whitespace.
    """
    info = ReuseInfo(
        spdx_expressions={SpdxExpression("GPL-3.0-or-later")},
        copyright_notices={
            CopyrightNotice.from_string("SPDX-FileCopyrightText: John Doe")
        },
    )
    text = cleandoc(
        """
        # SPDX-FileCopyrightText: Jane Doe

        pass
        """
    )
    text = "\n" + text
    expected = cleandoc(
        """
        # SPDX-FileCopyrightText: Jane Doe
        # SPDX-FileCopyrightText: John Doe
        #
        # SPDX-License-Identifier: GPL-3.0-or-later

        pass
        """
    )

    assert find_and_replace_header(text, info) == expected


def test_find_and_replace_preserve_preceding():
    """When the SPDX header is in the middle of the file, keep it there."""
    info = ReuseInfo(
        spdx_expressions={SpdxExpression("GPL-3.0-or-later")},
        copyright_notices={
            CopyrightNotice.from_string("SPDX-FileCopyrightText: John Doe")
        },
    )
    text = cleandoc(
        """
        # Hello, world!

        def foo(bar):
            return bar

        # SPDX-FileCopyrightText: Jane Doe

        pass
        """
    )
    expected = cleandoc(
        """
        # Hello, world!

        def foo(bar):
            return bar

        # SPDX-FileCopyrightText: Jane Doe
        # SPDX-FileCopyrightText: John Doe
        #
        # SPDX-License-Identifier: GPL-3.0-or-later

        pass
        """
    )

    assert find_and_replace_header(text, info) == expected


def test_find_and_replace_keep_shebang():
    """When encountering a shebang, keep it and put the REUSE header beneath
    it.
    """
    info = ReuseInfo(
        spdx_expressions={SpdxExpression("GPL-3.0-or-later")},
        copyright_notices={
            CopyrightNotice.from_string("SPDX-FileCopyrightText: John Doe")
        },
    )
    text = cleandoc(
        """
        #!/usr/bin/env python3

        # SPDX-FileCopyrightText: Jane Doe

        pass
        """
    )
    expected = cleandoc(
        """
        #!/usr/bin/env python3

        # SPDX-FileCopyrightText: Jane Doe
        # SPDX-FileCopyrightText: John Doe
        #
        # SPDX-License-Identifier: GPL-3.0-or-later

        pass
        """
    )

    assert find_and_replace_header(text, info) == expected


def test_find_and_replace_separate_shebang():
    """When the shebang is part of the same comment as the SPDX comment,
    separate the two.
    """
    info = ReuseInfo(spdx_expressions={SpdxExpression("GPL-3.0-or-later")})
    text = cleandoc(
        """
        #!/usr/bin/env python3
        #!nix-shell -p python3
        # SPDX-FileCopyrightText: Jane Doe

        pass
        """
    )
    expected = cleandoc(
        """
        #!/usr/bin/env python3
        #!nix-shell -p python3

        # SPDX-FileCopyrightText: Jane Doe
        #
        # SPDX-License-Identifier: GPL-3.0-or-later

        pass
        """
    )

    assert find_and_replace_header(text, info) == expected


def test_find_and_replace_shebang_but_no_copyright():
    """When the file contains a shebang but no copyright information, keep it at
    the top of the file.
    """
    info = ReuseInfo(spdx_expressions={SpdxExpression("GPL-3.0-or-later")})
    text = cleandoc(
        """
        #!/usr/bin/env python3

        # Hello, world!

        pass
        """
    )
    expected = cleandoc(
        """
        #!/usr/bin/env python3

        # SPDX-License-Identifier: GPL-3.0-or-later

        # Hello, world!

        pass
        """
    )

    assert find_and_replace_header(text, info) == expected


def test_find_and_replace_only_shebang():
    """When the file only contains a shebang, add copyright info below it."""
    info = ReuseInfo(spdx_expressions={SpdxExpression("GPL-3.0-or-later")})
    text = "#!/usr/bin/env python3"
    expected = (
        cleandoc(
            """
            #!/usr/bin/env python3

            # SPDX-License-Identifier: GPL-3.0-or-later
            """
        )
        + "\n"
    )

    assert find_and_replace_header(text, info) == expected


def test_find_and_replace_keep_old_comment():
    """When encountering a comment that does not contain copyright and
    licensing information, preserve it below the REUSE header.
    """
    info = ReuseInfo(
        spdx_expressions={SpdxExpression("GPL-3.0-or-later")},
        copyright_notices={
            CopyrightNotice.from_string("SPDX-FileCopyrightText: Jane Doe")
        },
    )
    text = cleandoc(
        """
        # Hello, world!

        pass
        """
    )
    expected = cleandoc(
        """
        # SPDX-FileCopyrightText: Jane Doe
        #
        # SPDX-License-Identifier: GPL-3.0-or-later

        # Hello, world!

        pass
        """
    )

    assert find_and_replace_header(text, info) == expected


def test_find_and_replace_preserve_newline():
    """If the file content ends with a newline, don't remove it."""

    info = ReuseInfo()
    text = (
        cleandoc(
            """
            # SPDX-FileCopyrightText: Jane Doe
            #
            # SPDX-License-Identifier: GPL-3.0-or-later

            pass
            """
        )
        + "\n"
    )

    assert find_and_replace_header(text, info) == text


# REUSE-IgnoreEnd
