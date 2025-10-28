# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2024 Nico Rikken <nico@nicorikken.eu>
# SPDX-FileCopyrightText: 2024 Sebastien Morais <github@SMoraisAnsys>
# SPDX-FileCopyrightText: 2025 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""All tests for reuse.lint."""

import shutil
from inspect import cleandoc
from pathlib import PurePath

from conftest import cpython, posix

from reuse._util import cleandoc_nl
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
    (fake_repository / "LICENSES/foo.txt").write_text("Hello, world!")
    project = Project.from_directory(fake_repository)
    report = ProjectReport.generate(project)
    result = format_plain(report)

    assert ":-(" in result
    assert "# BAD LICENSES" in result
    assert "foo.txt" in result
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


def test_invalid_spdx_expressions(fake_repository):
    """An invalid expression is detected."""
    (fake_repository / "foo.py").write_text(
        cleandoc(
            """
            Copyright Jane Doe

            SPDX-License-Identifier: MIT OR
            SPDX-License-Identifier: Apache-2.0 AND
            SPDX-License-Identifier: 0BSD
            """
        )
    )
    project = Project.from_directory(fake_repository)
    report = ProjectReport.generate(project)
    result = format_plain(report)

    assert ":-(" in result
    assert "# INVALID SPDX LICENSE EXPRESSIONS" in result
    assert "foo.py' contains invalid SPDX License Expressions:" in result
    assert "Invalid SPDX License Expressions: 2" in result
    assert "Fix invalid SPDX License Expressions:" in result


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
        if test_file["path"] == "foo.py":
            assert test_file["spdx_expressions"][0]["value"] == "MIT"
            assert test_file["spdx_expressions"][0]["source"] == "foo.py"
            assert test_file["spdx_expressions"][0]["is_valid"]
        if test_file["path"] == "doc/usage.md":
            assert test_file["spdx_expressions"][0]["value"] == "CC0-1.0"
            assert test_file["spdx_expressions"][0]["source"] == "doc/usage.md"
            assert test_file["spdx_expressions"][0]["is_valid"]


class TestFormatLines:
    """Tests for format_lines and format_lines_subset."""

    def test_missing_licenses(self, empty_directory, format_lines_func):
        """List missing licenses."""
        (empty_directory / "foo.py").write_text(
            cleandoc(
                """
                Copyright Jane Doe
                SPDX-License-Identifier: MIT OR 0BSD
                """
            )
        )
        project = Project.from_directory(".")
        report = ProjectReport.generate(project)
        result = format_lines_func(report)
        assert result == cleandoc_nl(
            """
            foo.py: missing license '0BSD'
            foo.py: missing license 'MIT'
            """
        )

    @cpython
    @posix
    def test_read_errors(self, fake_repository, format_lines_func):
        """Check read error output"""
        (fake_repository / "restricted.py").write_text("foo")
        (fake_repository / "restricted.py").chmod(0o000)
        project = Project.from_directory(".")
        report = ProjectReport.generate(project)
        result = format_lines_func(report)

        assert result == "restricted.py: read error\n"

    def test_invalid_spdx_expressions(self, empty_directory, format_lines_func):
        """List invalid SPDX License Expressions."""
        (empty_directory / "foo.py").write_text(
            cleandoc(
                """
                Copyright Jane Doe
                SPDX-License-Identifier: MIT OR
                SPDX-License-Identifier: <>
                """
            )
        )
        (empty_directory / "bar.py").write_text(
            cleandoc(
                """
                Copyright John Doe
                SPDX-License-Identifier: MIT OR
                """
            )
        )
        project = Project.from_directory(".")
        report = ProjectReport.generate(project)
        result = format_lines_func(report)

        assert result == cleandoc_nl(
            """
            bar.py: invalid SPDX License Expression 'MIT OR'
            bar.py: no license identifier
            foo.py: invalid SPDX License Expression '<>'
            foo.py: invalid SPDX License Expression 'MIT OR'
            foo.py: no license identifier
            """
        )

    def test_no_copyright_or_licensing(
        self, empty_directory, format_lines_func
    ):
        """List files without copyright or licensing."""
        (empty_directory / "no_lic.py").write_text("Copyright Jane Doe")
        (empty_directory / "no_copy.py").write_text(
            "SPDX-License-Identifier: MIT"
        )
        (empty_directory / "none.py").write_text("Hello, world!")
        project = Project.from_directory(".")
        report = ProjectReport.generate(project)
        result = format_lines_func(report)

        assert result == cleandoc_nl(
            """
            no_copy.py: missing license 'MIT'
            no_copy.py: no copyright notice
            no_lic.py: no license identifier
            none.py: no license identifier
            none.py: no copyright notice
            """
        )

    def test_bad_license(self, empty_directory):
        """List bad licenses."""
        (empty_directory / "LICENSES").mkdir()
        (empty_directory / "LICENSES/bad.txt").write_text("Hello, world!")
        project = Project.from_directory(".")
        report = ProjectReport.generate(project)
        result = format_lines(report)

        path = PurePath("LICENSES/bad.txt")
        assert result == cleandoc_nl(
            f"""
            {path}: bad license 'bad'
            {path}: unused license
            """
        )

    def test_deprecated_license(self, empty_directory):
        """List deprecated licenses."""
        (empty_directory / "LICENSES").mkdir()
        (empty_directory / "LICENSES/GPL-3.0.txt").write_text("Hello, world!")
        project = Project.from_directory(".")
        report = ProjectReport.generate(project)
        result = format_lines(report)

        path = PurePath("LICENSES/GPL-3.0.txt")
        assert result == cleandoc_nl(
            f"""
            {path}: deprecated license
            {path}: unused license
            """
        )

    def test_licenses_without_extension(self, empty_directory):
        """List licenses without extension."""
        (empty_directory / "LICENSES").mkdir()
        (empty_directory / "LICENSES/MIT").write_text("Hello, world!")
        project = Project.from_directory(".")
        report = ProjectReport.generate(project)
        result = format_lines(report)

        path = PurePath("LICENSES/MIT")
        assert result == cleandoc_nl(
            f"""
            {path}: license without file extension
            {path}: unused license
            """
        )


# REUSE-IgnoreEnd
