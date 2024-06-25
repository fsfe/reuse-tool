# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2022 Pietro Albini <pietro.albini@ferrous-systems.com>
# SPDX-FileCopyrightText: 2023 DB Systel GmbH
# SPDX-FileCopyrightText: 2023 Carmen Bianca BAKKER <carmenbianca@fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Module that contains reports about files and projects for linting."""

import bdb
import contextlib
import datetime
import logging
import multiprocessing as mp
import random
from gettext import gettext as _
from hashlib import md5
from io import StringIO
from os import cpu_count
from pathlib import Path, PurePath
from typing import Any, Dict, Iterable, List, NamedTuple, Optional, Set, cast
from uuid import uuid4

from . import __REUSE_version__, __version__
from ._util import _LICENSEREF_PATTERN, _LICENSING, StrPath, _checksum
from .global_licensing import ReuseDep5
from .project import Project, ReuseInfo

_LOGGER = logging.getLogger(__name__)

LINT_VERSION = "1.0"


class _MultiprocessingContainer:
    """Container that remembers some data in order to generate a FileReport."""

    def __init__(
        self, project: Project, do_checksum: bool, add_license_concluded: bool
    ):
        if isinstance(project.global_licensing, ReuseDep5):
            # Remember that a dep5_copyright was (or was not) set prior.
            self.has_dep5 = bool(project.global_licensing)
            # TODO: We create a copy of the project in the following
            # song-and-dance because the debian Copyright object cannot be
            # pickled.
            new_project = Project(
                project.root,
                vcs_strategy=project.vcs_strategy.__class__,
                license_map=project.license_map,
                licenses=project.licenses.copy(),
                # TODO: adjust this method/class to account for REUSE.toml as
                # well. Unset dep5_copyright
                global_licensing=None,
                include_submodules=project.include_submodules,
                include_meson_subprojects=project.include_meson_subprojects,
            )
            new_project.licenses_without_extension = (
                project.licenses_without_extension
            )
            self.project = new_project
        else:
            self.has_dep5 = False
            self.project = project

        self.reuse_dep5: Optional[ReuseDep5] = None
        self.do_checksum = do_checksum
        self.add_license_concluded = add_license_concluded

    def __call__(self, file_: StrPath) -> "_MultiprocessingResult":
        # By remembering that we've parsed the .reuse/dep5, we only parse it
        # once (the first time) inside of each process.
        if self.has_dep5 and not self.reuse_dep5:
            with contextlib.suppress(Exception):
                self.reuse_dep5 = ReuseDep5.from_file(
                    self.project.root / ".reuse/dep5"
                )
                self.project.global_licensing = self.reuse_dep5
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

        Returns:
            Dictionary containing data from the ProjectReport object.
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
            "recommendations": self.recommendations,
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
        # and the recommendations on the bottom
        sorted_keys = sorted(list(unsorted_data.keys()))
        sorted_keys.remove("lint_version")
        sorted_keys.remove("reuse_spec_version")
        sorted_keys.remove("reuse_tool_version")
        sorted_keys.remove("recommendations")
        sorted_keys = (
            [
                "lint_version",
                "reuse_spec_version",
                "reuse_tool_version",
            ]
            + sorted_keys
            + ["recommendations"]
        )

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

        now = datetime.datetime.now(tz=datetime.timezone.utc)
        out.write(f"Created: {now.strftime('%Y-%m-%dT%H:%M:%SZ')}\n")
        out.write(
            "CreatorComment: <text>This document was created automatically"
            " using available reuse information consistent with"
            " REUSE.</text>\n"
        )

        reports = sorted(self.file_reports, key=lambda x: x.name)

        for report in reports:
            out.write(
                "Relationship: SPDXRef-DOCUMENT DESCRIBES"
                f" {report.spdx_id}\n"
            )

        for report in reports:
            out.write("\n")
            out.write(f"FileName: {report.name}\n")
            out.write(f"SPDXID: {report.spdx_id}\n")
            out.write(f"FileChecksum: SHA1: {report.chk_sum}\n")
            out.write(f"LicenseConcluded: {report.license_concluded}\n")

            for lic in sorted(report.licenses_in_file):
                out.write(f"LicenseInfoInFile: {lic}\n")
            if report.copyright:
                out.write(
                    "FileCopyrightText:" f" <text>{report.copyright}</text>\n"
                )
            else:
                out.write("FileCopyrightText: NONE\n")

        # Licenses
        for lic, path in sorted(self.licenses.items()):
            if _LICENSEREF_PATTERN.match(lic):
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
                # Facilitate better debugging by being able to quit the program.
                if isinstance(result.error, bdb.BdbQuit):
                    raise bdb.BdbQuit() from result.error
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
            for lic in file_report.licenses_in_file
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
        """Set of paths that have no licensing information."""
        if self._files_without_licenses is not None:
            return self._files_without_licenses

        self._files_without_licenses = {
            file_report.path
            for file_report in self.file_reports
            if not file_report.licenses_in_file
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
            if not file_report.copyright
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

    @property
    def recommendations(self) -> List[str]:
        """Generate help for next steps based on found REUSE issues"""
        recommendations = []

        # These items should be ordered in the same way as in the summary.
        if self.bad_licenses:
            recommendations.append(
                _(
                    "Fix bad licenses: At least one license in the LICENSES"
                    " directory and/or provided by 'SPDX-License-Identifier'"
                    " tags is invalid. They are either not valid SPDX License"
                    " Identifiers or do not start with 'LicenseRef-'. FAQ about"
                    " custom licenses:"
                    " https://reuse.software/faq/#custom-license"
                )
            )
        if self.deprecated_licenses:
            recommendations.append(
                _(
                    "Fix deprecated licenses: At least one of the licenses in"
                    " the LICENSES directory and/or provided by an"
                    " 'SPDX-License-Identifier' tag or in '.reuse/dep5' has"
                    " been deprecated by SPDX. The current list and their"
                    " respective recommended  new identifiers can be found"
                    " here: <https://spdx.org/licenses/#deprecated>"
                )
            )
        if self.licenses_without_extension:
            recommendations.append(
                _(
                    "Fix licenses without file extension: At least one license"
                    " text file in the 'LICENSES' directory does not have a"
                    " '.txt' file extension. Please rename the file(s)"
                    " accordingly."
                )
            )
        if self.missing_licenses:
            recommendations.append(
                _(
                    "Fix missing licenses: For at least one of the license"
                    " identifiers provided by the 'SPDX-License-Identifier'"
                    " tags, there is no corresponding license text file in the"
                    " 'LICENSES' directory. For SPDX license identifiers, you"
                    " can simply run 'reuse download --all' to get any missing"
                    " ones. For custom licenses (starting with 'LicenseRef-'),"
                    " you need to add these files yourself."
                )
            )
        if self.unused_licenses:
            recommendations.append(
                _(
                    "Fix unused licenses: At least one of the license text"
                    " files in 'LICENSES' is not referenced by any file, e.g."
                    " by an 'SPDX-License-Identifier' tag. Please make sure"
                    " that you either tag the accordingly licensed files"
                    " properly, or delete the unused license text if you are"
                    " sure that no file or code snippet is licensed as such."
                )
            )
        if self.read_errors:
            recommendations.append(
                _(
                    "Fix read errors: At least one of the files in your"
                    " directory cannot be read by the tool. Please check the"
                    " file permissions. You will find the affected files at the"
                    " top of the output as part of the logged error messages."
                )
            )
        if self.files_without_copyright or self.files_without_licenses:
            recommendations.append(
                _(
                    "Fix missing copyright/licensing information: For one or"
                    " more files, the tool cannot find copyright and/or"
                    " licensing information. You typically do this by adding"
                    " 'SPDX-FileCopyrightText' and 'SPDX-License-Identifier'"
                    " tags to each file. The tutorial explains additional ways"
                    " to do this: <https://reuse.software/tutorial/>"
                )
            )

        return recommendations


class FileReport:  # pylint: disable=too-many-instance-attributes
    """Object that holds a linting report about a single file."""

    def __init__(self, name: str, path: StrPath, do_checksum: bool = True):
        self.name = name
        self.path = Path(path)
        self.do_checksum = do_checksum

        self.reuse_infos: List[ReuseInfo] = []

        self.spdx_id: Optional[str] = None
        self.chk_sum: Optional[str] = None
        self.licenses_in_file: List[str] = []
        self.license_concluded: str = ""
        self.copyright: str = ""

        self.bad_licenses: Set[str] = set()
        self.missing_licenses: Set[str] = set()

    def to_dict_lint(self) -> Dict[str, Any]:
        """Turn the report into a json-like dictionary with exclusively
        information relevant for linting.
        """
        return {
            # This gets rid of the './' prefix. In Python 3.9, use
            # str.removeprefix.
            "path": PurePath(self.name).as_posix(),
            "copyrights": [
                {
                    "value": line,
                    "source": reuse_info.source_path,
                    "source_type": (
                        reuse_info.source_type.value
                        if reuse_info.source_type
                        else None
                    ),
                }
                for reuse_info in self.reuse_infos
                for line in reuse_info.copyright_lines
            ],
            "spdx_expressions": [
                {
                    "value": str(expression),
                    "source": reuse_info.source_path,
                    "source_type": (
                        reuse_info.source_type.value
                        if reuse_info.source_type
                        else None
                    ),
                }
                for reuse_info in self.reuse_infos
                for expression in reuse_info.spdx_expressions
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
        if not path.is_file():
            raise OSError(f"{path} is not a file")

        relative = project.relative_from_root(path)
        report = cls(f"./{relative}", path, do_checksum=do_checksum)

        # Checksum and ID
        if report.do_checksum:
            report.chk_sum = _checksum(path)
        else:
            # This path avoids a lot of heavy computation, which is handy for
            # scenarios where you only need a unique hash, not a consistent
            # hash.
            report.chk_sum = f"{random.getrandbits(160):040x}"
        spdx_id = md5()
        spdx_id.update(report.name.encode("utf-8"))
        spdx_id.update(report.chk_sum.encode("utf-8"))
        report.spdx_id = f"SPDXRef-{spdx_id.hexdigest()}"

        reuse_infos = project.reuse_info_of(path)
        for reuse_info in reuse_infos:
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
                    report.licenses_in_file.append(identifier)

        if not add_license_concluded:
            report.license_concluded = "NOASSERTION"
        elif not any(reuse_info.spdx_expressions for reuse_info in reuse_infos):
            report.license_concluded = "NONE"
        else:
            # Merge all the license expressions together, wrapping them in
            # parentheses to make sure an expression doesn't spill into another
            # one. The extra parentheses will be removed by the roundtrip
            # through parse() -> simplify() -> render().
            report.license_concluded = (
                _LICENSING.parse(
                    " AND ".join(
                        f"({expression})"
                        for reuse_info in reuse_infos
                        for expression in reuse_info.spdx_expressions
                    ),
                )
                .simplify()
                .render()
            )

        # Copyright text
        report.copyright = "\n".join(
            sorted(
                line
                for reuse_info in reuse_infos
                for line in reuse_info.copyright_lines
            )
        )
        # Source of licensing and copyright info
        report.reuse_infos = reuse_infos
        return report

    def __hash__(self) -> int:
        if self.chk_sum is not None:
            return hash(self.name + self.chk_sum)
        return super().__hash__()


def format_creator(creator: Optional[str]) -> str:
    """Render the creator field based on the provided flag"""
    if creator is None:
        return "Anonymous ()"
    if "(" in creator and creator.endswith(")"):
        # The creator field already contains an email address
        return creator
    return creator + " ()"
