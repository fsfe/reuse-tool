# SPDX-Copyright: 2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""All tests for reuse.header"""

from inspect import cleandoc

from reuse import SpdxInfo
from reuse.header import create_new_header


def test_create_header_simple():
    """Create a super simple header."""
    spdx_info = SpdxInfo(["GPL-3.0-or-later"], ["Mary Sue"])
    expected = cleandoc(
        """
        # spdx-Copyright: Mary Sue
        #
        # spdx-License-Identifier: GPL-3.0-or-later
        """
    ).replace("spdx", "SPDX")

    assert create_new_header(spdx_info) == expected
