# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

# pylint: disable=redefined-outer-name

"""All tests for reuse.header"""

# pylint: disable=implicit-str-concat-in-sequence

from inspect import cleandoc

import pytest

from reuse import SpdxInfo
from reuse._comment import CCommentStyle, CommentCreateError
from reuse.header import (
    MissingSpdxInfo,
    create_header,
    find_and_replace_header,
)


def test_create_header_simple():
    """Create a super simple header."""
    spdx_info = SpdxInfo(
        {"GPL-3.0-or-later"}, {"SPDX" "-FileCopyrightText: Mary Sue"}
    )
    expected = cleandoc(
        """
        # spdx-FileCopyrightText: Mary Sue
        #
        # spdx-License-Identifier: GPL-3.0-or-later
        """
    ).replace("spdx", "SPDX")

    assert create_header(spdx_info).strip() == expected


def test_create_header_template_simple(template_simple):
    """Create a header with a simple template."""
    spdx_info = SpdxInfo(
        {"GPL-3.0-or-later"}, {"SPDX" "-FileCopyrightText: Mary Sue"}
    )
    expected = cleandoc(
        """
        # Hello, world!
        #
        # spdx-FileCopyrightText: Mary Sue
        #
        # spdx-License-Identifier: GPL-3.0-or-later
        """
    ).replace("spdx", "SPDX")

    assert (
        create_header(spdx_info, template=template_simple).strip() == expected
    )


def test_create_header_template_no_spdx(template_no_spdx):
    """Create a header with a template that does not have all SPDX info."""
    spdx_info = SpdxInfo(
        {"GPL-3.0-or-later"}, {"SPDX" "-FileCopyrightText: Mary Sue"}
    )

    with pytest.raises(MissingSpdxInfo):
        create_header(spdx_info, template=template_no_spdx)


def test_create_header_template_commented(template_commented):
    """Create a header with an already-commented template."""
    spdx_info = SpdxInfo(
        {"GPL-3.0-or-later"}, {"SPDX" "-FileCopyrightText: Mary Sue"}
    )
    expected = cleandoc(
        """
        # Hello, world!
        #
        # spdx-FileCopyrightText: Mary Sue
        #
        # spdx-License-Identifier: GPL-3.0-or-later
        """
    ).replace("spdx", "SPDX")

    assert (
        create_header(
            spdx_info,
            template=template_commented,
            template_is_commented=True,
            style=CCommentStyle,
        ).strip()
        == expected
    )


def test_create_header_already_contains_spdx():
    """Create a new header from a header that already contains SPDX info."""
    spdx_info = SpdxInfo(
        {"GPL-3.0-or-later"}, {"SPDX" "-FileCopyrightText: Mary Sue"}
    )
    existing = cleandoc(
        """
        # spdx-FileCopyrightText: John Doe
        #
        # spdx-License-Identifier: MIT
        """
    ).replace("spdx", "SPDX")
    expected = cleandoc(
        """
        # spdx-FileCopyrightText: John Doe
        # spdx-FileCopyrightText: Mary Sue
        #
        # spdx-License-Identifier: GPL-3.0-or-later
        # spdx-License-Identifier: MIT
        """
    ).replace("spdx", "SPDX")

    assert create_header(spdx_info, header=existing).strip() == expected


def test_create_header_existing_is_wrong():
    """If the existing header contains errors, raise a CommentCreateError."""
    spdx_info = SpdxInfo(
        {"GPL-3.0-or-later"}, {"SPDX" "-FileCopyrightText: Mary Sue"}
    )
    existing = cleandoc(
        """
        # spdx-FileCopyrightText: John Doe
        #
        # spdx-License-Identifier: MIT AND OR 0BSD
        """
    ).replace("spdx", "SPDX")

    with pytest.raises(CommentCreateError):
        create_header(spdx_info, header=existing)


def test_create_header_old_syntax():
    """Old copyright syntax is preserved when creating a new header."""
    spdx_info = SpdxInfo({"GPL-3.0-or-later"}, set())
    existing = cleandoc(
        """
        # Copyright John Doe
        """
    )
    expected = cleandoc(
        """
        # Copyright John Doe
        #
        # spdx-License-Identifier: GPL-3.0-or-later
        """
    ).replace("spdx", "SPDX")

    assert create_header(spdx_info, header=existing).strip() == expected


def test_create_header_remove_fluff():
    """Any stuff that isn't SPDX info is removed when using create_header."""
    spdx_info = SpdxInfo({"GPL-3.0-or-later"}, set())
    existing = cleandoc(
        """
        # spdx-FileCopyrightText: John Doe
        #
        # Hello, world!

        pass
        """
    ).replace("spdx", "SPDX")
    expected = cleandoc(
        """
        # SPDX-FileCopyrightText: John Doe
        #
        # spdx-License-Identifier: GPL-3.0-or-later
        """
    ).replace("spdx", "SPDX")

    assert create_header(spdx_info, header=existing).strip() == expected


def test_find_and_replace_no_header():
    """Given text without header, add a header."""
    spdx_info = SpdxInfo(
        {"GPL-3.0-or-later"}, {"SPDX" "-FileCopyrightText: Mary Sue"}
    )
    text = "pass"
    expected = cleandoc(
        """
        # spdx-FileCopyrightText: Mary Sue
        #
        # spdx-License-Identifier: GPL-3.0-or-later

        pass
        """
    ).replace("spdx", "SPDX")

    assert find_and_replace_header(text, spdx_info) == expected


def test_find_and_replace_verbatim():
    """Replace a header with itself."""
    spdx_info = SpdxInfo(set(), set())
    text = cleandoc(
        """
        # spdx-FileCopyrightText: Mary Sue
        #
        # spdx-License-Identifier: GPL-3.0-or-later

        pass
        """
    ).replace("spdx", "SPDX")

    assert find_and_replace_header(text, spdx_info) == text


def test_find_and_replace_newline_before_header():
    """In a scenario where the header is preceded by whitespace, remove the
    preceding whitespace.
    """
    spdx_info = SpdxInfo(
        {"GPL-3.0-or-later"}, {"SPDX" "-FileCopyrightText: Mary Sue"}
    )
    text = cleandoc(
        """
        # spdx-FileCopyrightText: Jane Doe

        pass
        """
    ).replace("spdx", "SPDX")
    text = "\n" + text
    expected = cleandoc(
        """
        # spdx-FileCopyrightText: Jane Doe
        # spdx-FileCopyrightText: Mary Sue
        #
        # spdx-License-Identifier: GPL-3.0-or-later

        pass
        """
    ).replace("spdx", "SPDX")

    assert find_and_replace_header(text, spdx_info) == expected


def test_find_and_replace_preserve_preceding():
    """When the SPDX header is in the middle of the file, keep it there."""
    spdx_info = SpdxInfo(
        {"GPL-3.0-or-later"}, {"SPDX" "-FileCopyrightText: Mary Sue"}
    )
    text = cleandoc(
        """
        # Hello, world!

        def foo(bar):
            return bar

        # spdx-FileCopyrightText: Jane Doe

        pass
        """
    ).replace("spdx", "SPDX")
    expected = cleandoc(
        """
        # Hello, world!

        def foo(bar):
            return bar

        # spdx-FileCopyrightText: Jane Doe
        # spdx-FileCopyrightText: Mary Sue
        #
        # spdx-License-Identifier: GPL-3.0-or-later

        pass
        """
    ).replace("spdx", "SPDX")

    assert find_and_replace_header(text, spdx_info) == expected


def test_find_and_replace_keep_shebang():
    """When encountering a shebang, keep it and put the REUSE header beneath
    it.
    """
    spdx_info = SpdxInfo(
        {"GPL-3.0-or-later"}, {"SPDX" "-FileCopyrightText: Mary Sue"}
    )
    text = cleandoc(
        """
        #!/usr/bin/env python3

        # spdx-FileCopyrightText: Jane Doe

        pass
        """
    ).replace("spdx", "SPDX")
    expected = cleandoc(
        """
        #!/usr/bin/env python3

        # spdx-FileCopyrightText: Jane Doe
        # spdx-FileCopyrightText: Mary Sue
        #
        # spdx-License-Identifier: GPL-3.0-or-later

        pass
        """
    ).replace("spdx", "SPDX")

    assert find_and_replace_header(text, spdx_info) == expected


def test_find_and_replace_separate_shebang():
    """When the shebang is part of the same comment as the SPDX comment,
    separate the two.
    """
    spdx_info = SpdxInfo({"GPL-3.0-or-later"}, set())
    text = cleandoc(
        """
        #!/usr/bin/env python3
        #!nix-shell -p python3
        # spdx-FileCopyrightText: Jane Doe

        pass
        """
    ).replace("spdx", "SPDX")
    expected = cleandoc(
        """
        #!/usr/bin/env python3
        #!nix-shell -p python3

        # spdx-FileCopyrightText: Jane Doe
        #
        # spdx-License-Identifier: GPL-3.0-or-later

        pass
        """
    ).replace("spdx", "SPDX")

    assert find_and_replace_header(text, spdx_info) == expected


def test_find_and_replace_only_shebang():
    """When the file only contains a shebang, keep it at the top of the file.
    """
    spdx_info = SpdxInfo({"GPL-3.0-or-later"}, set())
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

        # spdx-License-Identifier: GPL-3.0-or-later

        # Hello, world!

        pass
        """
    ).replace("spdx", "SPDX")

    assert find_and_replace_header(text, spdx_info) == expected


def test_find_and_replace_keep_old_comment():
    """When encountering a comment that does not contain copyright and
    licensing information, preserve it below the REUSE header.
    """
    spdx_info = SpdxInfo(
        {"GPL-3.0-or-later"}, {"SPDX" "-FileCopyrightText: Mary Sue"}
    )
    text = cleandoc(
        """
        # Hello, world!

        pass
        """
    ).replace("spdx", "SPDX")
    expected = cleandoc(
        """
        # spdx-FileCopyrightText: Mary Sue
        #
        # spdx-License-Identifier: GPL-3.0-or-later

        # Hello, world!

        pass
        """
    ).replace("spdx", "SPDX")

    assert find_and_replace_header(text, spdx_info) == expected


def test_find_and_replace_preserve_newline():
    """If the file content ends with a newline, don't remove it."""

    spdx_info = SpdxInfo(set(), set())
    text = (
        cleandoc(
            """
            # spdx-FileCopyrightText: Mary Sue
            #
            # spdx-License-Identifier: GPL-3.0-or-later

            pass
            """
        ).replace("spdx", "SPDX")
        + "\n"
    )

    assert find_and_replace_header(text, spdx_info) == text
