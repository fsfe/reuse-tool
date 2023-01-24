# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""All linting happens here. The linting here is nothing more than reading
the reports and printing some conclusions.
"""

import contextlib
import json
import os
import sys
from gettext import gettext as _
from typing import Dict

from . import __REUSE_version__
from .project import Project
from .report import ProjectReport


def add_arguments(parser):
    """Add arguments to parser."""
    parser.add_argument(
        "-q", "--quiet", action="store_true", help=_("prevents output")
    )
    parser.add_argument(
        "-j", "--json", action="store_true", help=_("formats output as JSON")
    )


def collect_data_from_report(report: ProjectReport) -> dict:
    """Collects and formats data from report and returns it as a dictionary

    :param report: ProjectReport object
    :return: Formatted dictionary containing data from the ProjectReport object
    """
    # Setup report data container
    data = {
        "json_version": "1.0",
        "reuse_version": __REUSE_version__,
        "non_compliant": {
            "missing_licenses": report.missing_licenses,
            "unused_licenses": [str(f) for f in report.unused_licenses],
            "deprecated_licenses": [str(f) for f in report.deprecated_licenses],
            "bad_licenses": report.bad_licenses,
            "licenses_without_extension": [
                f for f in report.licenses_without_extension.values()
            ],
            "missing_copyright_info": [
                str(f) for f in report.files_without_copyright
            ],
            "missing_licensing_info": [
                str(f) for f in report.files_without_licenses
            ],
            "read_error": [str(f) for f in report.read_errors],
        },
        "files": {},
        "summary": {
            "used_licenses": [],
        },
    }

    # Populate 'files'
    for file in report.file_reports:
        copyrights = file.spdxfile.copyright.split("\n")
        data["files"][str(file.path)] = {
            "copyrights": [
                {"value": cop, "source": file.spdxfile.name}
                for cop in copyrights
            ],
            "licenses": [
                {"value": lic, "source": file.spdxfile.name}
                for lic in file.spdxfile.licenses_in_file
            ],
        }

    # Populate 'summary'
    number_of_files = len(report.file_reports)
    is_compliant = not any(
        any(result)
        for result in (
            data["non_compliant"]["missing_licenses"],
            data["non_compliant"]["unused_licenses"],
            data["non_compliant"]["bad_licenses"],
            data["non_compliant"]["deprecated_licenses"],
            data["non_compliant"]["licenses_without_extension"],
            data["non_compliant"]["missing_copyright_info"],
            data["non_compliant"]["missing_licensing_info"],
            data["non_compliant"]["read_error"],
        )
    )
    data["summary"] = {
        "used_licenses": list(report.used_licenses),
        "files_total": number_of_files,
        "files_with_copyright_info": number_of_files
        - len(report.files_without_copyright),
        "files_with_licensing_info": number_of_files
        - len(report.files_without_licenses),
        "compliant": is_compliant,
    }
    return data


# pylint: disable=too-many-locals, too-many-branches, too-many-statements
def format_plain(data: Dict) -> str:
    """Formats data dictionary as plaintext string to be printed to sys.stdout

    :param data: Dictionary containing formatted ProjectReport data
    :return: String (in plaintext) that can be output to sys.stdout
    """
    output = ""

    # If the project is not compliant:
    if not data["summary"]["compliant"]:

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
        if files_without_both:
            output += header
            output += _(
                "The following files have no copyright and licensing "
                "information:"
            )
            output += "\n"
            for file in sorted(files_without_both):
                output += f"* {file}\n"
            output += "\n\n"

        if files_without_copyright - files_without_both:
            output += header
            output += _("The following files have no copyright information:")
            output += "\n"
            for file in sorted(files_without_copyright - files_without_both):
                output += f"* {file}\n"
            output += "\n\n"

        if files_without_license - files_without_both:
            output += header
            output += _("The following files have no licensing information:")
            output += "\n"
            for file in sorted(files_without_license - files_without_both):
                output += f"* {file}\n"
            output += "\n\n"

        # Bad licenses
        bad_licenses = data["non_compliant"]["bad_licenses"]
        if bad_licenses:
            output += "# " + _("BAD LICENSES") + "\n\n"
            for lic, files in sorted(bad_licenses.items()):
                output += f"'{lic}' found in:" + "\n"
                for file in sorted(files):
                    output += f"* {file}\n"
            output += "\n\n"

        # Deprecated licenses
        deprecated_licenses = data["non_compliant"]["deprecated_licenses"]
        if deprecated_licenses:
            output += "# " + _("DEPRECATED LICENSES") + "\n\n"
            output += _("The following licenses are deprecated by SPDX:") + "\n"
            for lic in sorted(deprecated_licenses):
                output += f"* {lic}\n"
            output += "\n\n"

        # Licenses without extension
        licenses_without_extension = data["non_compliant"][
            "licenses_without_extension"
        ]
        if licenses_without_extension:
            output += "# " + _("LICENSES WITHOUT FILE EXTENSION") + "\n\n"
            output += _("The following licenses have no file extension:") + "\n"
            for path in sorted(licenses_without_extension):
                output += f"* {str(path)}" + "\n"
            output += "\n\n"

        # Missing licenses
        missing_licenses = data["non_compliant"]["missing_licenses"]
        if missing_licenses:
            output += "# " + _("MISSING LICENSES") + "\n\n"
            for lic, files in sorted(missing_licenses.items()):
                output += f"'{lic}' found in:" + "\n"
                for file in sorted(files):
                    output += f"* {file}\n"
            output += "\n"

        # Unused licenses
        unused_licenses = data["non_compliant"]["unused_licenses"]
        if unused_licenses:
            output += "# " + _("UNUSED LICENSES") + "\n\n"
            output += _("The following licenses are not used:") + "\n"
            for lic in sorted(deprecated_licenses):
                output += f"* {lic}\n"
            output += "\n\n"

        # Read errors
        read_errors = data["non_compliant"]["read_error"]
        if read_errors:
            output += "# " + _("READ ERRORS") + "\n\n"
            output += _("Could not read:") + "\n"
            for path in sorted(read_errors):
                output += f"* {str(path)}" + "\n"
            output += "\n\n"

    output += "# " + _("SUMMARY")
    output += "\n\n"

    summary_contents = [
        (_("Bad licenses:"), ", ".join(data["non_compliant"]["bad_licenses"])),
        (
            _("Deprecated licenses:"),
            ", ".join(data["non_compliant"]["deprecated_licenses"]),
        ),
        (
            _("Licenses without file extension:"),
            ", ".join(
                [
                    lic.parts[-1] for lic in data["non_compliant"][
                        "licenses_without_extension"
                    ]
                ]
            ),
        ),
        (
            _("Missing licenses:"),
            ", ".join(data["non_compliant"]["missing_licenses"]),
        ),
        (
            _("Unused licenses:"),
            ", ".join(data["non_compliant"]["unused_licenses"]),
        ),
        (_("Used licenses:"), ", ".join(data["summary"]["used_licenses"])),
        (
            _("Read errors: {count}").format(
                count=len(data["non_compliant"]["read_error"])
            ),
            "empty",
        ),
        (
            _("files with copyright information: {count} / {total}").format(
                count=data["summary"]["files_with_copyright_info"],
                total=data["summary"]["files_total"],
            ),
            "empty",
        ),
        (
            _("files with license information: {count} / {total}").format(
                count=data["summary"]["files_with_licensing_info"],
                total=data["summary"]["files_total"],
            ),
            "empty",
        ),
    ]

    for key, value in summary_contents:
        if not value:
            value = "0"
        if value == "empty":
            value = ""
        output += "* " + key + " " + value + "\n"

    if data["summary"]["compliant"]:
        output += _(
            "Congratulations! Your project is compliant with version"
            " {} of the REUSE Specification :-)"
        ).format(__REUSE_version__)
    else:
        output += _(
            "Unfortunately, your project is not compliant with version "
            "{} of the REUSE Specification :-("
        ).format(__REUSE_version__)

    return output


def format_json(data: Dict) -> str:
    """Formats data dictionary as JSON string ready to be printed to sys.stdout

    :param data: Dictionary containing formatted ProjectReport data
    :return: String (representing JSON) that can be output to sys.stdout
    """

    return json.dumps(
        # Serialize sets to lists
        data,
        indent=2,
        default=lambda x: list(x) if isinstance(x, set) else x,
    )


def lint(data: Dict, formatter=format_plain, out=sys.stdout):
    """Lints the entire project

    :param data: Dictionary holding formatted ProjectReport data
    :param formatter: Callable that formats the data dictionary
    :param out: Where to output
    """

    out.write(formatter(data))

    result = data["summary"]["compliant"]
    return result


def run(args, project: Project, out=sys.stdout, formatter=format_plain):
    """List all non-compliant files."""
    report = ProjectReport.generate(
        project, do_checksum=False, multiprocessing=not args.no_multiprocessing
    )

    with contextlib.ExitStack() as stack:
        if args.quiet:
            out = stack.enter_context(open(os.devnull, "w", encoding="utf-8"))

        if args.json:
            formatter = format_json

        data = collect_data_from_report(report)
        lint(data, formatter=formatter, out=out)
        result = data["summary"]["compliant"]

    return 0 if result else 1
