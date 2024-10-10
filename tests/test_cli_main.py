# SPDX-FileCopyrightText: 2023 Carmen Bianca BAKKER <carmen@carmenbianca.eu>
# SPDX-FileCopyrightText: 2024 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for reuse.cli.main."""

from click.testing import CliRunner

from reuse import __version__
from reuse.cli.main import main


class TestMain:
    """Collect all tests for main."""

    def test_help_is_default(self):
        """--help is optional."""
        without_help = CliRunner().invoke(main, [])
        with_help = CliRunner().invoke(main, ["--help"])
        assert without_help.output == with_help.output
        assert without_help.exit_code == with_help.exit_code == 0
        assert with_help.output.startswith("Usage: reuse")

    def test_version(self):
        """--version returns the correct version."""
        result = CliRunner().invoke(main, ["--version"])
        assert result.output.startswith(f"reuse, version {__version__}\n")
        assert "This program is free software:" in result.output
        assert "GNU General Public License" in result.output
