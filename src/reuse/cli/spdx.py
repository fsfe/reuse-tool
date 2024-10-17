# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2022 Pietro Albini <pietro.albini@ferrous-systems.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Click code for spdx subcommand."""

import contextlib
import logging
import sys
from typing import Optional

import click

from ..covered_files import _IGNORE_SPDX_PATTERNS
from ..i18n import _
from ..report import ProjectReport
from .common import ClickObj
from .main import main

_LOGGER = logging.getLogger(__name__)

_HELP = _("Generate an SPDX bill of materials.")


@main.command(name="spdx", help=_HELP)
@click.option(
    "--output",
    "-o",
    type=click.File("w", encoding="utf-8", lazy=True),
    # Default is stdout.
    default=None,
    help=_("File to write to."),
)
@click.option(
    "--add-license-concluded",
    is_flag=True,
    help=_(
        "Populate the LicenseConcluded field; note that reuse cannot guarantee"
        " that the field is accurate."
    ),
)
@click.option(
    "--add-licence-concluded",
    "add_license_concluded",
    hidden=True,
)
@click.option(
    "--creator-person",
    type=str,
    help=_("Name of the person signing off on the SPDX report."),
)
@click.option(
    "--creator-organization",
    help=_("Name of the organization signing off on the SPDX report."),
)
@click.option(
    "--creator-organisation",
    "creator_organization",
    hidden=True,
)
@click.pass_obj
def spdx(
    obj: ClickObj,
    output: Optional[click.File],
    add_license_concluded: bool,
    creator_person: Optional[str],
    creator_organization: Optional[str],
) -> None:
    # pylint: disable=missing-function-docstring

    # The SPDX spec mandates that a creator must be specified when a license
    # conclusion is made, so here we enforce that. More context:
    # https://github.com/fsfe/reuse-tool/issues/586#issuecomment-1310425706
    if (
        add_license_concluded
        and creator_person is None
        and creator_organization is None
    ):
        raise click.UsageError(
            _(
                "'--creator-person' or '--creator-organization'"
                " is required when '--add-license-concluded' is provided."
            )
        )

    if (
        output is not None
        and output.name != "-"
        and not any(
            pattern.match(output.name) for pattern in _IGNORE_SPDX_PATTERNS
        )
    ):
        # pylint: disable=line-too-long
        _LOGGER.warning(
            _(
                "'{path}' does not match a common SPDX file pattern. Find"
                " the suggested naming conventions here:"
                " https://spdx.github.io/spdx-spec/conformance/#44-standard-data-format-requirements"
            ).format(path=output.name)
        )

    report = ProjectReport.generate(
        obj.project,
        multiprocessing=not obj.no_multiprocessing,
        add_license_concluded=add_license_concluded,
    )

    with contextlib.ExitStack() as stack:
        if output is not None:
            out = stack.enter_context(output.open())  # type: ignore
        else:
            out = sys.stdout
        click.echo(
            report.bill_of_materials(
                creator_person=creator_person,
                creator_organization=creator_organization,
            ),
            file=out,
        )
