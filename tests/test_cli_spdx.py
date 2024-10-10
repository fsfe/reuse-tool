# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2019 Stefan Bakker <s.bakker777@gmail.com>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2022 Pietro Albini <pietro.albini@ferrous-systems.com>
# SPDX-FileCopyrightText: 2024 Carmen Bianca BAKKER <carmenbianca@fsfe.org>
# SPDX-FileCopyrightText: 2024 Skyler Grey <sky@a.starrysky.fyi>
# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for spdx."""

from click.testing import CliRunner
from freezegun import freeze_time

from reuse.cli.main import main

# pylint: disable=unused-argument


class TestSpdx:
    """Tests for spdx."""

    @freeze_time("2024-04-08T17:34:00Z")
    def test_simple(self, fake_repository):
        """Compile to an SPDX document."""
        result = CliRunner().invoke(main, ["spdx"])
        output = result.output

        # Ensure no LicenseConcluded is included without the flag
        assert "\nLicenseConcluded: NOASSERTION\n" in output
        assert "\nLicenseConcluded: GPL-3.0-or-later\n" not in output
        assert "\nCreator: Person: Anonymous ()\n" in output
        assert "\nCreator: Organization: Anonymous ()\n" in output
        assert "\nCreated: 2024-04-08T17:34:00Z\n" in output

        # TODO: This test is rubbish.
        assert result.exit_code == 0

    def test_creator_info(self, fake_repository):
        """Ensure the --creator-* flags are properly formatted"""
        result = CliRunner().invoke(
            main,
            [
                "spdx",
                "--creator-person=Jane Doe (jane.doe@example.org)",
                "--creator-organization=FSFE",
            ],
        )
        output = result.output

        assert result.exit_code == 0
        assert "\nCreator: Person: Jane Doe (jane.doe@example.org)\n" in output
        assert "\nCreator: Organization: FSFE ()\n" in output

    def test_add_license_concluded(self, fake_repository):
        """Compile to an SPDX document with the LicenseConcluded field."""
        result = CliRunner().invoke(
            main,
            [
                "spdx",
                "--add-license-concluded",
                "--creator-person=Jane Doe",
                "--creator-organization=FSFE",
            ],
        )
        output = result.output

        # Ensure no LicenseConcluded is included without the flag
        assert result.exit_code == 0
        assert "\nLicenseConcluded: NOASSERTION\n" not in output
        assert "\nLicenseConcluded: GPL-3.0-or-later\n" in output
        assert "\nCreator: Person: Jane Doe ()\n" in output
        assert "\nCreator: Organization: FSFE ()\n" in output

    def test_add_license_concluded_without_creator_info(self, fake_repository):
        """Adding LicenseConcluded should require creator information"""
        result = CliRunner().invoke(main, ["spdx", "--add-license-concluded"])
        assert result.exit_code != 0
        assert "--add-license-concluded" in result.output

    def test_spdx_no_multiprocessing(self, fake_repository, multiprocessing):
        """--no-multiprocessing works."""
        result = CliRunner().invoke(main, ["--no-multiprocessing", "spdx"])

        # TODO: This test is rubbish.
        assert result.exit_code == 0
        assert result.output
