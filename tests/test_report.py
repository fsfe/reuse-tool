# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2022 Pietro Albini <pietro.albini@ferrous-systems.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for reuse.report"""


import os
import sys
from importlib import import_module
from textwrap import dedent

import pytest

from reuse import SourceType
from reuse.project import Project
from reuse.report import FileReport, ProjectReport

try:
    IS_POSIX = bool(import_module("posix"))
except ImportError:
    IS_POSIX = False

cpython = pytest.mark.skipif(
    sys.implementation.name != "cpython", reason="only CPython supported"
)
posix = pytest.mark.skipif(not IS_POSIX, reason="Windows not supported")


# REUSE-IgnoreStart


def test_generate_file_report_file_simple(
    fake_repository, add_license_concluded
):
    """An extremely simple generate test, just to see if the function doesn't
    crash.
    """
    project = Project(fake_repository)
    result = FileReport.generate(
        project,
        "src/source_code.py",
        add_license_concluded=add_license_concluded,
    )

    assert result.licenses_in_file == ["GPL-3.0-or-later"]
    assert (
        result.license_concluded == "GPL-3.0-or-later"
        if add_license_concluded
        else "NOASSERTION"
    )
    assert result.copyright == "SPDX-FileCopyrightText: 2017 Jane Doe"
    assert not result.bad_licenses
    assert not result.missing_licenses


def test_generate_file_report_file_from_different_cwd(
    fake_repository, add_license_concluded
):
    """Another simple generate test, but from a different CWD."""
    os.chdir("/")
    project = Project(fake_repository)
    result = FileReport.generate(
        project,
        fake_repository / "src/source_code.py",
        add_license_concluded=add_license_concluded,
    )
    assert result.licenses_in_file == ["GPL-3.0-or-later"]
    assert (
        result.license_concluded == "GPL-3.0-or-later"
        if add_license_concluded
        else "NOASSERTION"
    )
    assert result.copyright == "SPDX-FileCopyrightText: 2017 Jane Doe"
    assert not result.bad_licenses
    assert not result.missing_licenses


def test_generate_file_report_file_missing_license(
    fake_repository, add_license_concluded
):
    """Simple generate test with a missing license."""
    (fake_repository / "foo.py").write_text(
        "SPDX-License-Identifier: BSD-3-Clause"
    )
    project = Project(fake_repository)
    result = FileReport.generate(
        project, "foo.py", add_license_concluded=add_license_concluded
    )

    assert result.copyright == ""
    assert result.licenses_in_file == ["BSD-3-Clause"]
    assert (
        result.license_concluded == "BSD-3-Clause"
        if add_license_concluded
        else "NOASSERTION"
    )
    assert result.missing_licenses == {"BSD-3-Clause"}
    assert not result.bad_licenses


def test_generate_file_report_file_bad_license(
    fake_repository, add_license_concluded
):
    """Simple generate test with a bad license."""
    (fake_repository / "foo.py").write_text(
        "SPDX-License-Identifier: fakelicense"
    )
    project = Project(fake_repository)
    result = FileReport.generate(
        project, "foo.py", add_license_concluded=add_license_concluded
    )

    assert result.copyright == ""
    assert result.licenses_in_file == ["fakelicense"]
    assert (
        result.license_concluded == "fakelicense"
        if add_license_concluded
        else "NOASSERTION"
    )
    assert result.bad_licenses == {"fakelicense"}
    assert result.missing_licenses == {"fakelicense"}


def test_generate_file_report_license_contains_plus(
    fake_repository, add_license_concluded
):
    """Given a license expression akin to Apache-1.0+, LICENSES/Apache-1.0.txt
    should be an appropriate license file.
    """
    (fake_repository / "foo.py").write_text(
        "SPDX-License-Identifier: Apache-1.0+"
    )
    (fake_repository / "LICENSES/Apache-1.0.txt").touch()
    project = Project(fake_repository)
    result = FileReport.generate(
        project, "foo.py", add_license_concluded=add_license_concluded
    )

    assert result.copyright == ""
    assert result.licenses_in_file == ["Apache-1.0+"]
    assert (
        result.license_concluded == "Apache-1.0+"
        if add_license_concluded
        else "NOASSERTION"
    )
    assert not result.bad_licenses
    assert not result.missing_licenses


def test_generate_file_report_exception(fake_repository, add_license_concluded):
    """Simple generate test to test if the exception is detected."""
    project = Project(fake_repository)
    result = FileReport.generate(
        project, "src/exception.py", add_license_concluded=add_license_concluded
    )

    assert set(result.licenses_in_file) == {
        "GPL-3.0-or-later",
        "Autoconf-exception-3.0",
    }
    assert (
        result.license_concluded
        == "GPL-3.0-or-later WITH Autoconf-exception-3.0"
        if add_license_concluded
        else "NOASSERTION"
    )
    assert result.copyright == "SPDX-FileCopyrightText: 2017 Jane Doe"
    assert not result.bad_licenses
    assert not result.missing_licenses


def test_generate_file_report_no_licenses(
    fake_repository, add_license_concluded
):
    """Test behavior when no license information is present in the file"""
    (fake_repository / "foo.py").write_text("")
    project = Project(fake_repository)
    result = FileReport.generate(
        project, "foo.py", add_license_concluded=add_license_concluded
    )

    assert result.copyright == ""
    assert not result.licenses_in_file
    assert (
        result.license_concluded == "NONE"
        if add_license_concluded
        else "NOASSERTION"
    )
    assert not result.bad_licenses
    assert not result.missing_licenses


def test_generate_file_report_multiple_licenses(
    fake_repository, add_license_concluded
):
    """Test that all licenses are included in LicenseConcluded"""
    project = Project(fake_repository)
    result = FileReport.generate(
        project,
        "src/multiple_licenses.rs",
        add_license_concluded=add_license_concluded,
    )

    assert result.copyright == "SPDX-FileCopyrightText: 2022 Jane Doe"
    assert set(result.licenses_in_file) == {
        "GPL-3.0-or-later",
        "Apache-2.0",
        "CC0-1.0",
        "Autoconf-exception-3.0",
    }
    assert (
        result.license_concluded
        == "GPL-3.0-or-later AND (Apache-2.0 OR CC0-1.0"
        " WITH Autoconf-exception-3.0)"
        if add_license_concluded
        else "NOASSERTION"
    )
    assert not result.bad_licenses
    assert not result.missing_licenses


def test_generate_file_report_to_dict_lint_source_information(fake_repository):
    """When a file is covered both by DEP5 and its file header, the lint dict
    should correctly convey the source information.
    """
    (fake_repository / "doc/foo.py").write_text(
        dedent(
            """
            SPDX-License-Identifier: MIT OR 0BSD
            SPDX-FileCopyrightText: in file"""
        )
    )
    project = Project(fake_repository)
    report = FileReport.generate(
        project,
        "doc/foo.py",
    )
    result = report.to_dict_lint()
    assert result["path"] == "doc/foo.py"
    assert len(result["copyrights"]) == 2
    assert (
        result["copyrights"][0]["source_type"]
        != result["copyrights"][1]["source_type"]
    )
    for copyright_ in result["copyrights"]:
        if copyright_["source_type"] == SourceType.DEP5.value:
            assert copyright_["source"] == ".reuse/dep5"
            assert copyright_["value"] == "2017 Jane Doe"
        elif copyright_["source_type"] == SourceType.FILE_HEADER.value:
            assert copyright_["source"] == "doc/foo.py"
            assert copyright_["value"] == "SPDX-FileCopyrightText: in file"

    assert len(result["spdx_expressions"]) == 2
    assert (
        result["spdx_expressions"][0]["source_type"]
        != result["spdx_expressions"][1]["source_type"]
    )
    for expression in result["spdx_expressions"]:
        if expression["source_type"] == SourceType.DEP5.value:
            assert expression["source"] == ".reuse/dep5"
            assert expression["value"] == "CC0-1.0"
        elif expression["source_type"] == SourceType.FILE_HEADER.value:
            assert expression["source"] == "doc/foo.py"
            assert expression["value"] == "MIT OR 0BSD"


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


def test_generate_project_report_unused_license(
    fake_repository, multiprocessing
):
    """Unused licenses are detected."""
    (fake_repository / "LICENSES/MIT.txt").write_text("foo")

    project = Project(fake_repository)
    result = ProjectReport.generate(project, multiprocessing=multiprocessing)

    assert result.unused_licenses == {"MIT"}


def test_generate_project_report_unused_license_plus(
    fake_repository, multiprocessing
):
    """Apache-1.0+ is not an unused license if LICENSES/Apache-1.0.txt
    exists.

    Furthermore, Apache-1.0+ is separately identified as a used license.
    """
    (fake_repository / "foo.py").write_text(
        "SPDX-License-Identifier: Apache-1.0+"
    )
    (fake_repository / "bar.py").write_text(
        "SPDX-License-Identifier: Apache-1.0"
    )
    (fake_repository / "LICENSES/Apache-1.0.txt").touch()

    project = Project(fake_repository)
    result = ProjectReport.generate(project, multiprocessing=multiprocessing)

    assert not result.unused_licenses
    assert {"Apache-1.0", "Apache-1.0+"}.issubset(result.used_licenses)


def test_generate_project_report_unused_license_plus_only_plus(
    fake_repository, multiprocessing
):
    """If Apache-1.0+ is the only declared license in the project,
    LICENSES/Apache-1.0.txt should not be an unused license.
    """
    (fake_repository / "foo.py").write_text(
        "SPDX-License-Identifier: Apache-1.0+"
    )
    (fake_repository / "LICENSES/Apache-1.0.txt").touch()

    project = Project(fake_repository)
    result = ProjectReport.generate(project, multiprocessing=multiprocessing)

    assert not result.unused_licenses
    assert "Apache-1.0+" in result.used_licenses
    assert "Apache-1.0" not in result.used_licenses


def test_generate_project_report_bad_license_in_file(
    fake_repository, multiprocessing
):
    """Bad licenses in files are detected."""
    (fake_repository / "foo.py").write_text("SPDX-License-Identifier: bad")

    project = Project(fake_repository)
    result = ProjectReport.generate(project, multiprocessing=multiprocessing)

    assert "bad" in result.bad_licenses


def test_generate_project_report_bad_license_can_also_be_missing(
    fake_repository, multiprocessing
):
    """Bad licenses can also be missing licenses."""
    (fake_repository / "foo.py").write_text("SPDX-License-Identifier: bad")

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


def test_generate_project_report_to_dict_lint(fake_repository, multiprocessing):
    """Generate dictionary output and verify correct ordering."""
    project = Project(fake_repository)
    report = ProjectReport.generate(project, multiprocessing=multiprocessing)
    result = report.to_dict_lint()

    # Check if the top three keys are at the beginning of the dictionary
    assert list(result.keys())[:3] == [
        "lint_version",
        "reuse_spec_version",
        "reuse_tool_version",
    ]

    # Check if the rest of the keys are sorted alphabetically
    assert list(result.keys())[3:] == sorted(list(result.keys())[3:])


def test_bill_of_materials(fake_repository, multiprocessing):
    """Generate a bill of materials."""
    project = Project(fake_repository)
    report = ProjectReport.generate(project, multiprocessing=multiprocessing)
    # TODO: Actually do something
    report.bill_of_materials()


# REUSE-IgnoreEnd
