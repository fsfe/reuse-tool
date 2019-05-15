# SPDX-Copyright: 2017-2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Compilation of the SPDX Document."""

import argparse
import logging
import sys
from gettext import gettext as _

from .project import create_project
from .report import ProjectReport

_LOGGER = logging.getLogger(__name__)


def add_arguments(parser) -> None:
    """Add arguments to the parser."""
    parser.add_argument(
        "--output", "-o", action="store", type=argparse.FileType("w")
    )


def run(args, out=sys.stdout) -> int:
    """Print the project's bill of materials."""
    if args.output:
        out = args.output
        if not out.name.endswith(".spdx"):
            # Translators: %s is a file name.
            _LOGGER.warning(_("%s does not end with .spdx"), out.name)

    project = create_project()
    report = ProjectReport.generate(project)

    out.write(report.bill_of_materials())

    return 0
