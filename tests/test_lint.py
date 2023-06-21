# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""All tests for reuse.lint"""

import shutil
import sys
from importlib import import_module

import pytest

from reuse.lint import format_plain
from reuse.project import Project
from reuse.report import ProjectReport

try:
    IS_POSIX = bool(import_module("posix"))
except ImportError:
    IS_POSIX = False

cpython = pytest.mark.skipif(
    sys.implementation.name != "cpython", reason="only CPython supported"
)
posix = pytest.mark.skipif(not IS_POSIX, reason="Windows not supported")


# REUSE-IgnoreStart


def test_lint_simple(fake_repository):
    """Extremely simple test for lint."""
    project = Project(fake_repository)
    report = ProjectReport.generate(project)
    result = format_plain(report)
    assert result


def test_lint_git(git_repository):
    """Extremely simple test for lint with a git repository."""
    project = Project(git_repository)
    report = ProjectReport.generate(project)
    result = format_plain(report)
    assert result


def test_lint_submodule(submodule_repository):
    """Extremely simple test for lint with an ignored submodule."""
    project = Project(submodule_repository)
    (submodule_repository / "submodule/foo.c").write_text("foo")
    report = ProjectReport.generate(project)
    result = format_plain(report)
    assert result


def test_lint_submodule_included(submodule_repository):
    """Extremely simple test for lint with an included submodule."""
    project = Project(submodule_repository, include_submodules=True)
    (submodule_repository / "submodule/foo.c").write_text("foo")
    report = ProjectReport.generate(project)
    result = format_plain(report)
    assert ":-(" in result


def test_lint_empty_directory(empty_directory):
    """An empty directory is compliant."""
    project = Project(empty_directory)
    report = ProjectReport.generate(project)
    result = format_plain(report)
    assert result


def test_lint_deprecated(fake_repository):
    """If a repo has a deprecated license, detect it."""
    shutil.copy(
        fake_repository / "LICENSES/GPL-3.0-or-later.txt",
        fake_repository / "LICENSES/GPL-3.0.txt",
    )
    (fake_repository / "foo.py").write_text(
        "SPDX-License-Identifier: GPL-3.0\nSPDX-FileCopyrightText: Jane Doe"
    )

    project = Project(fake_repository)
    report = ProjectReport.generate(project)
    result = format_plain(report)

    assert ":-(" in result
    assert "GPL-3.0" in result


def test_lint_bad_license(fake_repository):
    """A bad license is detected."""
    (fake_repository / "foo.py").write_text(
        "SPDX-License-Identifier: bad-license"
    )
    project = Project(fake_repository)
    report = ProjectReport.generate(project)
    result = format_plain(report)

    assert ":-(" in result
    assert "foo.py" in result
    assert "bad-license" in result


def test_lint_missing_licenses(fake_repository):
    """A missing license is detected."""
    (fake_repository / "foo.py").write_text("SPDX-License-Identifier: MIT")
    project = Project(fake_repository)
    report = ProjectReport.generate(project)
    result = format_plain(report)

    assert ":-(" in result
    assert "foo.py" in result
    assert "MIT" in result


def test_lint_unused_licenses(fake_repository):
    """An unused license is detected."""
    (fake_repository / "LICENSES/MIT.txt").write_text("foo")
    project = Project(fake_repository)
    report = ProjectReport.generate(project)
    result = format_plain(report)

    assert ":-(" in result
    assert "Unused licenses: MIT" in result


@cpython
@posix
def test_lint_read_errors(fake_repository):
    """A read error is detected."""
    (fake_repository / "foo.py").write_text("foo")
    (fake_repository / "foo.py").chmod(0o000)
    project = Project(fake_repository)
    report = ProjectReport.generate(project)
    result = format_plain(report)

    assert ":-(" in result
    assert "Could not read:" in result
    assert "foo.py" in result


def test_lint_files_without_copyright_and_licensing(fake_repository):
    """A file without copyright and licensing is detected."""
    (fake_repository / "foo.py").write_text("foo")
    project = Project(fake_repository)
    report = ProjectReport.generate(project)
    result = format_plain(report)

    assert ":-(" in result
    assert (
        "The following files have no copyright and licensing information:"
        in result
    )
    assert "foo.py" in result


def test_lint_json_output(fake_repository):
    """Test for lint with JSON output."""
    (fake_repository / "foo.py").write_text("SPDX-License-Identifier: MIT")
    project = Project(fake_repository)
    report = ProjectReport.generate(project)

    json_result = report.to_dict_lint()

    assert json_result
    # Test if all the keys are present
    assert "lint_version" in json_result
    assert "reuse_spec_version" in json_result
    assert "reuse_tool_version" in json_result
    assert "non_compliant" in json_result
    assert "files" in json_result
    assert "summary" in json_result
    # Test length of resulting list values
    assert len(json_result["files"]) == 9
    assert len(json_result["summary"]) == 5
    # Test result
    assert json_result["summary"]["compliant"] is False
    # Test license path
    for test_file in json_result["files"]:
        if test_file["path"] == str(fake_repository / "foo.py"):
            assert test_file["licenses"][0]["value"] == "MIT"
            assert test_file["licenses"][0]["source"] == str(
                fake_repository / "foo.py"
            )
        if test_file["path"].startswith(str(fake_repository / "doc")):
            assert test_file["licenses"][0]["value"] == "CC0-1.0"
            assert test_file["licenses"][0]["source"] == str(
                fake_repository / ".reuse/dep5"
            )


# REUSE-IgnoreEnd
