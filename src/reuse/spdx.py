# SPDX-FileCopyrightText: 2017-2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Compilation of the SPDX Document."""

import contextlib
import logging
import sys
from gettext import gettext as _

from ._util import PathType
from .project import create_project
from .report import ProjectReport

_LOGGER = logging.getLogger(__name__)


def add_arguments(parser) -> None:
    """Add arguments to the parser."""
    parser.add_argument(
        "--output", "-o", dest="file", action="store", type=PathType("w")
    )


def run(args, out=sys.stdout) -> int:
    """Print the project's bill of materials."""
    if args.file:
        out = args.file.open("w", encoding="UTF-8")
        if args.file.suffix != ".spdx":
            # Translators: %s is a file name.
            _LOGGER.warning(_("'%s' does not end with .spdx"), out.name)

    project = create_project()
    report = ProjectReport.generate(project)

    out.write(report.bill_of_materials())

    # Don't close sys.stdout or StringIO
    if args.file:
        with contextlib.suppress(Exception):
            out.close()

    return 0
