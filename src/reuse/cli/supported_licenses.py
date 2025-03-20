# SPDX-FileCopyrightText: 2021 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightTect: 2021 Michael Weimann
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Click code for supported-licenses subcommand."""

import click

from .._licenses import _LICENSES, _load_license_list
from ..i18n import _
from .main import main

_HELP = _("List all licenses on the SPDX License List.")


@main.command(name="supported-licenses", help=_HELP)
def supported_licenses() -> None:
    # pylint: disable=missing-function-docstring
    licenses = _load_license_list(_LICENSES)[1]

    license_name_width = 0
    for license_id, license_info in licenses.items():
        license_name = license_info["name"]

        width = len(license_name)
        if width > license_name_width:
            license_name_width = width

    for license_id, license_info in licenses.items():
        license_name = license_info["name"]

        click.echo(f"{license_name: <{license_name_width}}    {license_id}")
