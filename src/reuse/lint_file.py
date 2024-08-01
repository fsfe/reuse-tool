# SPDX-FileCopyrightText: 2024 Kerry McAdams <github@klmcadams>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Linting specific files happens here. The linting here is nothing more than 
reading the reports and printing some conclusions.
"""

import sys
from argparse import ArgumentParser, Namespace
from gettext import gettext as _
from typing import IO

from .lint import format_json, format_lines, format_plain
from .project import Project
from .report import ProjectReport


def add_arguments(parser: ArgumentParser) -> None:
    """Add arguments to parser."""
    mutex_group = parser.add_mutually_exclusive_group()
    mutex_group.add_argument(
        "-q", "--quiet", action="store_true", help=_("prevents output")
    )
    mutex_group.add_argument(
        "-j", "--json", action="store_true", help=_("formats output as JSON")
    )
    mutex_group.add_argument(
        "-p",
        "--plain",
        action="store_true",
        help=_("formats output as plain text"),
    )
    mutex_group.add_argument(
        "-l",
        "--lines",
        action="store_true",
        help=_("formats output as errors per line"),
    )
    parser.add_argument("files", nargs="*")


def run(args: Namespace, project: Project, out: IO[str] = sys.stdout) -> int:
    """List all non-compliant files from specified file list."""
    report = ProjectReport.generate(
        project,
        do_checksum=False,
        file_list=args.files,
        multiprocessing=not args.no_multiprocessing,
    )

    if args.quiet:
        pass
    elif args.json:
        out.write(format_json(report))
    elif args.lines:
        out.write(format_lines(report))
    else:
        out.write(format_plain(report))

    return 0 if report.is_compliant else 1
