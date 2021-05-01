# SPDX-FileCopyrightText: 2020 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""List the project files and their license information."""

import logging
import sys
from gettext import gettext as _
from pathlib import Path

from .project import Project
from .report import ProjectReport

_LOGGER = logging.getLogger(__name__)


def add_arguments(_parser) -> None:
    """Add arguments to the parser."""


def print_table_line(out, line, widths) -> None:
    """Fill the values of the given line to the given widths and print them to
    the given output."""
    values = [str.ljust(str(val), width) for (val, width) in zip(line, widths)]
    print(*values, sep="  ", file=out)


def print_table_separator(out, widths) -> None:
    """Print a separator line with the given column widths to the given
    output."""
    values = ["-" * width for width in widths]
    print(*values, sep="  ", file=out)


def run(args, project: Project, out=sys.stdout) -> int:
    """List the project files files and their license information in a
    human-readable format."""
    report = ProjectReport.generate(
        project, multiprocessing=not args.no_multiprocessing
    )

    # Collect data and keep track of the longest values per column
    table_header = [_("File"), _("License")]
    column_widths = [len(header) for header in table_header]
    table_data = []
    for file_report in report.file_reports:
        file_name = project.relative_from_root(Path(file_report.path))
        licenses = ", ".join(sorted(file_report.spdxfile.licenses_in_file))
        table_data.append([file_name, licenses])
        column_widths[0] = max(column_widths[0], len(str(file_name)))
        column_widths[1] = max(column_widths[1], len(licenses))

    # Sort and print data, filling all values of the same column to the same
    # width for proper alignment
    table_data = sorted(table_data)
    print_table_line(out, table_header, column_widths)
    print_table_separator(out, column_widths)
    for row in table_data:
        print_table_line(out, row, column_widths)

    return 0
