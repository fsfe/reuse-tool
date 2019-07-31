# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""All tests for reuse.lint"""

from reuse.lint import (
    lint,
    lint_bad_licenses,
    lint_files_without_copyright_and_licensing,
    lint_missing_licenses,
    lint_read_errors,
    lint_summary,
)
from reuse.project import Project
from reuse.report import ProjectReport


def test_lint_simple(fake_repository):
    """Extremely simple test for lint."""
    project = Project(fake_repository)
    report = ProjectReport.generate(project)
    result = lint(report)
    assert result


def test_lint_git(git_repository):
    """Extremely simple test for lint with a git repository."""
    project = Project(git_repository)
    report = ProjectReport.generate(project)
    result = lint(report)
    assert result


def test_lint_empty_directory(empty_directory):
    """An empty directory is compliant."""
    project = Project(empty_directory)
    report = ProjectReport.generate(project)
    result = lint(report)
    assert result


def test_lint_bad_license(fake_repository, stringio):
    """A bad license is detected."""
    (fake_repository / "foo.py").write_text(
        "SPDX" "-License-Identifier: bad-license"
    )
    project = Project(fake_repository)
    report = ProjectReport.generate(project)
    result = lint_bad_licenses(report, out=stringio)

    assert "foo.py" in str(list(result)[0])
    assert "foo.py" in stringio.getvalue()
    assert "bad-license" in stringio.getvalue()


def test_lint_missing_licenses(fake_repository, stringio):
    """A missing license is detected."""
    (fake_repository / "foo.py").write_text("SPDX" "-License-Identifier: MIT")
    project = Project(fake_repository)
    report = ProjectReport.generate(project)
    result = lint_missing_licenses(report, out=stringio)

    assert "foo.py" in str(list(result)[0])
    assert "foo.py" in stringio.getvalue()
    assert "MIT" in stringio.getvalue()


def test_lint_unused_licenses(fake_repository, stringio):
    """An unused license is detected."""
    (fake_repository / "LICENSES/MIT.txt").touch()
    project = Project(fake_repository)
    report = ProjectReport.generate(project)
    lint_summary(report, out=stringio)

    assert "MIT" in stringio.getvalue()


def test_lint_read_errors(fake_repository, stringio):
    """A read error is detected."""
    (fake_repository / "foo.py").symlink_to("does_not_exist")
    project = Project(fake_repository)
    report = ProjectReport.generate(project)
    result = lint_read_errors(report, out=stringio)

    assert "foo.py" in str(list(result)[0])
    assert "foo.py" in stringio.getvalue()


def test_lint_files_without_copyright_and_licensing(fake_repository, stringio):
    """A file without copyright and licensing is detected."""
    (fake_repository / "foo.py").touch()
    project = Project(fake_repository)
    report = ProjectReport.generate(project)
    result = lint_files_without_copyright_and_licensing(report, out=stringio)

    assert "foo.py" in str(list(result)[0])
    assert "foo.py" in stringio.getvalue()
