# SPDX-Copyright: 2017-2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""All linting happens here. The linting here is nothing more than reading
the reports and printing some conclusions.
"""

import sys
from gettext import gettext as _
from typing import Iterable

from ._util import PathType
from .project import create_project
from .report import ProjectReport


def _write_element(element, out=sys.stdout):
    out.write("  ")
    out.write(str(element))
    out.write("\n")


def lint(report: ProjectReport, out=sys.stdout) -> bool:
    """Lint the entire project."""
    bad_licenses_result = lint_bad_licenses(report, out)
    missing_licenses_result = lint_missing_licenses(report, out)
    unused_licenses_result = lint_unused_licenses(report, out)
    read_errors_result = lint_read_errors(report, out)
    files_without_licenses_result = lint_files_without_licenses(report, out)
    files_without_copyright_result = lint_files_without_copyright(report, out)

    lint_summary(report, out=out)

    success = not any(
        any(result)
        for result in (
            bad_licenses_result,
            missing_licenses_result,
            unused_licenses_result,
            read_errors_result,
            files_without_licenses_result,
            files_without_copyright_result,
        )
    )

    if success:
        out.write("\n")
        out.write(_("Congratulations! Your project is REUSE compliant :-)"))
        out.write("\n")

    return success


def lint_bad_licenses(report: ProjectReport, out=sys.stdout) -> Iterable[str]:
    """Lint for bad licenses. Bad licenses are licenses that are not in the
    SPDX License List or do not start with LicenseRef-.
    """
    bad_files = []

    if report.bad_licenses:
        out.write(_("BAD LICENSES"))
        out.write("\n")
        for lic, files in sorted(report.bad_licenses.items()):
            out.write("\n")
            out.write(_("'{}' found in:").format(lic))
            out.write("\n")
            for file_ in sorted(files):
                bad_files.append(file_)
                _write_element(file_, out=out)
        out.write("\n")

    return bad_files


def lint_missing_licenses(
    report: ProjectReport, out=sys.stdout
) -> Iterable[str]:
    """Lint for missing licenses. A license is missing when it is referenced
    in a file, but cannot be found.
    """
    bad_files = []

    if report.missing_licenses:
        out.write(_("MISSING LICENSES"))
        out.write("\n")

        for lic, files in sorted(report.missing_licenses.items()):
            out.write("\n")
            out.write(_("'{}' found in:").format(lic))
            out.write("\n")
            for file_ in sorted(files):
                bad_files.append(file_)
                _write_element(file_, out=out)
        out.write("\n")

    return bad_files


def lint_unused_licenses(
    report: ProjectReport, out=sys.stdout
) -> Iterable[str]:
    """Lint for unused licenses. A license is unused when it is not
    referenced in any files.
    """
    if report.unused_licenses:
        out.write(_("UNUSED LICENSES"))
        out.write("\n\n")
        out.write(_("The following licenses are not used:"))
        out.write("\n")
        for lic in sorted(report.unused_licenses):
            _write_element(lic, out=out)
        out.write("\n")

    return report.unused_licenses


def lint_read_errors(report: ProjectReport, out=sys.stdout) -> Iterable[str]:
    """Lint for read errors."""
    bad_files = []

    if report.read_errors:
        out.write(_("READ ERRORS"))
        out.write("\n\n")
        out.write(_("Could not read:"))
        out.write("\n")
        for file_ in report.read_errors:
            bad_files.append(file_)
            _write_element(file_, out=out)
        out.write("\n")

    return bad_files


def lint_files_without_licenses(
    report: ProjectReport, out=sys.stdout
) -> Iterable[str]:
    """Lint for files that do not have any license information."""
    if report.files_without_licenses:
        out.write(_("NO LICENSE"))
        out.write("\n\n")
        out.write(_("The following files have no license(s):"))
        out.write("\n")
        for file_ in sorted(report.files_without_licenses):
            _write_element(file_, out=out)
        out.write("\n")

    return report.files_without_licenses


def lint_files_without_copyright(
    report: ProjectReport, out=sys.stdout
) -> Iterable[str]:
    """Lint for files that do not have any copyright information."""
    if report.files_without_copyright:
        out.write(_("NO COPYRIGHT"))
        out.write("\n\n")
        out.write(_("The following files have no copyright:"))
        out.write("\n")
        for file_ in sorted(report.files_without_copyright):
            _write_element(file_, out=out)
        out.write("\n")

    return report.files_without_copyright


def lint_summary(report: ProjectReport, out=sys.stdout) -> None:
    """Print a summary for linting."""
    out.write(_("SUMMARY"))
    out.write("\n\n")

    file_total = len(report.file_reports)

    out.write(
        _("Bad licenses: {count}".format(count=len(report.bad_licenses)))
    )
    out.write("\n")

    out.write(
        _(
            "Missing licenses: {count}".format(
                count=len(report.missing_licenses)
            )
        )
    )
    out.write("\n")

    out.write(
        _("Unused licenses: {count}".format(count=len(report.unused_licenses)))
    )
    out.write("\n")

    out.write(_("Used licenses:"))
    for i, lic in enumerate(sorted(report.licenses)):
        if i:
            out.write(",")
        out.write(" ")
        out.write(lic)
    out.write("\n")

    out.write(_("Read errors: {count}".format(count=len(report.read_errors))))
    out.write("\n")

    out.write(
        _(
            "Files with copyright information: {count} / {total}".format(
                count=file_total - len(report.files_without_copyright),
                total=file_total,
            )
        )
    )
    out.write("\n")

    out.write(
        _(
            "Files with license information: {count} / {total}".format(
                count=file_total - len(report.files_without_licenses),
                total=file_total,
            )
        )
    )
    out.write("\n")


def add_arguments(parser):
    """Add arguments to parser."""
    parser.add_argument("paths", action="store", nargs="*", type=PathType("r"))


def run(args, out=sys.stdout):
    """List all non-compliant files."""
    project = create_project()
    paths = args.paths
    if not paths:
        paths = [project.root]

    report = ProjectReport.generate(project, paths)
    result = lint(report, out=out)

    return 0 if result else 1
