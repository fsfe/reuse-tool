# SPDX-FileCopyrightText: 2017-2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for reuse.report"""

import os

from reuse.project import Project
from reuse.report import FileReport, ProjectReport


def test_generate_file_report_file_simple(fake_repository):
    """An extremely simple generate test, just to see if the function doesn't
    crash.
    """
    project = Project(fake_repository)
    result = FileReport.generate(project, "src/source_code.py")
    assert result.file_report.spdxfile.licenses_in_file == ["GPL-3.0-or-later"]
    assert (
        result.file_report.spdxfile.copyright
        == "SPDX-FileCopyrightText: 2017 Mary Sue"
    )
    assert not result.bad_licenses
    assert not result.missing_licenses


def test_generate_file_report_file_from_different_cwd(fake_repository):
    """Another simple generate test, but from a different CWD."""
    os.chdir("/")
    project = Project(fake_repository)
    result = FileReport.generate(
        project, fake_repository / "src/source_code.py"
    )
    assert result.file_report.spdxfile.licenses_in_file == ["GPL-3.0-or-later"]
    assert (
        result.file_report.spdxfile.copyright
        == "SPDX-FileCopyrightText: 2017 Mary Sue"
    )
    assert not result.bad_licenses
    assert not result.missing_licenses


def test_generate_file_report_file_missing_license(fake_repository):
    """Simple generate test with a missing license."""
    (fake_repository / "foo.py").write_text(
        "SPDX" "-License-Identifier: BSD-3-Clause"
    )
    project = Project(fake_repository)
    result = FileReport.generate(project, "foo.py")

    assert result.file_report.spdxfile.copyright == ""
    assert result.missing_licenses == {"BSD-3-Clause"}
    assert not result.bad_licenses


def test_generate_file_report_file_bad_license(fake_repository):
    """Simple generate test with a bad license."""
    (fake_repository / "foo.py").write_text(
        "SPDX" "-License-Identifier: fakelicense"
    )
    project = Project(fake_repository)
    result = FileReport.generate(project, "foo.py")

    assert result.file_report.spdxfile.copyright == ""
    assert result.bad_licenses == {"fakelicense"}
    assert not result.missing_licenses


def test_generate_file_report_exception(fake_repository):
    """Simple generate test to test if the exception is detected."""
    project = Project(fake_repository)
    result = FileReport.generate(project, "src/exception.py")
    assert set(result.file_report.spdxfile.licenses_in_file) == {
        "GPL-3.0-or-later",
        "Autoconf-exception-3.0",
    }
    assert (
        result.file_report.spdxfile.copyright
        == "SPDX-FileCopyrightText: 2017 Mary Sue"
    )
    assert not result.bad_licenses
    assert not result.missing_licenses


def test_generate_project_report_simple(fake_repository):
    """Simple generate test, just to see if it sort of works."""
    project = Project(fake_repository)
    result = ProjectReport.generate(project)

    assert not result.missing_licenses
    assert not result.bad_licenses
    assert not result.read_errors
    assert result.file_reports


def test_generate_project_report_missing_license(fake_repository):
    """Missing licenses are detected."""
    (fake_repository / "LICENSES/GPL-3.0-or-later.txt").unlink()

    project = Project(fake_repository)
    result = ProjectReport.generate(project)

    assert "GPL-3.0-or-later" in result.missing_licenses
    assert not result.bad_licenses


def test_generate_project_report_bad_license(fake_repository):
    """Bad licenses are detected."""
    (fake_repository / "LICENSES/bad.txt").touch()

    project = Project(fake_repository)
    result = ProjectReport.generate(project)

    assert result.bad_licenses
    assert not result.missing_licenses


def test_generate_project_report_bad_license_in_file(fake_repository):
    """Bad licenses in files are detected."""
    (fake_repository / "foo.py").write_text("SPDX" "-License-Identifier: bad")

    project = Project(fake_repository)
    result = ProjectReport.generate(project)

    assert "bad" in result.bad_licenses


def test_generate_project_report_read_error(fake_repository):
    """Files that cannot be read are added to the read error list."""
    (fake_repository / "bad").symlink_to("does_not_exist")

    project = Project(fake_repository)
    result = ProjectReport.generate(project)

    # pylint: disable=superfluous-parens
    assert (fake_repository / "bad") in result.read_errors


def test_generate_project_report_to_dict(fake_repository):
    """Extremely simple test for ProjectReport.to_dict."""
    project = Project(fake_repository)
    report = ProjectReport.generate(project)
    # TODO: Actually do something
    report.to_dict()


def test_bill_of_materials(fake_repository):
    """Generate a bill of materials."""
    project = Project(fake_repository)
    report = ProjectReport.generate(project)
    # TODO: Actually do something
    report.bill_of_materials()
