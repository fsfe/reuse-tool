# SPDX-Copyright: 2017-2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Entry functions for reuse."""

import argparse
import logging
import sys
from gettext import gettext as _
from pathlib import Path
from typing import List

from . import __version__
from ._format import INDENT, fill_all, fill_paragraph
from ._util import find_root, setup_logging
from .lint import lint
from .project import Project
from .report import ProjectReport

_logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

_DESCRIPTION_LINES = [
    _("reuse  Copyright (C) 2017-2019  Free Software Foundation Europe e.V."),
    _(
        "reuse is a tool for compliance with the REUSE Initiative "
        "recommendations.  See <https://reuse.software/> for more "
        "information."
    ),
    _(
        # Translators: Find an (un)official translation of the GPL for this
        # bit.
        "reuse is free software: you can redistribute it and/or modify it "
        "under the terms of the GNU General Public License as published by "
        "the Free Software Foundation, either version 3 of the License, or "
        "(at your option) any later version.\n"
        "\n"
        "reuse is distributed in the hope that it will be useful, but WITHOUT "
        "ANY WARRANTY; without even the implied warranty of MERCHANTABILITY "
        "or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public "
        "License for more details.\n"
        "\n"
        "You should have received a copy of the GNU General Public License "
        "along with reuse.  If not, see <http://www.gnu.org/licenses/>."
    ),
    _("Support the FSFE's work:"),
]

_INDENTED_LINE = _(
    "Donations are critical to our strength and autonomy.  They enable us to "
    "continue working for Free Software wherever necessary.  Please consider "
    "making a donation at <https://fsfe.org/donate/>."
)

_DESCRIPTION_TEXT = (
    fill_all("\n\n".join(_DESCRIPTION_LINES))
    + "\n\n"
    + fill_paragraph(_INDENTED_LINE, indent_width=INDENT)
)

_EPILOG_TEXT = ""


def _create_project() -> Project:
    """Create a project object.  Try to find the project root from $PWD,
    otherwise treat $PWD as root.
    """
    root = find_root()
    if root is None:
        root = Path.cwd()
    return Project(root)


def compile_spdx(args, out=sys.stdout):
    """Print the project's bill of materials."""
    if args.output:
        out = args.output
        if not out.name.endswith(".spdx"):
            # Translators: %s is a file name.
            _logger.warning(_("%s does not end with .spdx"), out.name)

    project = _create_project()
    report = ProjectReport.generate(project)

    out.write(report.bill_of_materials())

    return 0


def lint_(args, out=sys.stdout):
    """List all non-compliant files."""
    project = _create_project()
    paths = args.paths
    if not paths:
        paths = [project.root]

    report = ProjectReport.generate(project, paths)
    result = lint(report, out=out)

    return 0 if result else 1


def parser() -> argparse.ArgumentParser:
    """Create the parser and return it."""
    # pylint: disable=redefined-outer-name
    parser = argparse.ArgumentParser(
        "reuse",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(_DESCRIPTION_TEXT),
        epilog=_EPILOG_TEXT,
    )
    parser.add_argument(
        "--debug", action="store_true", help=_("enable debug statements")
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help=_("show program's version number and exit"),
    )
    parser.set_defaults(func=lambda x, y: parser.print_help())

    subparsers = parser.add_subparsers()

    spdx_parser = subparsers.add_parser(
        "spdx", help=_("print the project's bill of materials in SPDX format")
    )
    spdx_parser.add_argument(
        "--output", "-o", action="store", type=argparse.FileType("w")
    )
    spdx_parser.set_defaults(func=compile_spdx)

    lint_parser = subparsers.add_parser(
        "lint",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help=_("list all non-compliant files"),
        description=fill_all(_("TODO: Description for lint.")),
    )
    lint_parser.add_argument("paths", action="store", nargs="*")
    lint_parser.set_defaults(func=lint_)

    return parser


def main(args: List[str] = None, out=sys.stdout) -> None:
    """Main entry function."""
    if args is None:
        args = sys.argv[1:]

    main_parser = parser()
    parsed_args = main_parser.parse_args(args)

    setup_logging(
        level=logging.DEBUG if parsed_args.debug else logging.WARNING
    )

    if parsed_args.version:
        out.write(_("reuse, version {}\n").format(__version__))
        return 0
    return parsed_args.func(parsed_args, out)
