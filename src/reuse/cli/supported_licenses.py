# SPDX-FileCopyrightText: 2021 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2021 Michael Weimann
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2025 Shun Sakai <sorairolake@protonmail.ch>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Click code for supported-licenses subcommand."""

import json

import click

from .._licenses import _LICENSES, _load_license_list
from ..i18n import _
from .common import ClickObj
from .main import main

_HELP = _("List all licenses on the SPDX License List.")


@main.command(name="supported-licenses", help=_HELP)
@click.option(
    "--json",
    "-j",
    "format_json",
    is_flag=True,
    help=_("Format output as JSON."),
)
@click.pass_obj
def supported_licenses(_obj: ClickObj, format_json: bool) -> None:
    # pylint: disable=missing-function-docstring
    licenses = _load_license_list(_LICENSES)[1]

    if format_json:
        licenses = [
            {
                "id": license_id,
                "name": license_info["name"],
                "reference": license_info["reference"],
            }
            for license_id, license_info in licenses.items()
        ]
        click.echo(json.dumps(licenses, indent=2), nl=False)
    else:
        for license_id, license_info in licenses.items():
            license_name = license_info["name"]
            license_reference = license_info["reference"]
            click.echo(
                f"{license_id: <40}\t{license_name: <80}\t"
                f"{license_reference: <50}"
            )
