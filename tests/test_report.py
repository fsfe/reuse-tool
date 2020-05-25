# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for reuse.report"""

# pylint: disable=invalid-name

import os
import sys

import pytest

from reuse.project import Project
from reuse.report import FileReport, ProjectReport

try:
    import posix as is_posix
except ImportError:
    is_posix = False

cpython = pytest.mark.skipif(
    sys.implementation.name != "cpython", reason="only CPython supported"
)
posix = pytest.mark.skipif(not is_posix, reason="Windows not supported")


def test_generate_file_report_file_simple(fake_repository):
    """An extremely simple generate test, just to see if the function doesn't
    crash.
    """
    project = Project(fake_repository)
    result = FileReport.generate(project, "src/source_code.py")
    assert result.spdxfile.licenses_in_file == ["GPL-3.0-or-later"]
    assert result.spdxfile.copyright == "SPDX-FileCopyrightText: 2017 Mary Sue"
    assert not result.bad_licenses
    assert not result.missing_licenses


def test_generate_file_report_file_from_different_cwd(fake_repository):
    """Another simple generate test, but from a different CWD."""
    os.chdir("/")
    project = Project(fake_repository)
    result = FileReport.generate(
        project, fake_repository / "src/source_code.py"
    )
    assert result.spdxfile.licenses_in_file == ["GPL-3.0-or-later"]
    assert result.spdxfile.copyright == "SPDX-FileCopyrightText: 2017 Mary Sue"
    assert not result.bad_licenses
    assert not result.missing_licenses


def test_generate_file_report_file_missing_license(fake_repository):
    """Simple generate test with a missing license."""
    (fake_repository / "foo.py").write_text(
        "SPDX" "-License-Identifier: BSD-3-Clause"
    )
    project = Project(fake_repository)
    result = FileReport.generate(project, "foo.py")

    assert result.spdxfile.copyright == ""
    assert result.missing_licenses == {"BSD-3-Clause"}
    assert not result.bad_licenses


def test_generate_file_report_file_bad_license(fake_repository):
    """Simple generate test with a bad license."""
    (fake_repository / "foo.py").write_text(
        "SPDX" "-License-Identifier: fakelicense"
    )
    project = Project(fake_repository)
    result = FileReport.generate(project, "foo.py")

    assert result.spdxfile.copyright == ""
    assert result.bad_licenses == {"fakelicense"}
    assert result.missing_licenses == {"fakelicense"}


def test_generate_file_report_exception(fake_repository):
    """Simple generate test to test if the exception is detected."""
    project = Project(fake_repository)
    result = FileReport.generate(project, "src/exception.py")
    assert set(result.spdxfile.licenses_in_file) == {
        "GPL-3.0-or-later",
        "Autoconf-exception-3.0",
    }
    assert result.spdxfile.copyright == "SPDX-FileCopyrightText: 2017 Mary Sue"
    assert not result.bad_licenses
    assert not result.missing_licenses


def test_generate_project_report_simple(fake_repository, multiprocessing):
    """Simple generate test, just to see if it sort of works."""
    project = Project(fake_repository)
    result = ProjectReport.generate(project, multiprocessing=multiprocessing)

    assert not result.bad_licenses
    assert not result.licenses_without_extension
    assert not result.missing_licenses
    assert not result.unused_licenses
    assert result.used_licenses
    assert not result.read_errors
    assert result.file_reports


def test_generate_project_report_licenses_without_extension(
    fake_repository, multiprocessing
):
    """Licenses without extension are detected."""
    (fake_repository / "LICENSES/CC0-1.0.txt").rename(
        fake_repository / "LICENSES/CC0-1.0"
    )

    project = Project(fake_repository)
    result = ProjectReport.generate(project, multiprocessing=multiprocessing)

    assert "CC0-1.0" in result.licenses_without_extension


def test_generate_project_report_missing_license(
    fake_repository, multiprocessing
):
    """Missing licenses are detected."""
    (fake_repository / "LICENSES/GPL-3.0-or-later.txt").unlink()

    project = Project(fake_repository)
    result = ProjectReport.generate(project, multiprocessing=multiprocessing)

    assert "GPL-3.0-or-later" in result.missing_licenses
    assert not result.bad_licenses


def test_generate_project_report_bad_license(fake_repository, multiprocessing):
    """Bad licenses are detected."""
    (fake_repository / "LICENSES/bad.txt").write_text("foo")

    project = Project(fake_repository)
    result = ProjectReport.generate(project, multiprocessing=multiprocessing)

    assert result.bad_licenses
    assert not result.missing_licenses


def test_generate_project_report_bad_license_in_file(
    fake_repository, multiprocessing
):
    """Bad licenses in files are detected."""
    (fake_repository / "foo.py").write_text("SPDX" "-License-Identifier: bad")

    project = Project(fake_repository)
    result = ProjectReport.generate(project, multiprocessing=multiprocessing)

    assert "bad" in result.bad_licenses


def test_generate_project_report_bad_license_can_also_be_missing(
    fake_repository, multiprocessing
):
    """Bad licenses can also be missing licenses."""
    (fake_repository / "foo.py").write_text("SPDX" "-License-Identifier: bad")

    project = Project(fake_repository)
    result = ProjectReport.generate(project, multiprocessing=multiprocessing)

    assert "bad" in result.bad_licenses
    assert "bad" in result.missing_licenses


def test_generate_project_report_deprecated_license(
    fake_repository, multiprocessing
):
    """Deprecated licenses are detected."""
    (fake_repository / "LICENSES/GPL-3.0-or-later.txt").rename(
        fake_repository / "LICENSES/GPL-3.0.txt"
    )

    project = Project(fake_repository)
    result = ProjectReport.generate(project, multiprocessing=multiprocessing)

    assert "GPL-3.0" in result.deprecated_licenses


@cpython
@posix
def test_generate_project_report_read_error(fake_repository, multiprocessing):
    """Files that cannot be read are added to the read error list."""
    (fake_repository / "bad").write_text("foo")
    (fake_repository / "bad").chmod(0o000)

    project = Project(fake_repository)
    result = ProjectReport.generate(project, multiprocessing=multiprocessing)

    # pylint: disable=superfluous-parens
    assert (fake_repository / "bad") in result.read_errors


def test_generate_project_report_to_dict(fake_repository, multiprocessing):
    """Extremely simple test for ProjectReport.to_dict."""
    project = Project(fake_repository)
    report = ProjectReport.generate(project, multiprocessing=multiprocessing)
    # TODO: Actually do something
    report.to_dict()


def test_bill_of_materials(fake_repository, multiprocessing):
    """Generate a bill of materials."""
    project = Project(fake_repository)
    report = ProjectReport.generate(project, multiprocessing=multiprocessing)
    # TODO: Actually do something
    report.bill_of_materials()
