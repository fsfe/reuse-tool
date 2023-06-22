# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2023 Matthias Riße
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for reuse.project."""

import itertools
import os
import shutil
import warnings
from importlib import import_module
from inspect import cleandoc
from pathlib import Path
from textwrap import dedent

import pytest
from license_expression import LicenseSymbol

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
        Project(empty_directory / "foo.py")


def test_all_files(empty_directory):
    """Given a directory with some files, yield all files."""
    (empty_directory / "foo").write_text("foo")
    (empty_directory / "bar").write_text("foo")

    project = Project(empty_directory)
    assert {file_.name for file_ in project.all_files()} == {"foo", "bar"}


def test_all_files_ignore_dot_license(empty_directory):
    """When file and file.license are present, only yield file."""
    (empty_directory / "foo").write_text("foo")
    (empty_directory / "foo.license").write_text("foo")

    project = Project(empty_directory)
    assert {file_.name for file_ in project.all_files()} == {"foo"}


def test_all_files_ignore_cal_license(empty_directory):
    """CAL licenses contain SPDX tags referencing themselves. They should be
    skipped.
    """
    (empty_directory / "CAL-1.0").write_text("foo")
    (empty_directory / "CAL-1.0.txt").write_text("foo")
    (empty_directory / "CAL-1.0-Combined-Work-Exception").write_text("foo")
    (empty_directory / "CAL-1.0-Combined-Work-Exception.txt").write_text("foo")

    project = Project(empty_directory)
    assert not list(project.all_files())


def test_all_files_ignore_shl_license(empty_directory):
    """SHL-2.1 contains an SPDX tag referencing itself. It should be skipped."""
    (empty_directory / "SHL-2.1").write_text("foo")
    (empty_directory / "SHL-2.1.txt").write_text("foo")

    project = Project(empty_directory)
    assert not list(project.all_files())


def test_all_files_ignore_git(empty_directory):
    """When the git directory is present, ignore it."""
    (empty_directory / ".git").mkdir()
    (empty_directory / ".git/config").write_text("foo")

    project = Project(empty_directory)
    assert not list(project.all_files())


def test_all_files_ignore_hg(empty_directory):
    """When the hg directory is present, ignore it."""
    (empty_directory / ".hg").mkdir()
    (empty_directory / ".hg/config").touch()

    project = Project(empty_directory)
    assert not list(project.all_files())


@posix
def test_all_files_ignore_symlinks_to_covered_files(empty_directory):
    """All symlinks to covered files must be ignored."""
    (empty_directory / "blob").write_text("foo")
    (empty_directory / "blob.license").write_text(
        cleandoc(
            """
            SPDX-FileCopyrightText: Jane Doe

            SPDX-License-Identifier: GPL-3.0-or-later
            """
        )
    )
    (empty_directory / "symlink0").symlink_to("blob")
    for i in range(5):
        (empty_directory / f"symlink{i + 1}").symlink_to(f"symlink{i}")
    project = Project(empty_directory)
    for i in range(6):
        assert Path(f"symlink{i}").absolute() not in project.all_files()


no_vcs_params = list(
    filter(
        lambda x: not (x[0] == "non_existent_file" and x[1] is True),
        itertools.product(
            [
                "../outside_file",
                "non_existent_file",
            ],
            [False, True],
        ),
    )
)


@posix
@pytest.mark.parametrize(
    "target,create_target",
    no_vcs_params,
    ids=map(lambda x: f"target={x[0]},create_target={x[1]}", no_vcs_params),
)
def test_all_files_cover_symlinks_to_uncovered_files(
    empty_directory, target, create_target
):
    """All symlinks to files not covered must be included."""
    project_dir = empty_directory / "project_dir"
    project_dir.mkdir()
    (project_dir / "symlink").symlink_to(target)
    if create_target:
        (project_dir / target).parent.mkdir(parents=True, exist_ok=True)
        (project_dir / target).write_text("some content")
    project = Project(project_dir)
    assert (project_dir / "symlink").absolute() in project.all_files()


@posix
@pytest.mark.parametrize(
    "target,create_target",
    no_vcs_params,
    ids=map(lambda x: f"target={x[0]},create_target={x[1]}", no_vcs_params),
)
def test_all_files_ignore_symlinks_to_covered_symlinks(
    empty_directory, target, create_target
):
    """All symlinks to symlinks that are considered to be covered files must be
    ignored.
    """
    project_dir = empty_directory / "project_dir"
    project_dir.mkdir()
    (project_dir / "symlink0").symlink_to(target)
    for i in range(5):
        (project_dir / f"symlink{i + 1}").symlink_to(
            project_dir / f"symlink{i}"
        )
    if create_target:
        (project_dir / target).parent.mkdir(parents=True, exist_ok=True)
        (project_dir / target).write_text("some content")
    project = Project(project_dir)
    for i in range(1, 6):
        assert (
            project_dir / f"symlink{i}"
        ).absolute() not in project.all_files()


def test_all_files_ignore_zero_sized(empty_directory):
    """Empty files should be skipped."""
    (empty_directory / "foo").touch()

    project = Project(empty_directory)
    assert Path("foo").absolute() not in project.all_files()


def test_all_files_git_ignored(git_repository):
    """Given a Git repository where some files are ignored, do not yield those
    files.
    """
    project = Project(git_repository)
    assert Path("build/hello.py").absolute() not in project.all_files()


def test_all_files_git_ignored_different_cwd(git_repository):
    """Given a Git repository where some files are ignored, do not yield those
    files.

    Be in a different CWD during the above.
    """
    os.chdir(git_repository / "LICENSES")
    project = Project(git_repository)
    assert Path("build/hello.py").absolute() not in project.all_files()


def test_all_files_git_ignored_contains_space(git_repository):
    """Files that contain spaces are also ignored."""
    (git_repository / "I contain spaces.pyc").write_text("foo")
    project = Project(git_repository)
    assert Path("I contain spaces.pyc").absolute() not in project.all_files()


@posix
def test_all_files_git_ignored_contains_newline(git_repository):
    """Files that contain newlines are also ignored."""
    (git_repository / "hello\nworld.pyc").write_text("foo")
    project = Project(git_repository)
    assert Path("hello\nworld.pyc").absolute() not in project.all_files()


@posix
def test_all_files_git_ignore_symlinks_to_covered_files(git_repository):
    """All symlinks to covered files must be ignored."""
    (git_repository / "symlink0").symlink_to("doc/index.rst")
    for i in range(5):
        (git_repository / f"symlink{i + 1}").symlink_to(f"symlink{i}")
    project = Project(git_repository)
    for i in range(6):
        assert Path(f"symlink{i}").absolute() not in project.all_files()


git_params = list(
    filter(
        lambda x: not (x[0] == "non_existent_file" and x[1] is True),
        itertools.product(
            [
                ".git/file_in_dotgit",
                ".git/annex/objects/file_in_annex",
                "../outside_file",
                "build/somefile.py",
                "non_existent_file",
            ],
            [False, True],
        ),
    )
)


@posix
@pytest.mark.parametrize(
    "target,create_target",
    git_params,
    ids=map(lambda x: f"target={x[0]},create_target={x[1]}", git_params),
)
def test_all_files_git_cover_symlinks_to_uncovered_files(
    empty_directory, git_repository, target, create_target
):
    """All symlinks to files not covered must be included."""
    git_repository_target_path = empty_directory / "repository"
    shutil.move(git_repository, git_repository_target_path)
    git_repository = git_repository_target_path
    if create_target:
        (git_repository / target).parent.mkdir(parents=True, exist_ok=True)
        (git_repository / target).write_text("some content")
    (git_repository / "symlink").symlink_to(target)
    project = Project(git_repository)
    assert Path("symlink").absolute() in project.all_files()


@posix
@pytest.mark.parametrize(
    "target,create_target",
    git_params,
    ids=map(lambda x: f"target={x[0]},create_target={x[1]}", git_params),
)
def test_all_files_git_ignore_symlinks_to_covered_symlinks(
    empty_directory, git_repository, target, create_target
):
    """All symlinks to symlinks that are considered to be covered files must be
    ignored.
    """
    git_repository_target_path = empty_directory / "repository"
    shutil.move(git_repository, git_repository_target_path)
    git_repository = git_repository_target_path
    if create_target:
        (git_repository / target).parent.mkdir(parents=True, exist_ok=True)
        (git_repository / target).write_text("some content")
    (git_repository / "symlink0").symlink_to(target)
    for i in range(5):
        (git_repository / f"symlink{i + 1}").symlink_to(f"symlink{i}")
    project = Project(git_repository)
    for i in range(1, 6):
        assert Path(f"symlink{i}").absolute() not in project.all_files()


def test_all_files_submodule_is_ignored(submodule_repository):
    """If a submodule is ignored, all_files should not raise an Exception."""
    (submodule_repository / "submodule/foo.py").write_text("foo")
    gitignore = submodule_repository / ".gitignore"
    contents = gitignore.read_text()
    contents += "\nsubmodule/\n"
    gitignore.write_text(contents)
    project = Project(submodule_repository)
    assert Path("submodule/foo.py").absolute() not in project.all_files()


def test_all_files_hg_ignored(hg_repository):
    """Given a mercurial repository where some files are ignored, do not yield
    those files.
    """
    project = Project(hg_repository)
    assert Path("build/hello.py").absolute() not in project.all_files()


def test_all_files_hg_ignored_different_cwd(hg_repository):
    """Given a mercurial repository where some files are ignored, do not yield
    those files.

    Be in a different CWD during the above.
    """
    os.chdir(hg_repository / "LICENSES")
    project = Project(hg_repository)
    assert Path("build/hello.py").absolute() not in project.all_files()


def test_all_files_hg_ignored_contains_space(hg_repository):
    """File names that contain spaces are also ignored."""
    (hg_repository / "I contain spaces.pyc").touch()
    project = Project(hg_repository)
    assert Path("I contain spaces.pyc").absolute() not in project.all_files()


@posix
def test_all_files_hg_ignored_contains_newline(hg_repository):
    """File names that contain newlines are also ignored."""
    (hg_repository / "hello\nworld.pyc").touch()
    project = Project(hg_repository)
    assert Path("hello\nworld.pyc").absolute() not in project.all_files()


@posix
def test_all_files_hg_ignore_symlinks_to_covered_files(hg_repository):
    """All symlinks to covered files must be ignored."""
    (hg_repository / "symlink0").symlink_to("doc/index.rst")
    for i in range(5):
        (hg_repository / f"symlink{i + 1}").symlink_to(f"symlink{i}")
    project = Project(hg_repository)
    for i in range(6):
        assert Path(f"symlink{i}").absolute() not in project.all_files()


hg_params = list(
    filter(
        lambda x: not (x[0] == "non_existent_file" and x[1] is True),
        itertools.product(
            [
                ".hg/file_in_dothg",
                "../outside_file",
                "build/somefile.py",
                "non_existent_file",
            ],
            [False, True],
        ),
    )
)


@posix
@pytest.mark.parametrize(
    "target,create_target",
    hg_params,
    ids=map(lambda x: f"target={x[0]},create_target={x[1]}", hg_params),
)
def test_all_files_hg_cover_symlinks_to_uncovered_files(
    empty_directory, hg_repository, target, create_target
):
    """All symlinks to files not covered must be included."""
    hg_repository_target_path = empty_directory / "repository"
    shutil.move(hg_repository, hg_repository_target_path)
    hg_repository = hg_repository_target_path
    if create_target:
        (hg_repository / target).parent.mkdir(parents=True, exist_ok=True)
        (hg_repository / target).write_text("some content")
    (hg_repository / "symlink").symlink_to(target)
    project = Project(hg_repository)
    assert Path("symlink").absolute() in project.all_files()


@posix
@pytest.mark.parametrize(
    "target,create_target",
    hg_params,
    ids=map(lambda x: f"target={x[0]},create_target={x[1]}", hg_params),
)
def test_all_files_hg_ignore_symlinks_to_covered_symlinks(
    empty_directory, hg_repository, target, create_target
):
    """All symlinks to symlinks that are considered to be covered files must be
    ignored.
    """
    hg_repository_target_path = empty_directory / "repository"
    shutil.move(hg_repository, hg_repository_target_path)
    hg_repository = hg_repository_target_path
    if create_target:
        (hg_repository / target).parent.mkdir(parents=True, exist_ok=True)
        (hg_repository / target).write_text("some content")
    (hg_repository / "symlink0").symlink_to(target)
    for i in range(5):
        (hg_repository / f"symlink{i + 1}").symlink_to(f"symlink{i}")
    project = Project(hg_repository)
    for i in range(1, 6):
        assert Path(f"symlink{i}").absolute() not in project.all_files()


def test_reuse_info_of_file_does_not_exist(fake_repository):
    """Raise FileNotFoundError when asking for the REUSE info of a file that
    does not exist.
    """
    project = Project(fake_repository)
    with pytest.raises(FileNotFoundError):
        project.reuse_info_of(fake_repository / "does_not_exist")


def test_reuse_info_of_directory(empty_directory):
    """Raise IsADirectoryError when calling reuse_info_of on a directory."""
    (empty_directory / "src").mkdir()

    project = Project(empty_directory)
    with pytest.raises((IsADirectoryError, PermissionError)):
        project.reuse_info_of(empty_directory / "src")


def test_reuse_info_of_unlicensed_file(fake_repository):
    """Return an empty ReuseInfo object when asking for the REUSE information
    of a file that has no REUSE information.
    """
    (fake_repository / "foo.py").write_text("foo")
    project = Project(fake_repository)
    assert not bool(project.reuse_info_of("foo.py"))


def test_reuse_info_of_only_copyright(fake_repository):
    """A file contains only a copyright line. Test whether it correctly picks
    up on that.
    """
    (fake_repository / "foo.py").write_text(
        "SPDX-FileCopyrightText: 2017 Jane Doe"
    )
    project = Project(fake_repository)
    reuse_info = project.reuse_info_of("foo.py")
    assert not any(reuse_info.spdx_expressions)
    assert len(reuse_info.copyright_lines) == 1
    assert (
        reuse_info.copyright_lines.pop()
        == "SPDX-FileCopyrightText: 2017 Jane Doe"
    )


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
    project = Project(fake_repository)
    with warnings.catch_warnings(record=True) as caught_warnings:
        reuse_info = project.reuse_info_of("doc/foo.py")
        assert LicenseSymbol("MIT") in reuse_info.spdx_expressions
        assert LicenseSymbol("CC0-1.0") in reuse_info.spdx_expressions
        assert "SPDX-FileCopyrightText: in file" in reuse_info.copyright_lines
        assert "2017 Jane Doe" in reuse_info.copyright_lines

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
    project = Project(empty_directory)
    reuse_info = project.reuse_info_of("foo.py")
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

    project = Project(fake_repository)
    reuse_info = project.reuse_info_of("doc/fsfe.png")
    assert LicenseSymbol("CC0-1.0") in reuse_info.spdx_expressions


def test_license_file_detected(empty_directory):
    """Test whether---when given a file and a license file---the license file
    is detected and read.
    """
    (empty_directory / "foo.py").write_text("foo")
    (empty_directory / "foo.py.license").write_text(
        "SPDX-FileCopyrightText: 2017 Jane Doe\nSPDX-License-Identifier: MIT\n"
    )

    project = Project(empty_directory)
    reuse_info = project.reuse_info_of("foo.py")

    assert "SPDX-FileCopyrightText: 2017 Jane Doe" in reuse_info.copyright_lines
    assert LicenseSymbol("MIT") in reuse_info.spdx_expressions


def test_licenses_filename(empty_directory):
    """Detect the license identifier of a license from its stem."""
    (empty_directory / "LICENSES").mkdir()
    (empty_directory / "LICENSES/foo.txt").write_text("foo")
    project = Project(empty_directory)
    assert "foo" in project.licenses


def test_licenses_no_extension(empty_directory):
    """Detect the license identifier of a license from its full name if it is
    in the license list.
    """
    (empty_directory / "LICENSES").mkdir()
    (empty_directory / "LICENSES/GPL-3.0-or-later").write_text("foo")
    (empty_directory / "LICENSES/MIT-3.0-or-later").write_text("foo")
    project = Project(empty_directory)
    assert "GPL-3.0-or-later" in project.licenses
    assert "MIT-3" in project.licenses


def test_licenses_subdirectory(empty_directory):
    """Find a license in a subdirectory of LICENSES/."""
    (empty_directory / "LICENSES/sub").mkdir(parents=True)
    (empty_directory / "LICENSES/sub/MIT.txt").write_text("foo")
    project = Project(empty_directory)
    assert "MIT" in project.licenses


def test_relative_from_root(empty_directory):
    """A simple test. Given /path/to/root/src/hello.py, return src/hello.py."""
    project = Project(empty_directory)
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
    project = Project(empty_directory)
    parent = empty_directory.parent
    os.chdir(parent)
    assert project.relative_from_root(
        Path(f"{project.root.name}/src/hello.py")
    ) == Path("src/hello.py")


# REUSE-IgnoreEnd
