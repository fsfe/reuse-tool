# SPDX-FileCopyrightText: 2024 Kerry McAdams <github@klmcadams>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Linting specific files happens here. The linting here is nothing more than 
reading the reports and printing some conclusions.
"""

import sys
from argparse import ArgumentParser, Namespace
from gettext import gettext as _
from pathlib import Path
from typing import IO

from ._util import PathType, is_relative_to
from .lint import format_lines_subset
from .project import Project
from .report import ProjectSubsetReport


def add_arguments(parser: ArgumentParser) -> None:
    """Add arguments to parser."""
    mutex_group = parser.add_mutually_exclusive_group()
    mutex_group.add_argument(
        "-q", "--quiet", action="store_true", help=_("prevents output")
    )
    mutex_group.add_argument(
        "-l",
        "--lines",
        action="store_true",
        help=_("formats output as errors per line (default)"),
    )
    parser.add_argument(
        "files",
        action="store",
        nargs="*",
        type=PathType("r"),
        help=_("files to lint"),
    )


def run(args: Namespace, project: Project, out: IO[str] = sys.stdout) -> int:
    """List all non-compliant files from specified file list."""
    subset_files = {Path(file_) for file_ in args.files}
    for file_ in subset_files:
        if not is_relative_to(file_.resolve(), project.root.resolve()):
            args.parser.error(
                _("'{file}' is not inside of '{root}'").format(
                    file=file_, root=project.root
                )
            )
    report = ProjectSubsetReport.generate(
        project,
        subset_files,
        multiprocessing=not args.no_multiprocessing,
    )

    if args.quiet:
        pass
    else:
        out.write(format_lines_subset(report))

    return 0 if report.is_compliant else 1
