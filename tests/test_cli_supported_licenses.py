# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightTect: 2021 Michael Weimann
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for supported-licenses."""

import re

from click.testing import CliRunner

from reuse.cli.main import main


class TestSupportedLicenses:
    """Tests for supported-licenses."""

    def test_simple(self):
        """Invoke the supported-licenses command and check whether the result
        contains at least one license in the expected format.
        """

        result = CliRunner().invoke(main, ["supported-licenses"])

        assert result.exit_code == 0
        assert re.search(
            # pylint: disable=line-too-long
            r"GPL-3\.0-or-later\s+GNU General Public License v3\.0 or later\s+https:\/\/spdx\.org\/licenses\/GPL-3\.0-or-later\.html\s+\n",
            result.output,
        )
