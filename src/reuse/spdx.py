# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2022 Pietro Albini <pietro.albini@ferrous-systems.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Compilation of the SPDX Document."""

import contextlib
import logging
import sys
from argparse import ArgumentParser, Namespace
from gettext import gettext as _
from typing import IO

from . import _IGNORE_SPDX_PATTERNS
from ._util import PathType
from .project import Project
from .report import ProjectReport

_LOGGER = logging.getLogger(__name__)


def add_arguments(parser: ArgumentParser) -> None:
    """Add arguments to the parser."""
    parser.add_argument(
        "--output", "-o", dest="file", action="store", type=PathType("w")
    )
    parser.add_argument(
        "--add-license-concluded",
        action="store_true",
        help=_(
            "populate the LicenseConcluded field; note that reuse cannot "
            "guarantee the field is accurate"
        ),
    )
    parser.add_argument(
        "--creator-person",
        metavar="NAME",
        help=_("name of the person signing off on the SPDX report"),
    )
    parser.add_argument(
        "--creator-organization",
        metavar="NAME",
        help=_("name of the organization signing off on the SPDX report"),
    )


def run(args: Namespace, project: Project, out: IO[str] = sys.stdout) -> int:
    """Print the project's bill of materials."""
    # The SPDX spec mandates that a creator must be specified when a license
    # conclusion is made, so here we enforce that. More context:
    # https://github.com/fsfe/reuse-tool/issues/586#issuecomment-1310425706
    if (
        args.add_license_concluded
        and args.creator_person is None
        and args.creator_organization is None
    ):
        args.parser.error(
            _(
                "error: --creator-person=NAME or --creator-organization=NAME"
                " required when --add-license-concluded is provided"
            ),
        )

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
            project,
            multiprocessing=not args.no_multiprocessing,
            add_license_concluded=args.add_license_concluded,
        )

        out.write(
            report.bill_of_materials(
                creator_person=args.creator_person,
                creator_organization=args.creator_organization,
            )
        )

    return 0
