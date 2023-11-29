# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2023 Carmen Bianca BAKKER <carmenbianca@fsfe.org>
# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for reuse.project."""

import os
import shutil
import warnings
from importlib import import_module
from inspect import cleandoc
from pathlib import Path
from textwrap import dedent

import pytest
from debian.copyright import Error as DebianError
from license_expression import LicenseSymbol

from reuse import SourceType
from reuse.project import Project

try:
    IS_POSIX = bool(import_module("posix"))
except ImportError:
    IS_POSIX = False

posix = pytest.mark.skipif(not IS_POSIX, reason="Windows not supported")

TESTS_DIRECTORY = Path(__file__).parent.resolve()
RESOURCES_DIRECTORY = TESTS_DIRECTORY / "resources"


# REUSE-IgnoreStart


def test_project_not_a_directory(empty_directory):
    """Cannot create a Project without a valid directory."""
    (empty_directory / "foo.py").write_text("foo")
    with pytest.raises(NotADirectoryError):
        Project.from_directory(empty_directory / "foo.py")


def test_project_not_exists(empty_directory):
    """Cannot create a Project with a directory that doesn't exist."""
    with pytest.raises(FileNotFoundError):
        Project.from_directory(empty_directory / "foo")


def test_all_files(empty_directory):
    """Given a directory with some files, yield all files."""
    (empty_directory / "foo").write_text("foo")
    (empty_directory / "bar").write_text("foo")

    project = Project.from_directory(empty_directory)
    assert {file_.name for file_ in project.all_files()} == {"foo", "bar"}


def test_all_files_ignore_dot_license(empty_directory):
    """When file and file.license are present, only yield file."""
    (empty_directory / "foo").write_text("foo")
    (empty_directory / "foo.license").write_text("foo")

    project = Project.from_directory(empty_directory)
    assert {file_.name for file_ in project.all_files()} == {"foo"}


def test_all_files_ignore_cal_license(empty_directory):
    """CAL licenses contain SPDX tags referencing themselves. They should be
    skipped.
    """
    (empty_directory / "CAL-1.0").write_text("foo")
    (empty_directory / "CAL-1.0.txt").write_text("foo")
    (empty_directory / "CAL-1.0-Combined-Work-Exception").write_text("foo")
    (empty_directory / "CAL-1.0-Combined-Work-Exception.txt").write_text("foo")

    project = Project.from_directory(empty_directory)
    assert not list(project.all_files())


def test_all_files_ignore_shl_license(empty_directory):
    """SHL-2.1 contains an SPDX tag referencing itself. It should be skipped."""
    (empty_directory / "SHL-2.1").write_text("foo")
    (empty_directory / "SHL-2.1.txt").write_text("foo")

    project = Project.from_directory(empty_directory)
    assert not list(project.all_files())


def test_all_files_ignore_git(empty_directory):
    """When the git directory is present, ignore it."""
    (empty_directory / ".git").mkdir()
    (empty_directory / ".git/config").write_text("foo")

    project = Project.from_directory(empty_directory)
    assert not list(project.all_files())


def test_all_files_ignore_hg(empty_directory):
    """When the hg directory is present, ignore it."""
    (empty_directory / ".hg").mkdir()
    (empty_directory / ".hg/config").touch()

    project = Project.from_directory(empty_directory)
    assert not list(project.all_files())


@posix
def test_all_files_symlinks(empty_directory):
    """All symlinks must be ignored."""
    (empty_directory / "blob").write_text("foo")
    (empty_directory / "blob.license").write_text(
        cleandoc(
            """
            SPDX-FileCopyrightText: Jane Doe

            SPDX-License-Identifier: GPL-3.0-or-later
            """
        )
    )
    (empty_directory / "symlink").symlink_to("blob")
    project = Project.from_directory(empty_directory)
    assert Path("symlink").absolute() not in project.all_files()


def test_all_files_ignore_zero_sized(empty_directory):
    """Empty files should be skipped."""
    (empty_directory / "foo").touch()

    project = Project.from_directory(empty_directory)
    assert Path("foo").absolute() not in project.all_files()


def test_all_files_git_ignored(git_repository):
    """Given a Git repository where some files are ignored, do not yield those
    files.
    """
    project = Project.from_directory(git_repository)
    assert Path("build/hello.py").absolute() not in project.all_files()


def test_all_files_git_ignored_different_cwd(git_repository):
    """Given a Git repository where some files are ignored, do not yield those
    files.

    Be in a different CWD during the above.
    """
    os.chdir(git_repository / "LICENSES")
    project = Project.from_directory(git_repository)
    assert Path("build/hello.py").absolute() not in project.all_files()


def test_all_files_git_ignored_contains_space(git_repository):
    """Files that contain spaces are also ignored."""
    (git_repository / "I contain spaces.pyc").write_text("foo")
    project = Project.from_directory(git_repository)
    assert Path("I contain spaces.pyc").absolute() not in project.all_files()


@posix
def test_all_files_git_ignored_contains_newline(git_repository):
    """Files that contain newlines are also ignored."""
    (git_repository / "hello\nworld.pyc").write_text("foo")
    project = Project.from_directory(git_repository)
    assert Path("hello\nworld.pyc").absolute() not in project.all_files()


def test_all_files_submodule_is_ignored(submodule_repository):
    """If a submodule is ignored, all_files should not raise an Exception."""
    (submodule_repository / "submodule/foo.py").write_text("foo")
    gitignore = submodule_repository / ".gitignore"
    contents = gitignore.read_text()
    contents += "\nsubmodule/\n"
    gitignore.write_text(contents)
    project = Project.from_directory(submodule_repository)
    assert Path("submodule/foo.py").absolute() not in project.all_files()


def test_all_files_hg_ignored(hg_repository):
    """Given a mercurial repository where some files are ignored, do not yield
    those files.
    """
    project = Project.from_directory(hg_repository)
    assert Path("build/hello.py").absolute() not in project.all_files()


def test_all_files_hg_ignored_different_cwd(hg_repository):
    """Given a mercurial repository where some files are ignored, do not yield
    those files.

    Be in a different CWD during the above.
    """
    os.chdir(hg_repository / "LICENSES")
    project = Project.from_directory(hg_repository)
    assert Path("build/hello.py").absolute() not in project.all_files()


def test_all_files_hg_ignored_contains_space(hg_repository):
    """File names that contain spaces are also ignored."""
    (hg_repository / "I contain spaces.pyc").touch()
    project = Project.from_directory(hg_repository)
    assert Path("I contain spaces.pyc").absolute() not in project.all_files()


@posix
def test_all_files_hg_ignored_contains_newline(hg_repository):
    """File names that contain newlines are also ignored."""
    (hg_repository / "hello\nworld.pyc").touch()
    project = Project.from_directory(hg_repository)
    assert Path("hello\nworld.pyc").absolute() not in project.all_files()


def test_all_files_pijul_ignored(pijul_repository):
    """Given a pijul repository where some files are ignored, do not yield
    those files.
    """
    project = Project.from_directory(pijul_repository)
    assert Path("build/hello.py").absolute() not in project.all_files()


def test_all_files_pijul_ignored_different_cwd(pijul_repository):
    """Given a pijul repository where some files are ignored, do not yield
    those files.

    Be in a different CWD during the above.
    """
    os.chdir(pijul_repository / "LICENSES")
    project = Project.from_directory(pijul_repository)
    assert Path("build/hello.py").absolute() not in project.all_files()


def test_all_files_pijul_ignored_contains_space(pijul_repository):
    """File names that contain spaces are also ignored."""
    (pijul_repository / "I contain spaces.pyc").touch()
    project = Project.from_directory(pijul_repository)
    assert Path("I contain spaces.pyc").absolute() not in project.all_files()


@posix
def test_all_files_pijul_ignored_contains_newline(pijul_repository):
    """File names that contain newlines are also ignored."""
    (pijul_repository / "hello\nworld.pyc").touch()
    project = Project.from_directory(pijul_repository)
    assert Path("hello\nworld.pyc").absolute() not in project.all_files()


def test_reuse_info_of_file_does_not_exist(fake_repository):
    """Raise FileNotFoundError when asking for the REUSE info of a file that
    does not exist.
    """
    project = Project.from_directory(fake_repository)
    with pytest.raises(FileNotFoundError):
        project.reuse_info_of(fake_repository / "does_not_exist")


def test_reuse_info_of_directory(empty_directory):
    """Raise IsADirectoryError when calling reuse_info_of on a directory."""
    (empty_directory / "src").mkdir()

    project = Project.from_directory(empty_directory)
    with pytest.raises((IsADirectoryError, PermissionError)):
        project.reuse_info_of(empty_directory / "src")


def test_reuse_info_of_unlicensed_file(fake_repository):
    """Return an empty set when asking for the REUSE information of a file that
    has no REUSE information.

    """
    (fake_repository / "foo.py").write_text("foo")
    project = Project.from_directory(fake_repository)
    assert not bool(project.reuse_info_of("foo.py"))


def test_reuse_info_of_only_copyright(fake_repository):
    """A file contains only a copyright line. Test whether it correctly picks
    up on that.
    """
    (fake_repository / "foo.py").write_text(
        "SPDX-FileCopyrightText: 2017 Jane Doe"
    )
    project = Project.from_directory(fake_repository)
    reuse_info = project.reuse_info_of("foo.py")[0]
    assert not any(reuse_info.spdx_expressions)
    assert len(reuse_info.copyright_lines) == 1
    assert (
        reuse_info.copyright_lines.pop()
        == "SPDX-FileCopyrightText: 2017 Jane Doe"
    )
    assert reuse_info.source_type == SourceType.FILE_HEADER
    assert reuse_info.source_path == "foo.py"
    assert reuse_info.path == "foo.py"


def test_reuse_info_of_also_covered_by_dep5(fake_repository):
    """A file contains all REUSE information, but .reuse/dep5 also
    provides information on this file. Aggregate the information (for now), and
    expect a PendingDeprecationWarning.
    """
    (fake_repository / "doc/foo.py").write_text(
        dedent(
            """
            SPDX-License-Identifier: MIT
            SPDX-FileCopyrightText: in file"""
        )
    )
    project = Project.from_directory(fake_repository)
    with warnings.catch_warnings(record=True) as caught_warnings:
        reuse_infos = project.reuse_info_of("doc/foo.py")
        assert len(reuse_infos) == 2
        assert reuse_infos[0].source_type != reuse_infos[1].source_type
        for reuse_info in reuse_infos:
            if reuse_info.source_type == SourceType.DEP5:
                assert LicenseSymbol("CC0-1.0") in reuse_info.spdx_expressions
                assert "2017 Jane Doe" in reuse_info.copyright_lines
                assert reuse_info.path == "doc/foo.py"
                assert reuse_info.source_path == ".reuse/dep5"
            elif reuse_info.source_type == SourceType.FILE_HEADER:
                assert LicenseSymbol("MIT") in reuse_info.spdx_expressions
                assert (
                    "SPDX-FileCopyrightText: in file"
                    in reuse_info.copyright_lines
                )
                assert reuse_info.path == "doc/foo.py"
                assert reuse_info.source_path == "doc/foo.py"

        assert len(caught_warnings) == 1
        assert issubclass(
            caught_warnings[0].category, PendingDeprecationWarning
        )


def test_reuse_info_of_no_duplicates(empty_directory):
    """A file contains the same lines twice. The ReuseInfo only contains those
    lines once.
    """
    spdx_line = "SPDX-License-Identifier: GPL-3.0-or-later\n"
    copyright_line = (
        "SPDX-FileCopyrightText: 2017 Free Software Foundation Europe\n"
    )
    text = spdx_line + copyright_line

    (empty_directory / "foo.py").write_text(text * 2)
    project = Project.from_directory(empty_directory)
    reuse_info = project.reuse_info_of("foo.py")[0]
    assert len(reuse_info.spdx_expressions) == 1
    assert LicenseSymbol("GPL-3.0-or-later") in reuse_info.spdx_expressions
    assert len(reuse_info.copyright_lines) == 1
    assert (
        "SPDX-FileCopyrightText: 2017 Free Software Foundation Europe"
        in reuse_info.copyright_lines
    )


def test_reuse_info_of_binary_succeeds(fake_repository):
    """reuse_info_of succeeds when the target is covered by dep5."""
    shutil.copy(
        RESOURCES_DIRECTORY / "fsfe.png", fake_repository / "doc/fsfe.png"
    )

    project = Project.from_directory(fake_repository)
    reuse_info = project.reuse_info_of("doc/fsfe.png")[0]
    assert LicenseSymbol("CC0-1.0") in reuse_info.spdx_expressions
    assert reuse_info.source_type == SourceType.DEP5
    assert reuse_info.path == "doc/fsfe.png"


def test_license_file_detected(empty_directory):
    """Test whether---when given a file and a license file---the license file
    is detected and read.
    """
    (empty_directory / "foo.py").write_text("foo")
    (empty_directory / "foo.py.license").write_text(
        "SPDX-FileCopyrightText: 2017 Jane Doe\nSPDX-License-Identifier: MIT\n"
    )

    project = Project.from_directory(empty_directory)
    reuse_info = project.reuse_info_of("foo.py")[0]

    assert "SPDX-FileCopyrightText: 2017 Jane Doe" in reuse_info.copyright_lines
    assert LicenseSymbol("MIT") in reuse_info.spdx_expressions
    assert reuse_info.source_type == SourceType.DOT_LICENSE
    assert reuse_info.path == "foo.py"
    assert reuse_info.source_path == "foo.py.license"


def test_licenses_filename(empty_directory):
    """Detect the license identifier of a license from its stem."""
    (empty_directory / "LICENSES").mkdir()
    (empty_directory / "LICENSES/foo.txt").write_text("foo")
    project = Project.from_directory(empty_directory)
    assert "foo" in project.licenses


def test_licenses_no_extension(empty_directory):
    """Detect the license identifier of a license from its full name if it is
    in the license list.
    """
    (empty_directory / "LICENSES").mkdir()
    (empty_directory / "LICENSES/GPL-3.0-or-later").write_text("foo")
    (empty_directory / "LICENSES/MIT-3.0-or-later").write_text("foo")
    project = Project.from_directory(empty_directory)
    assert "GPL-3.0-or-later" in project.licenses
    assert "MIT-3" in project.licenses


def test_licenses_subdirectory(empty_directory):
    """Find a license in a subdirectory of LICENSES/."""
    (empty_directory / "LICENSES/sub").mkdir(parents=True)
    (empty_directory / "LICENSES/sub/MIT.txt").write_text("foo")
    project = Project.from_directory(empty_directory)
    assert "MIT" in project.licenses


def test_relative_from_root(empty_directory):
    """A simple test. Given /path/to/root/src/hello.py, return src/hello.py."""
    project = Project.from_directory(empty_directory)
    assert project.relative_from_root(project.root / "src/hello.py") == Path(
        "src/hello.py"
    )


def test_relative_from_root_no_shared_base_path(empty_directory):
    """A path can still be relative from root if the paths do not have a common
    prefix.

    For instance, if root is /path/to/root and given root/src/hello.py from the
    directory /path/to, return src/hello.py. This is a bit involved, but works
    out.
    """
    project = Project.from_directory(empty_directory)
    parent = empty_directory.parent
    os.chdir(parent)
    assert project.relative_from_root(
        Path(f"{project.root.name}/src/hello.py")
    ) == Path("src/hello.py")


def test_duplicate_field_dep5(empty_directory):
    """When a duplicate field is in a dep5 file, correctly handle errors."""
    dep5_text = cleandoc(
        """
        Format: https://example.com/format/1.0
        Upstream-Name: Some project
        Upstream-Contact: Jane Doe
        Source: https://example.com/

        Files: foo.py
        Copyright: 2017 Jane Doe
        Copyright: 2017 John Doe
        License: GPL-3.0-or-later
        """
    )
    (empty_directory / ".reuse").mkdir()
    (empty_directory / ".reuse/dep5").write_text(dep5_text)

    with pytest.raises(DebianError):
        Project.from_directory(empty_directory)


# REUSE-IgnoreEnd
