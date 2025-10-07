# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2023 DB Systel GmbH
# SPDX-FileCopyrightText: 2024 Nico Rikken <nico@nicorikken.eu>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""All linting happens here. The linting here is nothing more than reading
the reports and printing some conclusions.
"""

import json
from collections import defaultdict
from io import StringIO
from itertools import chain
from pathlib import Path
from textwrap import TextWrapper
from typing import Any

from . import __REUSE_version__
from .i18n import _
from .report import ProjectReport, ProjectReportSubsetProtocol


# pylint: disable=too-many-branches,too-many-statements,too-many-locals
def format_plain(report: ProjectReport) -> str:
    """Formats data dictionary as plaintext string to be printed to sys.stdout

    Args:
        report: ProjectReport data

    Returns:
        String (in plaintext) that can be output to sys.stdout
    """
    output = StringIO()

    if not report.is_compliant:
        # Bad licenses
        if report.bad_licenses:
            output.write("# " + _("BAD LICENSES") + "\n\n")
            output.write(
                _("The following licenses are not valid SPDX licenses:") + "\n"
            )
            for path in sorted(report.bad_licenses.values()):
                output.write(f"* {path}\n")
            output.write("\n")

        # Deprecated licenses
        if report.deprecated_licenses:
            output.write("# " + _("DEPRECATED LICENSES") + "\n\n")
            output.write(
                _("The following licenses are deprecated by SPDX:") + "\n"
            )
            for lic in sorted(report.deprecated_licenses):
                output.write(f"* {lic}\n")
            output.write("\n")

        # Licenses without extension
        if report.licenses_without_extension:
            output.write("# " + _("LICENSES WITHOUT FILE EXTENSION") + "\n\n")
            output.write(
                _("The following licenses have no file extension:") + "\n"
            )
            for lic in sorted(report.licenses_without_extension):
                output.write(f"* {lic}\n")
            output.write("\n")

        # Missing licenses
        if report.missing_licenses:
            output.write("# " + _("MISSING LICENSES") + "\n\n")
            for lic, files in sorted(report.missing_licenses.items()):
                output.write(_("'{}' found in:").format(lic) + "\n")
                for file in sorted(files):
                    output.write(f"* {file}\n")
            output.write("\n")

        # Unused licenses
        if report.unused_licenses:
            output.write("# " + _("UNUSED LICENSES") + "\n\n")
            output.write(_("The following licenses are not used:") + "\n")
            for lic in sorted(report.unused_licenses):
                output.write(f"* {lic}\n")
            output.write("\n")

        # Read errors
        if report.read_errors:
            output.write("# " + _("READ ERRORS") + "\n\n")
            output.write(_("Could not read:") + "\n")
            for path in sorted(report.read_errors):
                output.write(f"* {path}\n")
            output.write("\n")

        if report.invalid_spdx_expressions:
            output.write("# " + _("INVALID SPDX LICENSE EXPRESSIONS") + "\n\n")
            for path, expressions in sorted(
                report.invalid_spdx_expressions.items()
            ):
                output.write(
                    _("'{}' contains invalid SPDX License Expressions:").format(
                        path
                    )
                    + "\n"
                )
                for expression in sorted(expressions):
                    output.write(f"* {expression}\n")
            output.write("\n")

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

        if files_without_either or files_without_both:
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

    output.write("# " + _("SUMMARY"))
    output.write("\n\n")

    total_files = len(report.file_reports)
    summary_contents = {
        _("Bad licenses:"): ", ".join(sorted(report.bad_licenses)),
        _("Deprecated licenses:"): ", ".join(
            sorted(report.deprecated_licenses)
        ),
        _("Licenses without file extension:"): ", ".join(
            sorted(report.licenses_without_extension)
        ),
        _("Missing licenses:"): ", ".join(sorted(report.missing_licenses)),
        _("Unused licenses:"): ", ".join(sorted(report.unused_licenses)),
        _("Used licenses:"): ", ".join(sorted(report.used_licenses)),
        _("Read errors:"): str(len(report.read_errors)),
        _("Invalid SPDX License Expressions:"): str(
            len(
                list(
                    chain.from_iterable(
                        report.invalid_spdx_expressions.values()
                    )
                )
            )
        ),
        _(
            "Files with copyright information:"
        ): f"{total_files - len(report.files_without_copyright)}"
        f" / {total_files}",
        _(
            "Files with license information:"
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

        # Write recommendations in a nicely wrapped format
        output.write("\n\n\n# ")
        output.write(_("RECOMMENDATIONS"))
        output.write("\n\n")

        wrapper = TextWrapper(
            width=80,
            drop_whitespace=True,
            break_long_words=False,
            initial_indent="* ",
            subsequent_indent="  ",
        )
        for help_text in report.recommendations:
            output.write("\n".join(wrapper.wrap(help_text)))
            output.write("\n")

    output.write("\n")

    return output.getvalue()


def format_json(report: ProjectReport) -> str:
    """Formats data dictionary as JSON string ready to be printed to sys.stdout

    Args:
        report: Dictionary containing formatted ProjectReport data

    Returns:
        String (representing JSON) that can be output to sys.stdout
    """

    def custom_serializer(obj: Any) -> Any:
        """Custom serializer for the dictionary output of ProjectReport

        Args:
            obj: Object to be serialized
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


def _output_lines_dict(format_dict: dict[str, list[str]]) -> str:
    output = StringIO()
    for path, items in sorted(format_dict.items()):
        for item in items:
            output.write(f"{path}: {item}\n")
    return output.getvalue()


def _format_lines_subset_dict(
    report: ProjectReportSubsetProtocol,
) -> defaultdict[str, list[str]]:
    result_dict = defaultdict(list)

    # Missing licenses
    for lic, files in sorted(report.missing_licenses.items()):
        for path in files:
            result_dict[str(path)].append(
                _("missing license '{lic}'").format(lic=lic)
            )

    # Read errors
    for path in report.read_errors:
        result_dict[str(path)].append(_("read error").format(path=path))

    for path, expressions in report.invalid_spdx_expressions.items():
        for expression in sorted(expressions):
            result_dict[str(path)].append(
                _("invalid SPDX License Expression '{expression}'").format(
                    expression=expression
                )
            )

    # Without licenses
    for path in report.files_without_licenses:
        result_dict[str(path)].append(_("no license identifier"))

    # Without copyright
    for path in report.files_without_copyright:
        result_dict[str(path)].append(_("no copyright notice"))

    return result_dict


def format_lines_subset(report: ProjectReportSubsetProtocol) -> str:
    """Formats a subset of a report, namely missing licenses, read errors,
    invalid SPDX License Expressions, files without licenses, and files without
    copyright.

    Args:
        report: A populated report.

    Returns:
        String (in plaintext) that can be output to sys.stdout
    """
    return _output_lines_dict(_format_lines_subset_dict(report))


def format_lines(report: ProjectReport) -> str:
    """Formats report as plaintext strings to be printed to sys.stdout. Sorting
    of output is not guaranteed.

    Args:
        report: A populated report.

    Returns:
        String (in plaintext) that can be output to sys.stdout
    """

    def license_path(lic: str) -> str:
        """Resolve a license identifier to a license path."""
        return str(report.licenses.get(lic))

    result_dict: defaultdict[str, list[str]] = defaultdict(list)

    # Bad licenses
    for lic, path in report.bad_licenses.items():
        result_dict[str(path)].append(_("bad license '{lic}'").format(lic=lic))

    # Deprecated licenses
    for lic in report.deprecated_licenses:
        lic_path = license_path(lic)
        result_dict[lic_path].append(_("deprecated license"))

    # Licenses without extension
    for lic in report.licenses_without_extension:
        lic_path = license_path(lic)
        result_dict[lic_path].append(_("license without file extension"))

    # Unused licenses
    for lic in report.unused_licenses:
        lic_path = license_path(lic)
        result_dict[lic_path].append(_("unused license"))

    subset_dict = _format_lines_subset_dict(report)
    for key, value in subset_dict.items():
        result_dict[key].extend(value)

    return _output_lines_dict(result_dict)
