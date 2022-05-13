# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Compilation of the SPDX Document."""

import contextlib
import logging
import sys
from gettext import gettext as _

from . import _IGNORE_SPDX_PATTERNS
from ._util import PathType
from .project import Project
from .report import ProjectReport

_LOGGER = logging.getLogger(__name__)


def add_arguments(parser) -> None:
    """Add arguments to the parser."""
    parser.add_argument(
        "--output", "-o", dest="file", action="store", type=PathType("w")
    )


def run(args, project: Project, out=sys.stdout) -> int:
    """Print the project's bill of materials."""
    with contextlib.ExitStack() as stack:
        if args.file:
            out = stack.enter_context(args.file.open("w", encoding="utf-8"))
            if not any(
                pattern.match(args.file.name)
                for pattern in _IGNORE_SPDX_PATTERNS
            ):
                # pylint: disable=line-too-long
                _LOGGER.warning(
                    _(
                        "'{path}' does not match a common SPDX file pattern. Find"
                        " the suggested naming conventions here:"
                        " https://spdx.github.io/spdx-spec/conformance/#44-standard-data-format-requirements"
                    ).format(path=out.name)
                )

        report = ProjectReport.generate(
            project, multiprocessing=not args.no_multiprocessing
        )

        out.write(report.bill_of_materials())

    return 0
