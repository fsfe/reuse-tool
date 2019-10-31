# SPDX-FileCopyrightText: 2017-2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Module that contains reports about files and projects for linting."""

import datetime
import logging
import random
from gettext import gettext as _
from hashlib import md5
from io import StringIO
from os import PathLike
from pathlib import Path
from typing import Iterable, List, NamedTuple, Set
from uuid import uuid4

from . import __version__
from ._util import _LICENSING, _checksum
from .project import Project

_LOGGER = logging.getLogger(__name__)

FileReportInfo = NamedTuple(
    "FileReportInfo",
    [
        ("file_report", "FileReport"),
        ("bad_licenses", Set[str]),
        ("missing_licenses", Set[str]),
    ],
)


class ProjectReport:  # pylint: disable=too-many-instance-attributes
    """Object that holds linting report about the project."""

    def __init__(self, do_checksum: bool = True):
        self.path = None
        self.licenses = dict()
        self.missing_licenses = dict()
        self.bad_licenses = dict()
        self.read_errors = set()
        self.file_reports = set()

        self.do_checksum = do_checksum

        self._unused_licenses = None
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
            "missing_licenses": {
                lic: [str(file_) for file_ in files]
                for lic, files in self.missing_licenses.items()
            },
            "bad_licenses": {
                lic: [str(file_) for file_ in files]
                for lic, files in self.bad_licenses.items()
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

        out.write("DocumentName: {}\n".format(Path(self.path).resolve().name))
        # TODO: Generate UUID from git revision maybe
        # TODO: Fix the URL
        out.write(
            "DocumentNamespace: "
            "http://spdx.org/spdxdocs/spdx-v2.1-{}\n".format(uuid4())
        )

        # Author
        # TODO: Fix Person and Organization
        out.write("Creator: Person: Anonymous ()\n")
        out.write("Creator: Organization: Anonymous ()\n")
        out.write("Creator: Tool: reuse-{}\n".format(__version__))

        now = datetime.datetime.utcnow()
        now = now.replace(microsecond=0)
        out.write("Created: {}Z\n".format(now.isoformat()))
        out.write(
            "CreatorComment: <text>This document was created automatically "
            "using available reuse information consistent with "
            "REUSE.</text>\n"
        )

        reports = sorted(self.file_reports, key=lambda x: x.spdxfile.name)

        for report in reports:
            out.write(
                "Relationship: SPDXRef-DOCUMENT describes {}\n".format(
                    report.spdxfile.spdx_id
                )
            )

        for report in reports:
            out.write("\n")
            out.write("FileName: {}\n".format(report.spdxfile.name))
            out.write("SPDXID: {}\n".format(report.spdxfile.spdx_id))
            out.write(
                "FileChecksum: SHA1: {}\n".format(report.spdxfile.chk_sum)
            )
            # IMPORTANT: Make no assertion about concluded license. This tool
            # cannot, with full certainty, determine the license of a file.
            out.write("LicenseConcluded: NOASSERTION\n")

            for lic in sorted(report.spdxfile.licenses_in_file):
                out.write("LicenseInfoInFile: {}\n".format(lic))
            if report.spdxfile.copyright:
                out.write(
                    "FileCopyrightText: <text>{}</text>\n".format(
                        report.spdxfile.copyright
                    )
                )
            else:
                out.write("FileCopyrightText: NONE\n")

        # Licenses
        for lic, path in sorted(self.licenses.items()):
            if lic.startswith("LicenseRef-"):
                out.write("\n")
                out.write("LicenseID: {}\n".format(lic))
                out.write("LicenseName: NOASSERTION\n")

                with (Path(self.path) / path).open() as fp:
                    out.write(
                        "ExtractedText: <text>{}</text>\n".format(fp.read())
                    )

        return out.getvalue()

    @classmethod
    def generate(
        cls,
        project: Project,
        paths: Iterable[PathLike] = None,
        do_checksum: bool = True,
    ) -> "ProjectReport":
        """Generate a ProjectReport from a Project."""
        if paths is None:
            paths = [project.root]

        project_report = cls(do_checksum=do_checksum)
        project_report.path = project.root
        project_report.licenses = project.licenses
        for path in paths:
            for file_ in project.all_files(path):
                try:
                    lint_file_info = FileReport.generate(
                        project, file_, do_checksum=project_report.do_checksum
                    )
                except (OSError, UnicodeError):
                    # Translators: %s is a path.
                    _LOGGER.info(_("Could not read %s"), file_)
                    project_report.read_errors.add(file_)
                    continue

                # File report.
                project_report.file_reports.add(lint_file_info.file_report)

                # Bad and missing licenses.
                for license in lint_file_info.missing_licenses:
                    project_report.missing_licenses.setdefault(
                        license, set()
                    ).add(lint_file_info.file_report.path)
                for license in lint_file_info.bad_licenses:
                    project_report.bad_licenses.setdefault(license, set()).add(
                        lint_file_info.file_report.path
                    )

        # More bad licenses
        for name, path in project.licenses.items():
            if name not in project.license_map:
                project_report.bad_licenses.setdefault(name, set()).add(path)

        return project_report

    @property
    def used_licenses(self) -> Set[str]:
        """Set of license identifiers that are found in file reports."""
        return set(self.licenses) - self.unused_licenses

    @property
    def unused_licenses(self) -> Set[str]:
        """Set of license identifiers that are not found in any file report."""
        if self._unused_licenses is not None:
            return self._unused_licenses

        used_licenses = set()
        unused_licenses = set()

        for file_report in self.file_reports:
            for lic in file_report.spdxfile.licenses_in_file:
                used_licenses.add(lic)

        for lic in self.licenses:
            if lic not in used_licenses:
                unused_licenses.add(lic)

        self._unused_licenses = unused_licenses
        return unused_licenses

    @property
    def files_without_licenses(self) -> Iterable[PathLike]:
        """Iterable of paths that have no license information."""
        if self._files_without_licenses is not None:
            return self._files_without_licenses

        files_without_licenses = []

        for file_report in self.file_reports:
            if not file_report.spdxfile.licenses_in_file:
                files_without_licenses.append(file_report.path)

        self._files_without_licenses = files_without_licenses
        return files_without_licenses

    @property
    def files_without_copyright(self) -> Iterable[PathLike]:
        """Iterable of paths that have no copyright information."""
        if self._files_without_copyright is not None:
            return self._files_without_copyright

        files_without_copyright = []

        for file_report in self.file_reports:
            if not file_report.spdxfile.copyright:
                files_without_copyright.append(file_report.path)

        self._files_without_copyright = files_without_copyright
        return files_without_copyright


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

    def to_dict(self):
        """Turn the report into a json-like dictionary."""
        return {
            "path": str(Path(self.path).resolve()),
            "name": self.spdxfile.name,
            "spdx_id": self.spdxfile.spdx_id,
            "chk_sum": self.spdxfile.chk_sum,
            "licenses_in_file": [
                lic for lic in self.spdxfile.licenses_in_file
            ],
            "copyright": self.spdxfile.copyright,
        }

    @classmethod
    def generate(
        cls, project: Project, path: PathLike, do_checksum: bool = True
    ) -> FileReportInfo:
        """Generate a FileReport from a path in a Project."""
        path = Path(path)
        if not path.is_file():
            raise OSError("{} is not a file".format(path))

        # pylint: disable=protected-access
        relative = project._relative_from_root(path)
        report = cls("./" + str(relative), path, do_checksum=do_checksum)

        bad_licenses = set()
        missing_licenses = set()

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
        report.spdxfile.spdx_id = "SPDXRef-{}".format(spdx_id.hexdigest())

        spdx_info = project.spdx_info_of(path)
        for expression in spdx_info.spdx_expressions:
            for identifier in _LICENSING.license_keys(expression):
                # Bad license
                if identifier not in project.license_map:
                    bad_licenses.add(identifier)
                # Missing license
                elif identifier not in project.licenses:
                    missing_licenses.add(identifier)

                # Add license to report.
                report.spdxfile.licenses_in_file.append(identifier)

        # Copyright text
        report.spdxfile.copyright = "\n".join(
            sorted(spdx_info.copyright_lines)
        )

        return FileReportInfo(report, bad_licenses, missing_licenses)

    def __hash__(self):
        if self.spdxfile.chk_sum is not None:
            return hash(self.spdxfile.name + self.spdxfile.chk_sum)
        return super().__hash__(self)
