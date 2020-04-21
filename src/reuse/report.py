# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
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
from os import PathLike, cpu_count
from pathlib import Path
from typing import Iterable, List, NamedTuple, Optional, Set
from uuid import uuid4

from . import __version__
from ._util import _LICENSING, _checksum
from .project import Project

_LOGGER = logging.getLogger(__name__)


class _MultiprocessingContainer:
    """Container that remembers some data in order to generate a FileReport."""

    # pylint: disable=too-few-public-methods

    def __init__(self, project, do_checksum):
        self.project = project
        self.do_checksum = do_checksum

    def __call__(self, file_):
        # pylint: disable=broad-except
        try:
            return _MultiprocessingResult(
                file_,
                FileReport.generate(
                    self.project, file_, do_checksum=self.do_checksum
                ),
                None,
            )
        except Exception as exc:
            return _MultiprocessingResult(file_, None, exc)


class _MultiprocessingResult(NamedTuple):
    """Result of :class:`MultiprocessingContainer`."""

    path: PathLike
    report: Optional["FileReport"]
    error: Optional[Exception]


class ProjectReport:  # pylint: disable=too-many-instance-attributes
    """Object that holds linting report about the project."""

    def __init__(self, do_checksum: bool = True):
        self.path = None
        self.licenses = dict()
        self.missing_licenses = dict()
        self.bad_licenses = dict()
        self.deprecated_licenses = set()
        self.read_errors = set()
        self.file_reports = set()
        self.licenses_without_extension = dict()

        self.do_checksum = do_checksum

        self._unused_licenses = None
        self._used_licenses = None
        self._files_without_licenses = None
        self._files_without_copyright = None

    def to_dict(self):
        """Turn the report into a json-like dictionary."""
        return {
            "path": str(Path(self.path).resolve()),
            "licenses": {
                identifier: str(path)
                for identifier, path in self.licenses.items()
            },
            "bad_licenses": {
                lic: [str(file_) for file_ in files]
                for lic, files in self.bad_licenses.items()
            },
            "deprecated_licenses": sorted(self.deprecated_licenses),
            "licenses_without_extension": {
                identifier: str(path)
                for identifier, path in self.licenses_without_extension.items()
            },
            "missing_licenses": {
                lic: [str(file_) for file_ in files]
                for lic, files in self.missing_licenses.items()
            },
            "read_errors": list(map(str, self.read_errors)),
            "file_reports": [report.to_dict() for report in self.file_reports],
        }

    def bill_of_materials(self) -> str:
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
            f"DocumentNamespace:"
            f" http://spdx.org/spdxdocs/spdx-v2.1-{uuid4()}\n"
        )

        # Author
        # TODO: Fix Person and Organization
        out.write("Creator: Person: Anonymous ()\n")
        out.write("Creator: Organization: Anonymous ()\n")
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
                f"Relationship: SPDXRef-DOCUMENT describes"
                f" {report.spdxfile.spdx_id}\n"
            )

        for report in reports:
            out.write("\n")
            out.write(f"FileName: {report.spdxfile.name}\n")
            out.write(f"SPDXID: {report.spdxfile.spdx_id}\n")
            out.write(f"FileChecksum: SHA1: {report.spdxfile.chk_sum}\n")
            # IMPORTANT: Make no assertion about concluded license. This tool
            # cannot, with full certainty, determine the license of a file.
            out.write("LicenseConcluded: NOASSERTION\n")

            for lic in sorted(report.spdxfile.licenses_in_file):
                out.write(f"LicenseInfoInFile: {lic}\n")
            if report.spdxfile.copyright:
                out.write(
                    f"FileCopyrightText:"
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

                with (Path(self.path) / path).open() as fp:
                    out.write(f"ExtractedText: <text>{fp.read()}</text>\n")

        return out.getvalue()

    @classmethod
    def generate(
        cls,
        project: Project,
        do_checksum: bool = True,
        multiprocessing: bool = cpu_count() > 1,
    ) -> "ProjectReport":
        """Generate a ProjectReport from a Project."""
        project_report = cls(do_checksum=do_checksum)
        project_report.path = project.root
        project_report.licenses = project.licenses
        project_report.licenses_without_extension = (
            project.licenses_without_extension
        )

        container = _MultiprocessingContainer(project, do_checksum)

        if multiprocessing:
            pool = mp.Pool()

            results = pool.map(container, project.all_files())

            pool.close()
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
                    project_report.read_errors.add(result.path)
                    continue
                _LOGGER.error(
                    _(
                        "Unexpected error occurred while parsing '{path}'"
                    ).format(path=result.path),
                    exc_info=result.error,
                )
                project_report.read_errors.add(result.path)
                continue
            file_report = result.report

            # File report.
            project_report.file_reports.add(file_report)

            # Bad and missing licenses.
            for license in file_report.missing_licenses:
                project_report.missing_licenses.setdefault(license, set()).add(
                    file_report.path
                )
            for license in file_report.bad_licenses:
                project_report.bad_licenses.setdefault(license, set()).add(
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

        self._used_licenses = set(self.licenses) - self.unused_licenses
        return self._used_licenses

    @property
    def unused_licenses(self) -> Set[str]:
        """Set of license identifiers that are not found in any file report."""
        if self._unused_licenses is not None:
            return self._unused_licenses

        all_used_licenses = {
            lic
            for file_report in self.file_reports
            for lic in file_report.spdxfile.licenses_in_file
        }
        self._unused_licenses = {
            lic
            for file_report in self.file_reports
            for lic in file_report.spdxfile.licenses_in_file
            if lic not in all_used_licenses
        }

        return self._unused_licenses

    @property
    def files_without_licenses(self) -> Iterable[PathLike]:
        """Iterable of paths that have no license information."""
        if self._files_without_licenses is not None:
            return self._files_without_licenses

        self._files_without_licenses = {
            file_report.path
            for file_report in self.file_reports
            if not file_report.spdxfile.licenses_in_file
        }

        return self._files_without_licenses

    @property
    def files_without_copyright(self) -> Iterable[PathLike]:
        """Iterable of paths that have no copyright information."""
        if self._files_without_copyright is not None:
            return self._files_without_copyright

        self._files_without_copyright = {
            file_report.path
            for file_report in self.file_reports
            if not file_report.spdxfile.copyright
        }

        return self._files_without_copyright


class _File:  # pylint: disable=too-few-public-methods
    """Represent an SPDX file. Sufficiently enough for our purposes, in any
    case.
    """

    def __init__(self, name, spdx_id=None, chk_sum=None):
        self.name: str = name
        self.spdx_id: str = spdx_id
        self.chk_sum: str = chk_sum
        self.licenses_in_file: List[str] = []
        self.copyright: str = None


class FileReport:
    """Object that holds a linting report about a single file. Importantly,
    it also contains SPDX File information in :attr:`spdxfile`.
    """

    def __init__(
        self, name: PathLike, path: PathLike, do_checksum: bool = True
    ):
        self.spdxfile = _File(name)
        self.path = Path(path)
        self.do_checksum = do_checksum

        self.bad_licenses = set()
        self.missing_licenses = set()

    def to_dict(self):
        """Turn the report into a json-like dictionary."""
        return {
            "path": str(Path(self.path).resolve()),
            "name": self.spdxfile.name,
            "spdx_id": self.spdxfile.spdx_id,
            "chk_sum": self.spdxfile.chk_sum,
            "licenses_in_file": sorted(self.spdxfile.licenses_in_file),
            "copyright": self.spdxfile.copyright,
        }

    @classmethod
    def generate(
        cls, project: Project, path: PathLike, do_checksum: bool = True
    ) -> "FileReport":
        """Generate a FileReport from a path in a Project."""
        path = Path(path)
        if not path.is_file():
            raise OSError(f"{path} is not a file")

        # pylint: disable=protected-access
        relative = project.relative_from_root(path)
        report = cls("./" + str(relative), path, do_checksum=do_checksum)

        # Checksum and ID
        if report.do_checksum:
            report.spdxfile.chk_sum = _checksum(path)
        else:
            # This path avoids a lot of heavy computation, which is handy for
            # scenarios where you only need a unique hash, not a consistent
            # hash.
            report.spdxfile.chk_sum = "%040x" % random.getrandbits(40)
        spdx_id = md5()
        spdx_id.update(str(relative).encode("utf-8"))
        spdx_id.update(report.spdxfile.chk_sum.encode("utf-8"))
        report.spdxfile.spdx_id = f"SPDXRef-{spdx_id.hexdigest()}"

        spdx_info = project.spdx_info_of(path)
        for expression in spdx_info.spdx_expressions:
            for identifier in _LICENSING.license_keys(expression):
                # Bad license
                if identifier not in project.license_map:
                    report.bad_licenses.add(identifier)
                # Missing license
                if identifier not in project.licenses:
                    report.missing_licenses.add(identifier)

                # Add license to report.
                report.spdxfile.licenses_in_file.append(identifier)

        # Copyright text
        report.spdxfile.copyright = "\n".join(
            sorted(spdx_info.copyright_lines)
        )

        return report

    def __hash__(self):
        if self.spdxfile.chk_sum is not None:
            return hash(self.spdxfile.name + self.spdxfile.chk_sum)
        return super().__hash__(self)
