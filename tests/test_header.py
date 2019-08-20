# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V.
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
        set(["GPL-3.0-or-later"]), set(["SPDX" "-FileCopyrightText: Mary Sue"])
    )
    expected = cleandoc(
        """
        # spdx-FileCopyrightText: Mary Sue
        #
        # spdx-License-Identifier: GPL-3.0-or-later
        """
    ).replace("spdx", "SPDX")

    assert create_header(spdx_info) == expected


def test_create_header_template_simple(template_simple):
    """Create a header with a simple template."""
    spdx_info = SpdxInfo(
        set(["GPL-3.0-or-later"]), set(["SPDX" "-FileCopyrightText: Mary Sue"])
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

    assert create_header(spdx_info, template=template_simple) == expected


def test_create_header_template_no_spdx(template_no_spdx):
    """Create a header with a template that does not have all SPDX info."""
    spdx_info = SpdxInfo(
        set(["GPL-3.0-or-later"]), set(["SPDX" "-FileCopyrightText: Mary Sue"])
    )

    with pytest.raises(MissingSpdxInfo):
        create_header(spdx_info, template=template_no_spdx)


def test_create_header_template_commented(template_commented):
    """Create a header with an already-commented template."""
    spdx_info = SpdxInfo(
        set(["GPL-3.0-or-later"]), set(["SPDX" "-FileCopyrightText: Mary Sue"])
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
        )
        == expected
    )


def test_create_header_already_contains_spdx():
    """Create a new header from a header that already contains SPDX info."""
    spdx_info = SpdxInfo(
        set(["GPL-3.0-or-later"]), set(["SPDX" "-FileCopyrightText: Mary Sue"])
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

    assert create_header(spdx_info, header=existing) == expected


def test_create_header_existing_is_wrong():
    """If the existing header contains errors, raise a CommentCreateError."""
    spdx_info = SpdxInfo(
        set(["GPL-3.0-or-later"]), set(["SPDX" "-FileCopyrightText: Mary Sue"])
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
    spdx_info = SpdxInfo(set(["GPL-3.0-or-later"]), set())
    existing = cleandoc(
        """
        # Copyright John Doe

        pass
        """
    )
    expected = cleandoc(
        """
        # Copyright John Doe
        #
        # spdx-License-Identifier: GPL-3.0-or-later
        """
    ).replace("spdx", "SPDX")

    assert create_header(spdx_info, header=existing) == expected


def test_find_and_replace_no_header():
    """Given text without header, add a header."""
    spdx_info = SpdxInfo(
        set(["GPL-3.0-or-later"]), set(["SPDX" "-FileCopyrightText: Mary Sue"])
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
    """In a scenario where the header is not the first character in the file,
    create a new header. It would be nice if this were handled more elegantly.
    """
    spdx_info = SpdxInfo(
        set(["GPL-3.0-or-later"]), set(["SPDX" "-FileCopyrightText: Mary Sue"])
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
        # spdx-FileCopyrightText: Mary Sue
        #
        # spdx-License-Identifier: GPL-3.0-or-later

        # spdx-FileCopyrightText: Jane Doe

        pass
        """
    ).replace("spdx", "SPDX")

    assert find_and_replace_header(text, spdx_info) == expected


def test_find_and_replace_keep_shebang():
    """When encountering a shebang, keep it and put the REUSE header beneath
    it.
    """
    spdx_info = SpdxInfo(
        set(["GPL-3.0-or-later"]), set(["SPDX" "-FileCopyrightText: Mary Sue"])
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


def test_find_and_replace_keep_old_comment():
    """When encountering a comment that does not contain copyright and
    licensing information, preserve it below the REUSE header.
    """
    spdx_info = SpdxInfo(
        set(["GPL-3.0-or-later"]), set(["SPDX" "-FileCopyrightText: Mary Sue"])
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
