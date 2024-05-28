# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2024 Nico Rikken <nico@nicorikken.eu>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""All tests for reuse.lint"""

import re
import shutil

from conftest import cpython, posix

from reuse.lint import format_lines, format_plain
from reuse.project import Project
from reuse.report import ProjectReport

# REUSE-IgnoreStart


def test_lint_simple(fake_repository):
    """Extremely simple test for lint."""
    project = Project.from_directory(fake_repository)
    report = ProjectReport.generate(project)
    result = format_plain(report)
    assert result


def test_lint_git(git_repository):
    """Extremely simple test for lint with a git repository."""
    project = Project.from_directory(git_repository)
    report = ProjectReport.generate(project)
    result = format_plain(report)
    assert result


def test_lint_submodule(submodule_repository):
    """Extremely simple test for lint with an ignored submodule."""
    project = Project.from_directory(submodule_repository)
    (submodule_repository / "submodule/foo.c").write_text("foo")
    report = ProjectReport.generate(project)
    result = format_plain(report)
    assert result


def test_lint_submodule_included(submodule_repository):
    """Extremely simple test for lint with an included submodule."""
    project = Project.from_directory(
        submodule_repository, include_submodules=True
    )
    (submodule_repository / "submodule/foo.c").write_text("foo")
    report = ProjectReport.generate(project)
    result = format_plain(report)
    assert ":-(" in result


def test_lint_empty_directory(empty_directory):
    """An empty directory is compliant."""
    project = Project.from_directory(empty_directory)
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

    project = Project.from_directory(fake_repository)
    report = ProjectReport.generate(project)
    result = format_plain(report)

    assert ":-(" in result
    assert "# DEPRECATED LICENSES" in result
    assert "GPL-3.0" in result
    assert "Fix deprecated licenses:" in result
    assert "spdx.org/licenses/#deprecated" in result


def test_lint_bad_license(fake_repository):
    """A bad license is detected."""
    (fake_repository / "foo.py").write_text(
        "SPDX-License-Identifier: bad-license"
    )
    project = Project.from_directory(fake_repository)
    report = ProjectReport.generate(project)
    result = format_plain(report)

    assert ":-(" in result
    assert "# BAD LICENSES" in result
    assert "foo.py" in result
    assert "bad-license" in result
    assert "Fix bad licenses:" in result
    assert "reuse.software/faq/#custom-license" in result


def test_lint_licenses_without_extension(fake_repository):
    """A license without file extension is detected."""
    (fake_repository / "LICENSES/GPL-3.0-or-later.txt").rename(
        fake_repository / "LICENSES/GPL-3.0-or-later"
    )
    project = Project.from_directory(fake_repository)
    report = ProjectReport.generate(project)
    result = format_plain(report)

    assert ":-(" in result
    assert "# LICENSES WITHOUT FILE EXTENSION" in result
    assert "GPL-3.0-or-later" in result
    assert "Fix licenses without file extension:" in result


def test_lint_missing_licenses(fake_repository):
    """A missing license is detected."""
    (fake_repository / "foo.py").write_text("SPDX-License-Identifier: MIT")
    project = Project.from_directory(fake_repository)
    report = ProjectReport.generate(project)
    result = format_plain(report)

    assert ":-(" in result
    assert "# MISSING LICENSES" in result
    assert "foo.py" in result
    assert "MIT" in result
    assert "Fix missing licenses:" in result


def test_lint_unused_licenses(fake_repository):
    """An unused license is detected."""
    (fake_repository / "LICENSES/MIT.txt").write_text("foo")
    project = Project.from_directory(fake_repository)
    report = ProjectReport.generate(project)
    result = format_plain(report)

    assert ":-(" in result
    assert "# UNUSED LICENSES" in result
    assert "Unused licenses: MIT" in result
    assert "Fix unused licenses:" in result


@cpython
@posix
def test_lint_read_errors(fake_repository):
    """A read error is detected."""
    (fake_repository / "foo.py").write_text("foo")
    (fake_repository / "foo.py").chmod(0o000)
    project = Project.from_directory(fake_repository)
    report = ProjectReport.generate(project)
    result = format_plain(report)

    assert ":-(" in result
    assert "# READ ERRORS" in result
    assert "Could not read:" in result
    assert "foo.py" in result
    assert "Fix read errors:" in result


def test_lint_files_without_copyright_and_licensing(fake_repository):
    """A file without copyright and licensing is detected."""
    (fake_repository / "foo.py").write_text("foo")
    project = Project.from_directory(fake_repository)
    report = ProjectReport.generate(project)
    result = format_plain(report)

    assert ":-(" in result
    assert "# MISSING COPYRIGHT AND LICENSING INFORMATION" in result
    assert (
        "The following files have no copyright and licensing information:"
        in result
    )
    assert "foo.py" in result
    assert "Fix missing copyright/licensing information:" in result
    assert "reuse.software/tutorial" in result


def test_lint_json_output(fake_repository):
    """Test for lint with JSON output."""
    (fake_repository / "foo.py").write_text("SPDX-License-Identifier: MIT")
    project = Project.from_directory(fake_repository)
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
    assert "recommendations" in json_result
    # Test length of resulting list values
    assert len(json_result["files"]) == 9
    assert len(json_result["summary"]) == 5
    assert len(json_result["recommendations"]) == 2
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


def test_lint_lines_output(fake_repository):
    """Complete test for lint with lines output."""
    # Prepare a repository that includes all types of situations:
    # missing_licenses, unused_licenses, bad_licenses, deprecated_licenses,
    # licenses_without_extension, files_without_copyright,
    # files_without_licenses, read_errors
    (fake_repository / "invalid-license.py").write_text(
        "SPDX-License-Identifier: invalid"
    )
    (fake_repository / "no-license.py").write_text(
        "SPDX-FileCopyrightText: Jane Doe"
    )
    (fake_repository / "LICENSES" / "invalid-license-text").write_text(
        "An invalid license text"
    )
    (fake_repository / "LICENSES" / "Nokia-Qt-exception-1.1.txt").write_text(
        "Deprecated"
    )
    (fake_repository / "LICENSES" / "MIT").write_text("foo")
    (fake_repository / "file with spaces.py").write_text("foo")

    project = Project.from_directory(fake_repository)
    report = ProjectReport.generate(project)

    lines_result = format_lines(report)
    lines_result_lines = lines_result.splitlines()

    assert len(lines_result_lines) == 12

    for line in lines_result_lines:
        assert re.match(".+: [^:]+", line)

    assert lines_result.count("invalid-license.py") == 3
    assert lines_result.count("no-license.py") == 1
    assert lines_result.count("LICENSES") == 6
    assert lines_result.count("invalid-license-text") == 3
    assert lines_result.count("Nokia-Qt-exception-1.1.txt") == 2
    assert lines_result.count("MIT") == 2
    assert lines_result.count("file with spaces.py") == 2


@cpython
@posix
def test_lint_lines_read_errors(fake_repository):
    """Check read error output"""
    (fake_repository / "restricted.py").write_text("foo")
    (fake_repository / "restricted.py").chmod(0o000)
    project = Project.from_directory(fake_repository)
    report = ProjectReport.generate(project)
    result = format_lines(report)
    print(result)

    assert len(result.splitlines()) == 1
    assert "restricted.py" in result
    assert "read error" in result


# REUSE-IgnoreEnd
