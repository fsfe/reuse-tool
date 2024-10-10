# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2023 DB Systel GmbH
# SPDX-FileCopyrightText: 2024 Nico Rikken <nico@nicorikken.eu>
#
# SPDX-License-Identifier: GPL-3.0-or-later

# pylint: disable=unused-argument

"""Click code for lint subcommand."""

import sys

import click

from .. import __REUSE_version__
from ..i18n import _
from ..lint import format_json, format_lines, format_plain
from ..report import ProjectReport
from .common import ClickObj, MutexOption
from .main import main

_OUTPUT_MUTEX = ["quiet", "json", "plain", "lines"]

_HELP = (
    _(
        "Lint the project directory for REUSE compliance. This version of the"
        " tool checks against version {reuse_version} of the REUSE"
        " Specification. You can find the latest version of the specification"
        " at <https://reuse.software/spec/>."
    ).format(reuse_version=__REUSE_version__)
    + "\n\n"
    + _("Specifically, the following criteria are checked:")
    + "\n\n"
    + _(
        "- Are there any bad (unrecognised, not compliant with SPDX)"
        " licenses in the project?"
    )
    + "\n"
    + _("- Are there any deprecated licenses in the project?")
    + "\n"
    + _(
        "- Are there any license files in the LICENSES/ directory"
        " without file extension?"
    )
    + "\n"
    + _(
        "- Are any licenses referred to inside of the project, but"
        " not included in the LICENSES/ directory?"
    )
    + "\n"
    + _(
        "- Are any licenses included in the LICENSES/ directory that"
        " are not used inside of the project?"
    )
    + "\n"
    + _("- Are there any read errors?")
    + "\n"
    + _("- Do all files have valid copyright and licensing information?")
)


@main.command(name="lint", help=_HELP)
@click.option(
    "--quiet",
    "-q",
    cls=MutexOption,
    mutually_exclusive=_OUTPUT_MUTEX,
    is_flag=True,
    help=_("Prevent output."),
)
@click.option(
    "--json",
    "-j",
    cls=MutexOption,
    mutually_exclusive=_OUTPUT_MUTEX,
    is_flag=True,
    help=_("Format output as JSON."),
)
@click.option(
    "--plain",
    "-p",
    cls=MutexOption,
    mutually_exclusive=_OUTPUT_MUTEX,
    is_flag=True,
    help=_("Format output as plain text. (default)"),
)
@click.option(
    "--lines",
    "-l",
    cls=MutexOption,
    mutually_exclusive=_OUTPUT_MUTEX,
    is_flag=True,
    help=_("Format output as errors per line."),
)
@click.pass_obj
def lint(
    obj: ClickObj, quiet: bool, json: bool, plain: bool, lines: bool
) -> None:
    # pylint: disable=missing-function-docstring
    report = ProjectReport.generate(
        obj.project,
        do_checksum=False,
        multiprocessing=not obj.no_multiprocessing,
    )

    if quiet:
        pass
    elif json:
        click.echo(format_json(report), nl=False)
    elif lines:
        click.echo(format_lines(report), nl=False)
    else:
        click.echo(format_plain(report), nl=False)

    sys.exit(0 if report.is_compliant else 1)
