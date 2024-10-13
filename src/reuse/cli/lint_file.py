# SPDX-FileCopyrightText: 2024 Kerry McAdams <github@klmcadams>
# SPDX-FileCopyrightText: 2024 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Click code for lint-file subcommand."""

# pylint: disable=unused-argument

import sys
from pathlib import Path
from typing import Collection

import click

from ..i18n import _
from ..lint import format_lines_subset
from ..report import ProjectSubsetReport
from .common import ClickObj, MutexOption
from .main import main

_OUTPUT_MUTEX = ["quiet", "lines"]

_HELP = _(
    "Lint individual files for REUSE compliance. The specified FILEs are"
    " checked for the presence of copyright and licensing information, and"
    " whether the found licenses are included in the LICENSES/ directory."
)


@main.command(name="lint-file", help=_HELP)
@click.option(
    "--quiet",
    "-q",
    cls=MutexOption,
    mutually_exclusive=_OUTPUT_MUTEX,
    is_flag=True,
    help=_("Prevent output."),
)
@click.option(
    "--lines",
    "-l",
    cls=MutexOption,
    mutually_exclusive=_OUTPUT_MUTEX,
    is_flag=True,
    help=_("Format output as errors per line. (default)"),
)
@click.argument(
    "files",
    # TRANSLATORS: You may translate this. Please preserve capital letters.
    metavar=_("FILE"),
    type=click.Path(exists=True, path_type=Path),
    nargs=-1,
)
@click.pass_obj
def lint_file(
    obj: ClickObj, quiet: bool, lines: bool, files: Collection[Path]
) -> None:
    # pylint: disable=missing-function-docstring
    project = obj.project
    subset_files = {Path(file_) for file_ in files}
    for file_ in subset_files:
        if not file_.resolve().is_relative_to(project.root.resolve()):
            raise click.UsageError(
                _("'{file}' is not inside of '{root}'.").format(
                    file=file_, root=project.root
                )
            )
    report = ProjectSubsetReport.generate(
        project,
        subset_files,
        multiprocessing=not obj.no_multiprocessing,
    )

    if quiet:
        pass
    else:
        click.echo(format_lines_subset(report), nl=False)

    sys.exit(0 if report.is_compliant else 1)
