# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2022 Pietro Albini <pietro.albini@ferrous-systems.com>
# SPDX-FileCopyrightText: 2023 Matthias Riße
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Module that contains reports about files and projects for linting."""

import datetime
import logging
import multiprocessing as mp
import random
from gettext import gettext as _
from hashlib import md5
from io import StringIO
from os import cpu_count
from pathlib import Path
from typing import Any, Dict, Iterable, List, NamedTuple, Optional, Set, cast
from uuid import uuid4

from . import __REUSE_version__, __version__
from ._util import _LICENSING, StrPath, _checksum
from .project import Project, ReuseInfo

_LOGGER = logging.getLogger(__name__)

LINT_VERSION = "1.0"


class _MultiprocessingContainer:
    """Container that remembers some data in order to generate a FileReport."""

    def __init__(
        self, project: Project, do_checksum: bool, add_license_concluded: bool
    ):
        self.project = project
        self.do_checksum = do_checksum
        self.add_license_concluded = add_license_concluded

    def __call__(self, file_: StrPath) -> "_MultiprocessingResult":
        # pylint: disable=broad-except
        try:
            return _MultiprocessingResult(
                file_,
                FileReport.generate(
                    self.project,
                    file_,
                    do_checksum=self.do_checksum,
                    add_license_concluded=self.add_license_concluded,
                ),
                None,
            )
        except Exception as exc:
            return _MultiprocessingResult(file_, None, exc)


class _MultiprocessingResult(NamedTuple):
    """Result of :class:`MultiprocessingContainer`."""

    path: StrPath
    report: Optional["FileReport"]
    error: Optional[Exception]


class ProjectReport:  # pylint: disable=too-many-instance-attributes
    """Object that holds linting report about the project."""

    def __init__(self, do_checksum: bool = True):
        self.path: StrPath = ""
        self.licenses: Dict[str, Path] = {}
        self.missing_licenses: Dict[str, Set[Path]] = {}
        self.bad_licenses: Dict[str, Set[Path]] = {}
        self.deprecated_licenses: Set[str] = set()
        self.read_errors: Set[Path] = set()
        self.file_reports: Set[FileReport] = set()
        self.licenses_without_extension: Dict[str, Path] = {}

        self.do_checksum = do_checksum

        self._unused_licenses: Optional[Set[str]] = None
        self._used_licenses: Optional[Set[str]] = None
        self._files_without_licenses: Optional[Set[Path]] = None
        self._files_without_copyright: Optional[Set[Path]] = None
        self._is_compliant: Optional[bool] = None

    def to_dict_lint(self) -> Dict[str, Any]:
        """Collects and formats data relevant to linting from report and returns
        it as a dictionary.

        :return: Dictionary containing data from the ProjectReport object
        """
        # Setup report data container
        data: Dict[str, Any] = {
            "non_compliant": {
                "missing_licenses": self.missing_licenses,
                "unused_licenses": [str(file) for file in self.unused_licenses],
                "deprecated_licenses": [
                    str(file) for file in self.deprecated_licenses
                ],
                "bad_licenses": self.bad_licenses,
                "licenses_without_extension": self.licenses_without_extension,
                "missing_copyright_info": [
                    str(file) for file in self.files_without_copyright
                ],
                "missing_licensing_info": [
                    str(file) for file in self.files_without_licenses
                ],
                "read_errors": [str(file) for file in self.read_errors],
            },
            "files": [],
            "summary": {
                "used_licenses": [],
            },
        }

        # Populate 'files'
        for file_report in self.file_reports:
            data["files"].append(file_report.to_dict_lint())

        # Populate 'summary'
        number_of_files = len(self.file_reports)
        data["summary"] = {
            "used_licenses": list(self.used_licenses),
            "files_total": number_of_files,
            "files_with_copyright_info": number_of_files
            - len(self.files_without_copyright),
            "files_with_licensing_info": number_of_files
            - len(self.files_without_licenses),
            "compliant": self.is_compliant,
        }

        # Add the top three keys
        unsorted_data = {
            "lint_version": LINT_VERSION,
            "reuse_spec_version": __REUSE_version__,
            "reuse_tool_version": __version__,
            **data,
        }

        # Sort dictionary keys while keeping the top three keys at the beginning
        sorted_keys = sorted(list(unsorted_data.keys()))
        sorted_keys.remove("lint_version")
        sorted_keys.remove("reuse_spec_version")
        sorted_keys.remove("reuse_tool_version")
        sorted_keys = [
            "lint_version",
            "reuse_spec_version",
            "reuse_tool_version",
        ] + sorted_keys

        sorted_data = {key: unsorted_data[key] for key in sorted_keys}

        return sorted_data

    def bill_of_materials(
        self,
        creator_person: Optional[str] = None,
        creator_organization: Optional[str] = None,
    ) -> str:
        """Generate a bill of materials from the project.

        See https://spdx.org/specifications.
        """
        out = StringIO()
        # Write mandatory tags
        out.write("SPDXVersion: SPDX-2.1\n")
        out.write("DataLicense: CC0-1.0\n")
        out.write("SPDXID: SPDXRef-DOCUMENT\n")

        out.write(f"DocumentName: {Path(self.path).resolve().name}\n")
        # TODO: Generate UUID from git revision maybe
        # TODO: Fix the URL
        out.write(
            f"DocumentNamespace: http://spdx.org/spdxdocs/spdx-v2.1-{uuid4()}\n"
        )

        # Author
        out.write(f"Creator: Person: {format_creator(creator_person)}\n")
        out.write(
            f"Creator: Organization: {format_creator(creator_organization)}\n"
        )
        out.write(f"Creator: Tool: reuse-{__version__}\n")

        now = datetime.datetime.utcnow()
        now = now.replace(microsecond=0)
        out.write(f"Created: {now.isoformat()}Z\n")
        out.write(
            "CreatorComment: <text>This document was created automatically"
            " using available reuse information consistent with"
            " REUSE.</text>\n"
        )

        reports = sorted(self.file_reports, key=lambda x: x.spdxfile.name)

        for report in reports:
            out.write(
                "Relationship: SPDXRef-DOCUMENT describes"
                f" {report.spdxfile.spdx_id}\n"
            )

        for report in reports:
            out.write("\n")
            out.write(f"FileName: {report.spdxfile.name}\n")
            out.write(f"SPDXID: {report.spdxfile.spdx_id}\n")
            out.write(f"FileChecksum: SHA1: {report.spdxfile.chk_sum}\n")
            out.write(
                f"LicenseConcluded: {report.spdxfile.license_concluded}\n"
            )

            for lic in sorted(report.spdxfile.licenses_in_file):
                out.write(f"LicenseInfoInFile: {lic}\n")
            if report.spdxfile.copyright:
                out.write(
                    "FileCopyrightText:"
                    f" <text>{report.spdxfile.copyright}</text>\n"
                )
            else:
                out.write("FileCopyrightText: NONE\n")

        # Licenses
        for lic, path in sorted(self.licenses.items()):
            if lic.startswith("LicenseRef-"):
                out.write("\n")
                out.write(f"LicenseID: {lic}\n")
                out.write("LicenseName: NOASSERTION\n")

                with (Path(self.path) / path).open(encoding="utf-8") as fp:
                    out.write(f"ExtractedText: <text>{fp.read()}</text>\n")

        return out.getvalue()

    @classmethod
    def generate(
        cls,
        project: Project,
        do_checksum: bool = True,
        multiprocessing: bool = cpu_count() > 1,  # type: ignore
        add_license_concluded: bool = False,
    ) -> "ProjectReport":
        """Generate a ProjectReport from a Project."""
        project_report = cls(do_checksum=do_checksum)
        project_report.path = project.root
        project_report.licenses = project.licenses
        project_report.licenses_without_extension = (
            project.licenses_without_extension
        )

        container = _MultiprocessingContainer(
            project, do_checksum, add_license_concluded
        )

        if multiprocessing:
            with mp.Pool() as pool:
                results: Iterable[_MultiprocessingResult] = pool.map(
                    container, project.all_files()
                )
            pool.join()
        else:
            results = map(container, project.all_files())

        for result in results:
            if result.error:
                if isinstance(result.error, (OSError, UnicodeError)):
                    _LOGGER.error(
                        _("Could not read '{path}'").format(path=result.path),
                        exc_info=result.error,
                    )
                    project_report.read_errors.add(Path(result.path))
                    continue
                _LOGGER.error(
                    _(
                        "Unexpected error occurred while parsing '{path}'"
                    ).format(path=result.path),
                    exc_info=result.error,
                )
                project_report.read_errors.add(Path(result.path))
                continue
            file_report = cast(FileReport, result.report)

            # File report.
            project_report.file_reports.add(file_report)

            # Missing licenses.
            for missing_license in file_report.missing_licenses:
                project_report.missing_licenses.setdefault(
                    missing_license, set()
                ).add(file_report.path)

            # Bad licenses
            for bad_license in file_report.bad_licenses:
                project_report.bad_licenses.setdefault(bad_license, set()).add(
                    file_report.path
                )

        # More bad licenses, and also deprecated licenses
        for name, path in project.licenses.items():
            if name not in project.license_map:
                project_report.bad_licenses.setdefault(name, set()).add(path)
            elif project.license_map[name]["isDeprecatedLicenseId"]:
                project_report.deprecated_licenses.add(name)

        return project_report

    @property
    def used_licenses(self) -> Set[str]:
        """Set of license identifiers that are found in file reports."""
        if self._used_licenses is not None:
            return self._used_licenses

        self._used_licenses = {
            lic
            for file_report in self.file_reports
            for lic in file_report.spdxfile.licenses_in_file
        }
        return self._used_licenses

    @property
    def unused_licenses(self) -> Set[str]:
        """Set of license identifiers that are not found in any file report."""
        if self._unused_licenses is not None:
            return self._unused_licenses

        # First collect licenses that are suspected to be unused.
        suspected_unused_licenses = {
            lic for lic in self.licenses if lic not in self.used_licenses
        }
        # Remove false positives.
        self._unused_licenses = {
            lic
            for lic in suspected_unused_licenses
            if f"{lic}+" not in self.used_licenses
        }
        return self._unused_licenses

    @property
    def files_without_licenses(self) -> Set[Path]:
        """Set of paths that have no license information."""
        if self._files_without_licenses is not None:
            return self._files_without_licenses

        self._files_without_licenses = {
            file_report.path
            for file_report in self.file_reports
            if not file_report.spdxfile.licenses_in_file
        }

        return self._files_without_licenses

    @property
    def files_without_copyright(self) -> Set[Path]:
        """Set of paths that have no copyright information."""
        if self._files_without_copyright is not None:
            return self._files_without_copyright

        self._files_without_copyright = {
            file_report.path
            for file_report in self.file_reports
            if not file_report.spdxfile.copyright
        }

        return self._files_without_copyright

    @property
    def is_compliant(self) -> bool:
        """Whether the report is compliant with the REUSE Spec."""
        if self._is_compliant is not None:
            return self._is_compliant

        self._is_compliant = not any(
            (
                self.missing_licenses,
                self.unused_licenses,
                self.bad_licenses,
                self.deprecated_licenses,
                self.licenses_without_extension,
                self.files_without_copyright,
                self.files_without_licenses,
                self.read_errors,
            )
        )

        return self._is_compliant


class _File:  # pylint: disable=too-few-public-methods
    """Represent an SPDX file. Sufficiently enough for our purposes, in any
    case.
    """

    def __init__(
        self,
        name: str,
        spdx_id: Optional[str] = None,
        chk_sum: Optional[str] = None,
    ):
        self.name: str = name
        self.spdx_id: Optional[str] = spdx_id
        self.chk_sum: Optional[str] = chk_sum
        self.licenses_in_file: List[str] = []
        self.license_concluded: str = ""
        self.copyright: str = ""
        self.info: ReuseInfo = ReuseInfo()


class FileReport:
    """Object that holds a linting report about a single file. Importantly,
    it also contains SPDX File information in :attr:`spdxfile`.
    """

    def __init__(self, name: StrPath, path: StrPath, do_checksum: bool = True):
        self.spdxfile = _File(str(name))
        self.path = Path(path)
        self.do_checksum = do_checksum

        self.bad_licenses: Set[str] = set()
        self.missing_licenses: Set[str] = set()

    def to_dict_lint(self) -> Dict[str, Any]:
        """Turn the report into a json-like dictionary with exclusively
        information relevant for linting.
        """
        return {
            "path": str(Path(self.path).resolve()),
            # TODO: Why does every copyright line have the same source?
            "copyrights": [
                {"value": copyright_, "source": self.spdxfile.info.source_path}
                for copyright_ in self.spdxfile.copyright.split("\n")
                if copyright_
            ],
            # TODO: Why does every license expression have the same source?
            "licenses": [
                {"value": license_, "source": self.spdxfile.info.source_path}
                for license_ in self.spdxfile.licenses_in_file
                if license_
            ],
        }

    @classmethod
    def generate(
        cls,
        project: Project,
        path: StrPath,
        do_checksum: bool = True,
        add_license_concluded: bool = False,
    ) -> "FileReport":
        """Generate a FileReport from a path in a Project."""
        path = Path(path)
        if not path.is_file() and not path.is_symlink():
            raise OSError(f"{path} is not supported")

        relative = project.relative_from_root(path)
        report = cls("./" + str(relative), path, do_checksum=do_checksum)

        # Checksum and ID
        if report.do_checksum and not path.is_symlink():
            report.spdxfile.chk_sum = _checksum(path)
        else:
            # This path avoids a lot of heavy computation, which is handy for
            # scenarios where you only need a unique hash, not a consistent
            # hash.
            report.spdxfile.chk_sum = f"{random.getrandbits(160):040x}"
        spdx_id = md5()
        spdx_id.update(str(relative).encode("utf-8"))
        spdx_id.update(report.spdxfile.chk_sum.encode("utf-8"))
        report.spdxfile.spdx_id = f"SPDXRef-{spdx_id.hexdigest()}"

        reuse_info = project.reuse_info_of(path)
        for expression in reuse_info.spdx_expressions:
            for identifier in _LICENSING.license_keys(expression):
                # A license expression akin to Apache-1.0+ should register
                # correctly if LICENSES/Apache-1.0.txt exists.
                identifiers = {identifier}
                if identifier.endswith("+"):
                    identifiers.add(identifier[:-1])
                # Bad license
                if not identifiers.intersection(project.license_map):
                    report.bad_licenses.add(identifier)
                # Missing license
                if not identifiers.intersection(project.licenses):
                    report.missing_licenses.add(identifier)

                # Add license to report.
                report.spdxfile.licenses_in_file.append(identifier)

        if not add_license_concluded:
            report.spdxfile.license_concluded = "NOASSERTION"
        elif not reuse_info.spdx_expressions:
            report.spdxfile.license_concluded = "NONE"
        else:
            # Merge all the license expressions together, wrapping them in
            # parentheses to make sure an expression doesn't spill into another
            # one. The extra parentheses will be removed by the roundtrip
            # through parse() -> simplify() -> render().
            report.spdxfile.license_concluded = (
                _LICENSING.parse(
                    " AND ".join(
                        f"({expression})"
                        for expression in reuse_info.spdx_expressions
                    ),
                )
                .simplify()
                .render()
            )

        # Copyright text
        report.spdxfile.copyright = "\n".join(
            sorted(reuse_info.copyright_lines)
        )
        # Source of licensing and copyright info
        report.spdxfile.info = reuse_info
        return report

    def __hash__(self) -> int:
        if self.spdxfile.chk_sum is not None:
            return hash(self.spdxfile.name + self.spdxfile.chk_sum)
        return super().__hash__()


def format_creator(creator: Optional[str]) -> str:
    """Render the creator field based on the provided flag"""
    if creator is None:
        return "Anonymous ()"
    if "(" in creator and creator.endswith(")"):
        # The creator field already contains an email address
        return creator
    return creator + " ()"
