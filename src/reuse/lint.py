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
from typing import Iterable

from . import __REUSE_version__
from .project import Project
from .report import ProjectReport


def _write_element(element, out=sys.stdout):
    out.write("* ")
    out.write(str(element))
    out.write("\n")


def lint(report: ProjectReport, out=sys.stdout) -> bool:
    """Lint the entire project."""

    # Collect data from report
    # save into data structure (if report is not suitable)

    # Write output formatting functions (dynamic output formats)
    # Write output writing functions (stdout[, file, webrequest, ...])

    bad_licenses_result = lint_bad_licenses(report, out)
    deprecated_result = lint_deprecated_licenses(report, out)
    extensionless = lint_licenses_without_extension(report, out)
    missing_licenses_result = lint_missing_licenses(report, out)
    unused_licenses_result = lint_unused_licenses(report, out)
    read_errors_result = lint_read_errors(report, out)
    files_without_cali = lint_files_without_copyright_and_licensing(report, out)

    lint_summary(report, out=out)

    success = not any(
        any(result)
        for result in (
            bad_licenses_result,
            deprecated_result,
            extensionless,
            missing_licenses_result,
            unused_licenses_result,
            read_errors_result,
            files_without_cali,
        )
    )

    out.write("\n")
    if success:
        out.write(
            _(
                "Congratulations! Your project is compliant with version"
                " {} of the REUSE Specification :-)"
            ).format(__REUSE_version__)
        )
    else:
        out.write(
            _(
                "Unfortunately, your project is not compliant with version "
                "{} of the REUSE Specification :-("
            ).format(__REUSE_version__)
        )
    out.write("\n")

    return success


def lint_bad_licenses(report: ProjectReport, out=sys.stdout) -> Iterable[str]:
    """Lint for bad licenses. Bad licenses are licenses that are not in the
    SPDX License List or do not start with LicenseRef-.
    """
    bad_files = []

    if report.bad_licenses:
        out.write("# ")
        out.write(_("BAD LICENSES"))
        out.write("\n")
        for lic, files in sorted(report.bad_licenses.items()):
            out.write("\n")
            out.write(_("'{}' found in:").format(lic))
            out.write("\n")
            for file_ in sorted(files):
                bad_files.append(file_)
                _write_element(file_, out=out)
        out.write("\n\n")

    return bad_files


def lint_deprecated_licenses(
    report: ProjectReport, out=sys.stdout
) -> Iterable[str]:
    """Lint for deprecated licenses."""
    deprecated = []

    if report.deprecated_licenses:
        out.write("# ")
        out.write(_("DEPRECATED LICENSES"))
        out.write("\n\n")
        out.write(_("The following licenses are deprecated by SPDX:"))
        out.write("\n")
        for lic in sorted(report.deprecated_licenses):
            deprecated.append(lic)
            _write_element(lic, out=out)
        out.write("\n\n")

    return deprecated


def lint_licenses_without_extension(
    report: ProjectReport, out=sys.stdout
) -> Iterable[str]:
    """Lint for licenses without extensions."""
    extensionless = []

    if report.licenses_without_extension:
        out.write("# ")
        out.write(_("LICENSES WITHOUT FILE EXTENSION"))
        out.write("\n\n")
        out.write(_("The following licenses have no file extension:"))
        out.write("\n")
        for __, path in sorted(report.licenses_without_extension.items()):
            extensionless.append(path)
            _write_element(path, out=out)
        out.write("\n\n")

    return extensionless


def lint_missing_licenses(
    report: ProjectReport, out=sys.stdout
) -> Iterable[str]:
    """Lint for missing licenses. A license is missing when it is referenced
    in a file, but cannot be found.
    """
    bad_files = []

    if report.missing_licenses:
        out.write("# ")
        out.write(_("MISSING LICENSES"))
        out.write("\n")

        for lic, files in sorted(report.missing_licenses.items()):
            out.write("\n")
            out.write(_("'{}' found in:").format(lic))
            out.write("\n")
            for file_ in sorted(files):
                bad_files.append(file_)
                _write_element(file_, out=out)
        out.write("\n\n")

    return bad_files


def lint_unused_licenses(
    report: ProjectReport, out=sys.stdout
) -> Iterable[str]:
    """Lint for unused licenses."""
    unused_licenses = []

    if report.unused_licenses:
        out.write("# ")
        out.write(_("UNUSED LICENSES"))
        out.write("\n\n")
        out.write(_("The following licenses are not used:"))
        out.write("\n")
        for lic in sorted(report.unused_licenses):
            unused_licenses.append(lic)
            _write_element(lic, out=out)
        out.write("\n\n")

    return unused_licenses


def lint_read_errors(report: ProjectReport, out=sys.stdout) -> Iterable[str]:
    """Lint for read errors."""
    bad_files = []

    if report.read_errors:
        out.write("# ")
        out.write(_("READ ERRORS"))
        out.write("\n\n")
        out.write(_("Could not read:"))
        out.write("\n")
        for file_ in report.read_errors:
            bad_files.append(file_)
            _write_element(file_, out=out)
        out.write("\n\n")

    return bad_files


def lint_files_without_copyright_and_licensing(
    report: ProjectReport, out=sys.stdout
) -> Iterable[str]:
    """Lint for files that do not have copyright or licensing information."""
    # TODO: The below three operations can probably be optimised.
    both = set(report.files_without_copyright) & set(
        report.files_without_licenses
    )
    only_copyright = set(report.files_without_copyright) - both
    only_licensing = set(report.files_without_licenses) - both

    if any((both, only_copyright, only_licensing)):
        out.write("# ")
        out.write(_("MISSING COPYRIGHT AND LICENSING INFORMATION"))
        out.write("\n\n")
        if both:
            out.write(
                _(
                    "The following files have no copyright and licensing "
                    "information:"
                )
            )
            out.write("\n")
            for file_ in sorted(both):
                _write_element(file_, out=out)
            out.write("\n")
        if only_copyright:
            out.write(_("The following files have no copyright information:"))
            out.write("\n")
            for file_ in sorted(only_copyright):
                _write_element(file_, out=out)
            out.write("\n")
        if only_licensing:
            out.write(_("The following files have no licensing information:"))
            out.write("\n")
            for file_ in sorted(only_licensing):
                _write_element(file_, out=out)
            out.write("\n")
        out.write("\n")

    return both | only_copyright | only_licensing


def lint_summary(report: ProjectReport, out=sys.stdout) -> None:
    """Print a summary for linting."""
    # pylint: disable=too-many-statements
    out.write("# ")
    out.write(_("SUMMARY"))
    out.write("\n\n")

    file_total = len(report.file_reports)

    out.write("* ")
    out.write(_("Bad licenses:"))
    for i, lic in enumerate(sorted(report.bad_licenses)):
        if i:
            out.write(",")
        out.write(" ")
        out.write(lic)
    out.write("\n")

    out.write("* ")
    out.write(_("Deprecated licenses:"))
    for i, lic in enumerate(sorted(report.deprecated_licenses)):
        if i:
            out.write(",")
        out.write(" ")
        out.write(lic)
    out.write("\n")

    out.write("* ")
    out.write(_("Licenses without file extension:"))
    for i, lic in enumerate(sorted(report.licenses_without_extension)):
        if i:
            out.write(",")
        out.write(" ")
        out.write(lic)
    out.write("\n")

    out.write("* ")
    out.write(_("Missing licenses:"))
    for i, lic in enumerate(sorted(report.missing_licenses)):
        if i:
            out.write(",")
        out.write(" ")
        out.write(lic)
    out.write("\n")

    out.write("* ")
    out.write(_("Unused licenses:"))
    for i, lic in enumerate(sorted(report.unused_licenses)):
        if i:
            out.write(",")
        out.write(" ")
        out.write(lic)
    out.write("\n")

    out.write("* ")
    out.write(_("Used licenses:"))
    for i, lic in enumerate(sorted(report.used_licenses)):
        if i:
            out.write(",")
        out.write(" ")
        out.write(lic)
    out.write("\n")

    out.write("* ")
    out.write(_("Read errors: {count}").format(count=len(report.read_errors)))
    out.write("\n")

    out.write("* ")
    out.write(
        _("Files with copyright information: {count} / {total}").format(
            count=file_total - len(report.files_without_copyright),
            total=file_total,
        )
    )
    out.write("\n")

    out.write("* ")
    out.write(
        _("Files with license information: {count} / {total}").format(
            count=file_total - len(report.files_without_licenses),
            total=file_total,
        )
    )
    out.write("\n")


def add_arguments(parser):
    """Add arguments to parser."""
    parser.add_argument(
        "-q", "--quiet", action="store_true", help=_("prevents output")
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
        "non_compliant": {},
        "files": {},
        "summary": {
            "used_licenses": [],
        },
    }

    # Populate 'non_compliant'
    data["non_compliant"] = {
        "missing_licenses": [str(f) for f in report.missing_licenses],
        "unused_licenses": [str(f) for f in report.unused_licenses],
        "deprecated_licenses": [str(f) for f in report.deprecated_licenses],
        "bad_licenses": [str(f) for f in report.bad_licenses],
        "licenses_without_extension": [
            str(f) for f in report.licenses_without_extension
        ],
        "missing_copyright_info": [
            str(f) for f in report.files_without_copyright
        ],
        "missing_licensing_info": [str(f) for f in report.missing_licenses],
        "read_error": [str(f) for f in report.read_errors],
    }

    # Populate 'files'
    for file in report.file_reports:
        copyrights = file.spdxfile.copyright.split("\n")
        data["files"][str(file.path)] = {
            "copyrights": [
                {"value": copyright, "source": file.spdxfile.name}
                for copyright in copyrights
            ],
            "licenses": [
                {"value": license, "source": file.spdxfile.name}
                for license in file.spdxfile.licenses_in_file
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


def format_json(data) -> str:
    """Formats data dictionary as JSON string ready to be printed to std.out

    :param data: Dictionary containing formatted ProjectReport data
    :return: String (representing JSON) that can be output to std.out
    """
    return json.dumps(data, indent=2)


def format_plain(data) -> str:
    """Formats data dictionary as plaintext string to be printed to std.out

    :param data: Dictionary containing formatted ProjectReport data
    :return: String (in plaintext) that can be output to std.out
    """
    output = ""
    if not data["summary"]["compliant"]:

        output += "# " + _("MISSING COPYRIGHT AND LICENSING INFORMATION")
        output += "\n\n"
        files_without_copyright = set(
            data["non_compliant"]["missing_copyright_info"]
        )
        files_without_license = set(
            data["non_compliant"]["missing_licensing_info"]
        )
        files_without_both = files_without_license.intersection(
            files_without_license
        )

        if files_without_both:
            output += _(
                "The following files have no copyright and licensing "
                "information:"
            )
            output += "\n"
            for file in sorted(files_without_both):
                output += f"* {file}\n"

        if files_without_copyright - files_without_both:
            output += _("The following files have no copyright information:")
            output += "\n"
            for file in sorted(files_without_copyright - files_without_both):
                output += f"* {file}\n"

        if files_without_license - files_without_both:
            output += _("The following files have no licensing information:")
            output += "\n"
            for file in sorted(files_without_license - files_without_both):
                output += f"* {file}\n"

        # bad licenses
        # deprecated licenses

        output += "\n"

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
            ", ".join(data["non_compliant"]["licenses_without_extension"]),
        ),
        (
            _("Missing licenses:"),
            ", ".join(data["non_compliant"]["missing_licensing_info"]),
        ),
        (
            _("Unused licenses:"),
            ", ".join(data["non_compliant"]["unused_licenses"]),
        ),
        (_("Used licenses:"), ", ".join(data["summary"]["used_licenses"])),
    ]

    for key, value in summary_contents:
        if not value:
            value = "0"
        output += "* " + key + ": " + value + "\n"

    return output


def output_data(data: dict, formatter, out=sys.stdout):
    """Outputs data to stdout

    :param data:
    :param formatter:
    :param out:
    """
    out.write(formatter(data))


def run(args, project: Project):
    """List all non-compliant files."""
    report = ProjectReport.generate(
        project, do_checksum=False, multiprocessing=not args.no_multiprocessing
    )

    with contextlib.ExitStack() as stack:
        if args.quiet:
            # TODO Rework quiet flag
            out = stack.enter_context(open(os.devnull, "w", encoding="utf-8"))
        # TODO Toggle JSON formatter via flag
        data = collect_data_from_report(report)
        output_data(data, format_json())
        result = data["summary"]["compliant"]

    return 0 if result else 1
