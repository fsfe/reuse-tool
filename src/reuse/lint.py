# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""All linting happens here. The linting here is nothing more than reading
the reports and printing some conclusions.
"""

import json
import sys
from argparse import ArgumentParser, Namespace
from gettext import gettext as _
from io import StringIO
from pathlib import Path
from typing import IO, Any

from . import __REUSE_version__
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


# pylint: disable=too-many-branches, too-many-statements
def format_plain(report: ProjectReport) -> str:
    """Formats data dictionary as plaintext string to be printed to sys.stdout

    :param report: ProjectReport data
    :return: String (in plaintext) that can be output to sys.stdout
    """
    output = StringIO()

    if not report.is_compliant:
        # Bad licenses
        if report.bad_licenses:
            output.write("# " + _("BAD LICENSES") + "\n\n")
            for lic, files in sorted(report.bad_licenses.items()):
                output.write(_("'{}' found in:").format(lic) + "\n")
                for file in sorted(files):
                    output.write(f"* {file}\n")
            output.write("\n\n")

        # Deprecated licenses
        if report.deprecated_licenses:
            output.write("# " + _("DEPRECATED LICENSES") + "\n\n")
            output.write(
                _("The following licenses are deprecated by SPDX:") + "\n"
            )
            for lic in sorted(report.deprecated_licenses):
                output.write(f"* {lic}\n")
            output.write("\n\n")

        # Licenses without extension
        if report.licenses_without_extension:
            output.write("# " + _("LICENSES WITHOUT FILE EXTENSION") + "\n\n")
            output.write(
                _("The following licenses have no file extension:") + "\n"
            )
            for lic in sorted(report.licenses_without_extension):
                output.write(f"* {lic}\n")
            output.write("\n\n")

        # Missing licenses
        if report.missing_licenses:
            output.write("# " + _("MISSING LICENSES") + "\n\n")
            for lic, files in sorted(report.missing_licenses.items()):
                output.write(_("'{}' found in:").format(lic) + "\n")
                for file in sorted(files):
                    output.write(f"* {file}\n")
            output.write("\n\n")

        # Unused licenses
        if report.unused_licenses:
            output.write("# " + _("UNUSED LICENSES") + "\n\n")
            output.write(_("The following licenses are not used:") + "\n")
            for lic in sorted(report.unused_licenses):
                output.write(f"* {lic}\n")
            output.write("\n\n")

        # Read errors
        if report.read_errors:
            output.write("# " + _("READ ERRORS") + "\n\n")
            output.write(_("Could not read:") + "\n")
            for path in sorted(report.read_errors):
                output.write(f"* {path}\n")
            output.write("\n\n")

        # Missing copyright and licensing information
        files_without_both = report.files_without_copyright.intersection(
            report.files_without_licenses
        )
        files_without_copyright_excl = (
            report.files_without_copyright - files_without_both
        )
        files_without_licenses_excl = (
            report.files_without_licenses - files_without_both
        )
        files_without_either = files_without_copyright_excl.union(
            files_without_licenses_excl
        )

        if files_without_either:
            header = (
                "# " + _("MISSING COPYRIGHT AND LICENSING INFORMATION") + "\n\n"
            )
            output.write(header)
        if files_without_both:
            output.write(
                _(
                    "The following files have no copyright and licensing "
                    "information:"
                )
            )
            output.write("\n")
            for file in sorted(files_without_both):
                output.write(f"* {file}\n")
            output.write("\n")

        if files_without_copyright_excl:
            output.write(
                _("The following files have no copyright information:")
            )
            output.write("\n")
            for file in sorted(files_without_copyright_excl):
                output.write(f"* {file}\n")
            output.write("\n")

        if files_without_licenses_excl:
            output.write(
                _("The following files have no licensing information:")
            )
            output.write("\n")
            for file in sorted(files_without_licenses_excl):
                output.write(f"* {file}\n")
            output.write("\n")

    output.write("\n")
    output.write("# " + _("SUMMARY"))
    output.write("\n\n")

    total_files = len(report.file_reports)
    summary_contents = {
        _("Bad licenses:"): ", ".join(report.bad_licenses),
        _("Deprecated licenses:"): ", ".join(report.deprecated_licenses),
        _("Licenses without file extension:"): ", ".join(
            report.licenses_without_extension
        ),
        _("Missing licenses:"): ", ".join(report.missing_licenses),
        _("Unused licenses:"): ", ".join(report.unused_licenses),
        _("Used licenses:"): ", ".join(report.used_licenses),
        _("Read errors:"): str(len(report.read_errors)),
        _(
            "files with copyright information:"
        ): f"{total_files - len(report.files_without_copyright)}"
        f" / {total_files}",
        _(
            "files with license information:"
        ): f"{total_files - len(report.files_without_licenses)}"
        f" / {total_files}",
    }

    # Replace empty values with 0.
    summary_contents = {
        key: value if value else "0" for key, value in summary_contents.items()
    }

    for key, value in summary_contents.items():
        output.write(f"* {key} {value}\n")

    output.write("\n")
    if report.is_compliant:
        output.write(
            _(
                "Congratulations! Your project is compliant with version"
                " {} of the REUSE Specification :-)"
            ).format(__REUSE_version__)
        )
    else:
        output.write(
            _(
                "Unfortunately, your project is not compliant with version "
                "{} of the REUSE Specification :-("
            ).format(__REUSE_version__)
        )
    output.write("\n")

    return output.getvalue()


def format_json(report: ProjectReport) -> str:
    """Formats data dictionary as JSON string ready to be printed to sys.stdout

    :param report: Dictionary containing formatted ProjectReport data
    :return: String (representing JSON) that can be output to sys.stdout
    """

    def custom_serializer(obj: Any) -> Any:
        """Custom serializer for the dictionary output of ProjectReport

        :param obj: Object to be serialized
        """
        if isinstance(obj, Path):
            return str(obj)
        if isinstance(obj, set):
            return list(obj)
        raise TypeError(
            f"Object of type {obj.__class__.__name__} is not JSON serializable"
        )

    return json.dumps(
        report.to_dict_lint(),
        indent=2,
        # Serialize sets to lists
        default=custom_serializer,
    )


def run(args: Namespace, project: Project, out: IO[str] = sys.stdout) -> int:
    """List all non-compliant files."""
    report = ProjectReport.generate(
        project, do_checksum=False, multiprocessing=not args.no_multiprocessing
    )

    if args.quiet:
        pass
    elif args.json:
        out.write(format_json(report))
    else:
        out.write(format_plain(report))

    return 0 if report.is_compliant else 1
