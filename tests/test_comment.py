# SPDX-Copyright: 2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""All tests for reuse._comment"""

from inspect import cleandoc

from reuse._comment import create_header


def test_create_header_python():
    """Create a simple Python header."""
    text = cleandoc(
        """
        SPDX-Copyright: Mary Sue

        SPDX-License-Identifier: GPL-3.0-or-later
        """
    )

    expected = cleandoc(
        """
        # SPDX-Copyright: Mary Sue
        #
        # SPDX-License-Identifier: GPL-3.0-or-later
        """
    )

    assert create_header(text) == expected
