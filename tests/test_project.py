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
from inspect import cleandoc
from pathlib import Path

import pytest
from conftest import RESOURCES_DIRECTORY, posix
from license_expression import LicenseSymbol

from reuse import ReuseInfo, SourceType
from reuse._util import _LICENSING
from reuse.global_licensing import (
    GlobalLicensingParseError,
    NestedReuseTOML,
    ReuseDep5,
)
from reuse.project import GlobalLicensingConflict, Project

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


def test_project_conflicting_global_licensing(empty_directory):
    """If both REUSE.toml and .reuse/dep5 exist, expect a
    GlobalLicensingConflict.
    """
    (empty_directory / "REUSE.toml").write_text("version = 1")
    (empty_directory / ".reuse").mkdir()
    (empty_directory / ".reuse/dep5").touch()
    with pytest.raises(GlobalLicensingConflict):
        Project.from_directory(empty_directory)


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
    (empty_directory / ".hg/config").write_text("foo")

    project = Project.from_directory(empty_directory)
    assert not list(project.all_files())


def test_all_files_ignore_license_copying(empty_directory):
    """When there are files names LICENSE, LICENSE.ext, COPYING, or COPYING.ext,
    ignore them.
    """
    (empty_directory / "LICENSE").write_text("foo")
    (empty_directory / "LICENSE.txt").write_text("foo")
    (empty_directory / "COPYING").write_text("foo")
    (empty_directory / "COPYING.txt").write_text("foo")

    project = Project.from_directory(empty_directory)
    assert not list(project.all_files())


def test_all_files_not_ignore_license_copying_no_ext(empty_directory):
    """Do not ignore files that start with LICENSE or COPYING and are followed
    by some non-extension text.
    """
    (empty_directory / "LICENSE_README.md").write_text("foo")
    (empty_directory / "COPYING2").write_text("foo")

    project = Project.from_directory(empty_directory)
    assert len(list(project.all_files())) == 2


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


def test_reuse_info_of_uncommentable_file(empty_directory):
    """When a file is marked uncommentable, but does contain REUSE info, read it
    anyway.
    """
    (empty_directory / "foo.png").write_text("Copyright 2017 Jane Doe")
    project = Project.from_directory(empty_directory)
    result = project.reuse_info_of("foo.png")
    assert len(result) == 1
    assert result[0].copyright_lines


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


def test_reuse_info_of_toml_precedence(empty_directory):
    """When the precedence is set to toml, ignore file contents."""
    (empty_directory / "REUSE.toml").write_text(
        cleandoc(
            """
            version = 1

            [[annotations]]
            path = "foo.py"
            precedence = "override"
            SPDX-FileCopyrightText = "2017 Jane Doe"
            SPDX-License-Identifier = "CC0-1.0"
            """
        )
    )
    (empty_directory / "foo.py").write_text(
        cleandoc(
            """
            # The below should give a parser error. Not going to happen because
            # the file is never parsed.
            SPDX-License-Identifier: ignored AND
            SPDX-FileCopyrightText: ignored
            """
        )
    )
    project = Project.from_directory(empty_directory)
    reuse_infos = project.reuse_info_of("foo.py")
    assert len(reuse_infos) == 1
    reuse_info = reuse_infos[0]
    assert reuse_info.source_type == SourceType.REUSE_TOML
    assert reuse_info.source_path == "REUSE.toml"
    assert reuse_info.path == "foo.py"
    assert LicenseSymbol("CC0-1.0") in reuse_info.spdx_expressions
    assert "2017 Jane Doe" in reuse_info.copyright_lines


def test_reuse_info_of_closest_precedence(empty_directory):
    """When the precedence is set to closest, ignore REUSE.toml contents."""
    (empty_directory / "REUSE.toml").write_text(
        cleandoc(
            """
            version = 1

            [[annotations]]
            path = "foo.py"
            precedence = "closest"
            SPDX-FileCopyrightText = "2017 Jane Doe"
            SPDX-License-Identifier = "CC0-1.0"
            """
        )
    )
    (empty_directory / "foo.py").write_text(
        cleandoc(
            """
            SPDX-License-Identifier: MIT
            SPDX-FileCopyrightText: In File
            """
        )
    )
    project = Project.from_directory(empty_directory)
    reuse_infos = project.reuse_info_of("foo.py")
    assert len(reuse_infos) == 1
    reuse_info = reuse_infos[0]
    assert reuse_info.source_type == SourceType.FILE_HEADER
    assert reuse_info.source_path == "foo.py"
    assert reuse_info.path == "foo.py"
    assert LicenseSymbol("MIT") in reuse_info.spdx_expressions
    assert "SPDX-FileCopyrightText: In File" in reuse_info.copyright_lines


def test_reuse_info_of_closest_precedence_empty(empty_directory):
    """When the precedence is set to closest, but the file is empty, use
    REUSE.toml contents.
    """
    (empty_directory / "REUSE.toml").write_text(
        cleandoc(
            """
            version = 1

            [[annotations]]
            path = "foo.py"
            precedence = "closest"
            SPDX-FileCopyrightText = "2017 Jane Doe"
            SPDX-License-Identifier = "CC0-1.0"
            """
        )
    )
    (empty_directory / "foo.py").touch()
    project = Project.from_directory(empty_directory)
    reuse_infos = project.reuse_info_of("foo.py")
    assert len(reuse_infos) == 1
    reuse_info = reuse_infos[0]
    assert reuse_info.source_type == SourceType.REUSE_TOML
    assert reuse_info.source_path == "REUSE.toml"
    assert reuse_info.path == "foo.py"
    assert LicenseSymbol("CC0-1.0") in reuse_info.spdx_expressions
    assert "2017 Jane Doe" in reuse_info.copyright_lines


def test_reuse_info_of_aggregate_precedence(empty_directory):
    """When the precedence is set to aggregate, aggregate sources."""
    (empty_directory / "REUSE.toml").write_text(
        cleandoc(
            """
            version = 1

            [[annotations]]
            path = "foo.py"
            precedence = "aggregate"
            SPDX-FileCopyrightText = "2017 Jane Doe"
            SPDX-License-Identifier = "CC0-1.0"
            """
        )
    )
    (empty_directory / "foo.py").write_text(
        cleandoc(
            """
            SPDX-License-Identifier: MIT
            SPDX-FileCopyrightText: In File
            """
        )
    )
    project = Project.from_directory(empty_directory)
    reuse_infos = project.reuse_info_of("foo.py")
    assert len(reuse_infos) == 2
    assert reuse_infos[0].source_type != reuse_infos[1].source_type
    for reuse_info in reuse_infos:
        if reuse_info.source_type == SourceType.FILE_HEADER:
            assert reuse_info.source_type
            assert reuse_info.source_path == "foo.py"
            assert reuse_info.path == "foo.py"
            assert LicenseSymbol("MIT") in reuse_info.spdx_expressions
            assert (
                "SPDX-FileCopyrightText: In File" in reuse_info.copyright_lines
            )
        elif reuse_info.source_type == SourceType.REUSE_TOML:
            assert reuse_info.source_path == "REUSE.toml"
            assert reuse_info.path == "foo.py"
            assert LicenseSymbol("CC0-1.0") in reuse_info.spdx_expressions
            assert "2017 Jane Doe" in reuse_info.copyright_lines
        else:
            assert False


def test_reuse_info_of_aggregate_and_closest(empty_directory):
    """A rather tricky case. Top-level REUSE.toml says aggregate. Nearest
    REUSE.toml says closest. The top-level REUSE.toml info should now be
    aggregated with the file contents IF they exist. Else, aggregate with the
    nearest REUSE.toml info.
    """
    (empty_directory / "REUSE.toml").write_text(
        cleandoc(
            """
            version = 1

            [[annotations]]
            path = "src/foo.py"
            precedence = "aggregate"
            SPDX-FileCopyrightText = "2017 Jane Doe"
            SPDX-License-Identifier = "CC0-1.0"
            """
        )
    )
    (empty_directory / "src").mkdir()
    (empty_directory / "src/REUSE.toml").write_text(
        cleandoc(
            """
            version = 1

            [[annotations]]
            path = "foo.py"
            precedence = "closest"
            SPDX-FileCopyrightText = "2017 John Doe"
            SPDX-License-Identifier = "MIT"
            """
        )
    )
    (empty_directory / "src/foo.py").touch()
    project = Project.from_directory(empty_directory)
    assert project.reuse_info_of("src/foo.py") == [
        ReuseInfo(
            spdx_expressions={_LICENSING.parse("CC0-1.0")},
            copyright_lines={"2017 Jane Doe"},
            path="src/foo.py",
            source_path="REUSE.toml",
            source_type=SourceType.REUSE_TOML,
        ),
        ReuseInfo(
            spdx_expressions={_LICENSING.parse("MIT")},
            copyright_lines={"2017 John Doe"},
            path="src/foo.py",
            source_path="src/REUSE.toml",
            source_type=SourceType.REUSE_TOML,
        ),
    ]

    # Populate the file.
    (empty_directory / "src/foo.py").write_text(
        cleandoc(
            """
            # Copyright Example
            # SPDX-License-Identifier: 0BSD
            """
        )
    )
    assert project.reuse_info_of("src/foo.py") == [
        ReuseInfo(
            spdx_expressions={_LICENSING.parse("CC0-1.0")},
            copyright_lines={"2017 Jane Doe"},
            path="src/foo.py",
            source_path="REUSE.toml",
            source_type=SourceType.REUSE_TOML,
        ),
        ReuseInfo(
            spdx_expressions={_LICENSING.parse("0BSD")},
            copyright_lines={"Copyright Example"},
            path="src/foo.py",
            source_path="src/foo.py",
            source_type=SourceType.FILE_HEADER,
        ),
    ]


def test_reuse_info_of_copyright_xor_licensing(empty_directory):
    """Test a corner case where partial REUSE information is defined inside of a
    file (copyright xor licensing). Get the missing information from the
    REUSE.toml.
    """
    (empty_directory / "REUSE.toml").write_text(
        cleandoc(
            """
            version = 1

            [[annotations]]
            path = "foo.py"
            SPDX-FileCopyrightText = "2017 Jane Doe"
            SPDX-License-Identifier = "CC0-1.0"

            [[annotations]]
            path = "bar.py"
            SPDX-License-Identifier = "CC0-1.0"
            """
        )
    )
    (empty_directory / "foo.py").write_text(
        cleandoc(
            """
            SPDX-License-Identifier: MIT
            """
        )
    )
    (empty_directory / "bar.py").write_text(
        cleandoc(
            """
            SPDX-FileCopyrightText: 2017 John Doe
            """
        )
    )
    project = Project.from_directory(empty_directory)

    foo_infos = project.reuse_info_of("foo.py")
    assert len(foo_infos) == 2
    foo_toml_info = [info for info in foo_infos if info.copyright_lines][0]
    assert foo_toml_info.source_type == SourceType.REUSE_TOML
    assert not foo_toml_info.spdx_expressions
    foo_file_info = [info for info in foo_infos if info.spdx_expressions][0]
    assert foo_file_info.source_type == SourceType.FILE_HEADER
    assert not foo_file_info.copyright_lines

    bar_infos = project.reuse_info_of("bar.py")
    assert len(bar_infos) == 2
    bar_toml_info = [info for info in bar_infos if info.spdx_expressions][0]
    assert bar_toml_info.source_type == SourceType.REUSE_TOML
    assert not bar_toml_info.copyright_lines
    bar_file_info = [info for info in bar_infos if info.copyright_lines][0]
    assert bar_file_info.source_type == SourceType.FILE_HEADER
    assert not bar_file_info.spdx_expressions


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


def test_reuse_info_of_binary_succeeds(fake_repository_dep5):
    """reuse_info_of succeeds when the target is covered by dep5."""
    shutil.copy(
        RESOURCES_DIRECTORY / "fsfe.png", fake_repository_dep5 / "doc/fsfe.png"
    )

    project = Project.from_directory(fake_repository_dep5)
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


def test_find_global_licensing_dep5(fake_repository_dep5):
    """Find the dep5 file. Also output a PendingDeprecationWarning."""
    with warnings.catch_warnings(record=True) as caught_warnings:
        result = Project.find_global_licensing(fake_repository_dep5)
        assert result.path == fake_repository_dep5 / ".reuse/dep5"
        assert result.cls == ReuseDep5

        assert len(caught_warnings) == 1
        assert issubclass(
            caught_warnings[0].category, PendingDeprecationWarning
        )


def test_find_global_licensing_reuse_toml(fake_repository_reuse_toml):
    """Find the REUSE.toml file."""
    result = Project.find_global_licensing(fake_repository_reuse_toml)
    assert result.path == fake_repository_reuse_toml / "."
    assert result.cls == NestedReuseTOML


def test_find_global_licensing_none(empty_directory):
    """Find no file."""
    result = Project.find_global_licensing(empty_directory)
    assert result is None


def test_find_global_licensing_conflict(fake_repository_dep5):
    """Expect an error on a conflict"""
    (fake_repository_dep5 / "REUSE.toml").touch()
    with pytest.raises(GlobalLicensingConflict):
        Project.find_global_licensing(fake_repository_dep5)


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

    with pytest.raises(GlobalLicensingParseError):
        Project.from_directory(empty_directory)


# REUSE-IgnoreEnd
