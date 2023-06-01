# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""All linting happens here. The linting here is nothing more than reading
the reports and printing some conclusions.
"""

import json
import sys
from gettext import gettext as _
from io import StringIO
from pathlib import Path

from .project import Project
from .report import ProjectReport


def add_arguments(parser):
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
        "--format",
        nargs="?",
        choices=("json", "plain", "quiet"),
        help=_("formats output using the chosen formatter"),
    )


# pylint: disable=too-many-locals, too-many-branches, too-many-statements
def format_plain(report: ProjectReport) -> str:
    """Formats data dictionary as plaintext string to be printed to sys.stdout

    :param report: ProjectReport data
    :return: String (in plaintext) that can be output to sys.stdout
    """
    output = StringIO()
    data = report.to_dict_lint()

    # If the project is not compliant:
    if not data["summary"]["compliant"]:
        # Bad licenses
        bad_licenses = data["non_compliant"]["bad_licenses"]
        if bad_licenses:
            output.write("# " + _("BAD LICENSES") + "\n\n")
            for lic in sorted(bad_licenses.keys()):
                output.write(_("'{}' found in:").format(lic) + "\n")
                output.write(f"* {list(bad_licenses[lic])[0]}" + "\n\n")
            output.write("\n")

        # Deprecated licenses
        deprecated_licenses = data["non_compliant"]["deprecated_licenses"]
        if deprecated_licenses:
            output.write("# " + _("DEPRECATED LICENSES") + "\n\n")
            output.write(
                _("The following licenses are deprecated by SPDX:") + "\n"
            )
            for lic in sorted(deprecated_licenses):
                output.write(f"* {lic}\n")
            output.write("\n\n")

        # Licenses without extension
        licenses_without_extension = data["non_compliant"][
            "licenses_without_extension"
        ]
        if licenses_without_extension:
            output.write("# " + _("LICENSES WITHOUT FILE EXTENSION") + "\n\n")
            output.write(
                _("The following licenses have no file extension:") + "\n"
            )
            for lic in sorted(licenses_without_extension):
                output.write(f"* {str(licenses_without_extension[lic])}" + "\n")
            output.write("\n\n")

        # Missing licenses
        missing_licenses = data["non_compliant"]["missing_licenses"]
        if missing_licenses:
            output.write("# " + _("MISSING LICENSES") + "\n\n")
            for lic in sorted(missing_licenses.keys()):
                output.write(_("'{}' found in:").format(lic) + "\n")
                for file in sorted(missing_licenses[lic]):
                    output.write(f"* {file}\n")
            output.write("\n\n")

        # Unused licenses
        unused_licenses = data["non_compliant"]["unused_licenses"]
        if unused_licenses:
            output.write("# " + _("UNUSED LICENSES") + "\n\n")
            output.write(_("The following licenses are not used:") + "\n")
            for lic in sorted(unused_licenses):
                output.write(f"* {lic}\n")
            output.write("\n\n")

        # Read errors
        read_errors = data["non_compliant"]["read_errors"]
        if read_errors:
            output.write("# " + _("READ ERRORS") + "\n\n")
            output.write(_("Could not read:") + "\n")
            for path in sorted(read_errors):
                output.write(f"* {str(path)}" + "\n")
            output.write("\n\n")

        # Missing copyright and licensing information
        files_without_copyright = set(
            data["non_compliant"]["missing_copyright_info"]
        )
        files_without_license = set(
            data["non_compliant"]["missing_licensing_info"]
        )
        files_without_both = files_without_license.intersection(
            files_without_copyright
        )

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

        if files_without_copyright - files_without_both:
            output.write(
                _("The following files have no copyright information:")
            )
            output.write("\n")
            for file in sorted(files_without_copyright - files_without_both):
                output.write(f"* {file}\n")
            output.write("\n")

        if files_without_license - files_without_both:
            output.write(
                _("The following files have no licensing information:")
            )
            output.write("\n")
            for file in sorted(files_without_license - files_without_both):
                output.write(f"* {file}\n")
            output.write("\n")

    output.write("\n")
    output.write("# " + _("SUMMARY"))
    output.write("\n\n")

    summary_contents = {
        _("Bad licenses:"): ", ".join(data["non_compliant"]["bad_licenses"]),
        _("Deprecated licenses:"): ", ".join(
            data["non_compliant"]["deprecated_licenses"]
        ),
        _("Licenses without file extension:"): ", ".join(
            data["non_compliant"]["licenses_without_extension"]
        ),
        _("Missing licenses:"): ", ".join(
            data["non_compliant"]["missing_licenses"]
        ),
        _("Unused licenses:"): ", ".join(
            data["non_compliant"]["unused_licenses"]
        ),
        _("Used licenses:"): ", ".join(data["summary"]["used_licenses"]),
        _("Read errors: {count}").format(
            count=len(data["non_compliant"]["read_errors"])
        ): "empty",
        _("files with copyright information: {count} / {total}").format(
            count=data["summary"]["files_with_copyright_info"],
            total=data["summary"]["files_total"],
        ): "empty",
        _("files with license information: {count} / {total}").format(
            count=data["summary"]["files_with_licensing_info"],
            total=data["summary"]["files_total"],
        ): "empty",
    }

    filtered_summary_contents = {
        key: (value if value not in ("", "empty") else "0" if not value else "")
        for key, value in summary_contents.items()
    }

    for key, value in filtered_summary_contents.items():
        output.write(f"* {key} {value}\n")

    output.write("\n")
    if data["summary"]["compliant"]:
        output.write(
            _(
                "Congratulations! Your project is compliant with version"
                " {} of the REUSE Specification :-)"
            ).format(data["reuse_spec_version"])
        )
    else:
        output.write(
            _(
                "Unfortunately, your project is not compliant with version "
                "{} of the REUSE Specification :-("
            ).format(data["reuse_spec_version"])
        )
    output.write("\n")

    return output.getvalue()


def format_json(report: ProjectReport) -> str:
    """Formats data dictionary as JSON string ready to be printed to sys.stdout

    :param report: Dictionary containing formatted ProjectReport data
    :return: String (representing JSON) that can be output to sys.stdout
    """

    def custom_serializer(obj):
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


def run(args, project: Project, out=sys.stdout):
    """List all non-compliant files."""
    report = ProjectReport.generate(
        project, do_checksum=False, multiprocessing=not args.no_multiprocessing
    )

    if args.quiet or args.format == "quiet":
        pass
    elif args.json or args.format == "json":
        out.write(format_json(report))
    else:
        out.write(format_plain(report))

    return 0 if report.is_compliant else 1
