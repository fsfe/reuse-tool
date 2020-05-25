# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""All tests for reuse.lint"""

# pylint: disable=invalid-name

import shutil
import sys

import pytest

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

try:
    import posix as is_posix
except ImportError:
    is_posix = False

cpython = pytest.mark.skipif(
    sys.implementation.name != "cpython", reason="only CPython supported"
)
posix = pytest.mark.skipif(not is_posix, reason="Windows not supported")


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


def test_lint_submodule(submodule_repository):
    """Extremely simple test for lint with an ignored submodule."""
    project = Project(submodule_repository)
    (submodule_repository / "submodule/foo.c").write_text("foo")
    report = ProjectReport.generate(project)
    result = lint(report)
    assert result


def test_lint_submodule_included(submodule_repository):
    """Extremely simple test for lint with an included submodule."""
    project = Project(submodule_repository, include_submodules=True)
    (submodule_repository / "submodule/foo.c").write_text("foo")
    report = ProjectReport.generate(project)
    result = lint(report)
    assert not result


def test_lint_empty_directory(empty_directory):
    """An empty directory is compliant."""
    project = Project(empty_directory)
    report = ProjectReport.generate(project)
    result = lint(report)
    assert result


def test_lint_deprecated(fake_repository, stringio):
    """If a repo has a deprecated license, detect it."""
    shutil.copy(
        fake_repository / "LICENSES/GPL-3.0-or-later.txt",
        fake_repository / "LICENSES/GPL-3.0.txt",
    )
    (fake_repository / "foo.py").write_text(
        "SPDX"
        "-License-Identifier: GPL-3.0\n"
        "SPDX"
        "-FileCopyrightText: Jane Doe"
    )

    project = Project(fake_repository)
    report = ProjectReport.generate(project)
    result = lint(report, out=stringio)

    assert not result
    assert "GPL-3.0" in stringio.getvalue()


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
    (fake_repository / "LICENSES/MIT.txt").write_text("foo")
    project = Project(fake_repository)
    report = ProjectReport.generate(project)
    lint_summary(report, out=stringio)

    assert "MIT" in stringio.getvalue()


@cpython
@posix
def test_lint_read_errors(fake_repository, stringio):
    """A read error is detected."""
    (fake_repository / "foo.py").write_text("foo")
    (fake_repository / "foo.py").chmod(0o000)
    project = Project(fake_repository)
    report = ProjectReport.generate(project)
    result = lint_read_errors(report, out=stringio)

    assert "foo.py" in str(list(result)[0])
    assert "foo.py" in stringio.getvalue()


def test_lint_files_without_copyright_and_licensing(fake_repository, stringio):
    """A file without copyright and licensing is detected."""
    (fake_repository / "foo.py").write_text("foo")
    project = Project(fake_repository)
    report = ProjectReport.generate(project)
    result = lint_files_without_copyright_and_licensing(report, out=stringio)

    assert "foo.py" in str(list(result)[0])
    assert "foo.py" in stringio.getvalue()
