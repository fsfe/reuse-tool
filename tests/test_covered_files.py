# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2023 Carmen Bianca BAKKER <carmenbianca@fsfe.org>
# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for reuse.covered_files."""

import os
from pathlib import Path

from conftest import git, hg, pijul, posix

from reuse.covered_files import iter_files
from reuse.vcs import VCSStrategyGit, VCSStrategyHg, VCSStrategyPijul


class TestIterFiles:
    """Test the iter_files function."""

    def test_simple(self, empty_directory):
        """Given a directory with some files, yield all files."""
        (empty_directory / "foo").write_text("foo")
        (empty_directory / "bar").write_text("foo")

        assert {file_.name for file_ in iter_files(empty_directory)} == {
            "foo",
            "bar",
        }

    def test_ignore_dot_license(self, empty_directory):
        """When file and file.license are present, only yield file."""
        (empty_directory / "foo").write_text("foo")
        (empty_directory / "foo.license").write_text("foo")

        assert {file_.name for file_ in iter_files(empty_directory)} == {"foo"}

    def test_ignore_cal_license(self, empty_directory):
        """CAL licenses contain SPDX tags referencing themselves. They should be
        skipped.
        """
        (empty_directory / "CAL-1.0").write_text("foo")
        (empty_directory / "CAL-1.0.txt").write_text("foo")
        (empty_directory / "CAL-1.0-Combined-Work-Exception").write_text("foo")
        (empty_directory / "CAL-1.0-Combined-Work-Exception.txt").write_text(
            "foo"
        )

        assert not list(iter_files(empty_directory))

    def test_ignore_shl_license(self, empty_directory):
        """SHL-2.1 contains an SPDX tag referencing itself. It should be
        skipped.
        """
        (empty_directory / "SHL-2.1").write_text("foo")
        (empty_directory / "SHL-2.1.txt").write_text("foo")

        assert not list(iter_files(empty_directory))

    def test_ignore_git(self, empty_directory):
        """When the git directory is present, ignore it."""
        (empty_directory / ".git").mkdir()
        (empty_directory / ".git/config").write_text("foo")

        assert not list(iter_files(empty_directory))

    def test_ignore_hg(self, empty_directory):
        """When the hg directory is present, ignore it."""
        (empty_directory / ".hg").mkdir()
        (empty_directory / ".hg/config").write_text("foo")

        assert not list(iter_files(empty_directory))

    def test_ignore_license_copying(self, empty_directory):
        """When there are files names LICENSE, LICENSE.ext, COPYING, or
        COPYING.ext, ignore them.
        """
        (empty_directory / "LICENSE").write_text("foo")
        (empty_directory / "LICENSE.txt").write_text("foo")
        (empty_directory / "COPYING").write_text("foo")
        (empty_directory / "COPYING.txt").write_text("foo")

        assert not list(iter_files(empty_directory))

    def test_not_ignore_license_copying_no_ext(self, empty_directory):
        """Do not ignore files that start with LICENSE or COPYING and are
        followed by some non-extension text.
        """
        (empty_directory / "LICENSE_README.md").write_text("foo")
        (empty_directory / "COPYING2").write_text("foo")

        assert len(list(iter_files(empty_directory))) == 2

    @posix
    def test_ignore_symlinks(self, empty_directory):
        """All symlinks must be ignored."""
        (empty_directory / "blob").write_text("foo")
        (empty_directory / "symlink").symlink_to("blob")

        assert Path("symlink").absolute() not in iter_files(empty_directory)

    def test_ignore_zero_sized(self, empty_directory):
        """Empty files should be skipped."""
        (empty_directory / "foo").touch()

        assert Path("foo").absolute() not in iter_files(empty_directory)

    def test_include_meson_subprojects(self, empty_directory):
        """include_meson_subprojects is correctly interpreted."""
        (empty_directory / "foo.py").write_text("foo.py")
        subprojects_dir = empty_directory / "subprojects"
        subprojects_dir.mkdir()
        libfoo_dir = subprojects_dir / "libfoo"
        libfoo_dir.mkdir()
        bar_file = libfoo_dir / "bar.py"
        bar_file.write_text("pass")

        assert bar_file not in iter_files(empty_directory)
        assert bar_file in iter_files(
            empty_directory, include_meson_subprojects=True
        )

    def test_reuse_toml_ignored(self, empty_directory):
        """REUSE.toml is ignored."""
        (empty_directory / "REUSE.toml").write_text("version = 1")
        assert not list(iter_files(empty_directory))
        assert list(iter_files(empty_directory, include_reuse_tomls=True))


class TestIterFilesSubet:
    """Tests for  subset_files in iter_files."""

    def test_single(self, fake_repository):
        """Only yield the single specified file."""
        result = list(
            iter_files(
                fake_repository,
                subset_files={fake_repository / "src/custom.py"},
            )
        )
        assert result == [fake_repository / "src/custom.py"]

    def test_two(self, fake_repository):
        """Yield multiple specified files."""
        result = set(
            iter_files(
                fake_repository,
                subset_files={
                    fake_repository / "src/custom.py",
                    fake_repository / "src/exception.py",
                },
            )
        )
        assert result == {
            fake_repository / "src/custom.py",
            fake_repository / "src/exception.py",
        }

    def test_non_existent(self, fake_repository):
        """If a file does not exist, don't yield it."""
        result = list(
            iter_files(
                fake_repository,
                subset_files={
                    fake_repository / "src/custom.py",
                    fake_repository / "not_exist.py",
                    fake_repository / "also/does/not/exist.py",
                },
            )
        )
        assert result == [fake_repository / "src/custom.py"]

    def test_outside_cwd(self, fake_repository):
        """If a file is outside of the project, don't yield it."""
        result = list(
            iter_files(
                fake_repository,
                subset_files={
                    fake_repository / "src/custom.py",
                    (fake_repository / "../outside.py").resolve(),
                },
            )
        )
        assert result == [fake_repository / "src/custom.py"]

    def test_empty(self, fake_repository):
        """If no files are provided, yield nothing."""
        result = list(iter_files(fake_repository, subset_files=set()))
        assert not result

    def test_list_arg(self, fake_repository):
        """Also accepts a list argument."""
        result = list(
            iter_files(
                fake_repository,
                subset_files=[fake_repository / "src/custom.py"],
            )
        )
        assert result == [fake_repository / "src/custom.py"]

    def test_relative_path(self, fake_repository):
        """Also handles relative paths."""
        result = list(
            iter_files(fake_repository, subset_files={"src/custom.py"})
        )
        assert result == [fake_repository / "src/custom.py"]


@git
class TestAllFilesGit:
    """Test the iter_files function with git."""

    def test_simple(self, git_repository):
        """Given a Git repository where some files are ignored, do not yield
        those files.
        """
        assert Path("build/hello.py").absolute() not in iter_files(
            git_repository, vcs_strategy=VCSStrategyGit(git_repository)
        )

    def test_not_ignored_if_no_strategy(self, git_repository):
        """If no strategy is provided, the file is not ignored."""
        assert Path("build/hello.py").absolute() in iter_files(git_repository)

    def test_different_cwd(self, git_repository):
        """Given a Git repository where some files are ignored, do not yield
        those files.

        Be in a different CWD during the above.
        """
        os.chdir(git_repository / "LICENSES")
        assert Path("build/hello.py").absolute() not in iter_files(
            git_repository, vcs_strategy=VCSStrategyGit(git_repository)
        )

    def test_ignored_contains_space(self, git_repository):
        """Files that contain spaces are also ignored."""
        (git_repository / "I contain spaces.pyc").write_text("foo")
        assert Path("I contain spaces.pyc").absolute() not in iter_files(
            git_repository, vcs_strategy=VCSStrategyGit(git_repository)
        )

    @posix
    def test_ignored_contains_newline(self, git_repository):
        """Files that contain newlines are also ignored."""
        (git_repository / "hello\nworld.pyc").write_text("foo")
        assert Path("hello\nworld.pyc").absolute() not in iter_files(
            git_repository, vcs_strategy=VCSStrategyGit(git_repository)
        )

    def test_ignore_submodules(self, submodule_repository):
        """Normally ignore submodules."""
        (submodule_repository / "submodule/foo.py").write_text("foo")
        assert Path("submodule/foo.py").absolute() not in iter_files(
            submodule_repository,
            vcs_strategy=VCSStrategyGit(submodule_repository),
        )

    def test_include_submodules(self, submodule_repository):
        """If include_submodules is True, include files from the submodule."""
        (submodule_repository / "submodule/foo.py").write_text("foo")
        assert Path("submodule/foo.py").absolute() in iter_files(
            submodule_repository,
            include_submodules=True,
            vcs_strategy=VCSStrategyGit(submodule_repository),
        )

    def test_submodule_is_ignored(self, submodule_repository):
        """If a submodule is ignored, iter_files shouldn't raise an Exception"""
        (submodule_repository / "submodule/foo.py").write_text("foo")
        gitignore = submodule_repository / ".gitignore"
        contents = gitignore.read_text()
        contents += "\nsubmodule/\n"
        gitignore.write_text(contents)
        assert Path("submodule/foo.py").absolute() not in iter_files(
            submodule_repository,
            vcs_strategy=VCSStrategyGit(submodule_repository),
        )


@hg
class TestAllFilesHg:
    """Test the iter_files function with Mercurial."""

    def test_simple(self, hg_repository):
        """Given a mercurial repository where some files are ignored, do not
        yield those files.
        """
        assert Path("build/hello.py").absolute() not in iter_files(
            hg_repository, vcs_strategy=VCSStrategyHg(hg_repository)
        )

    def test_different_cwd(self, hg_repository):
        """Given a mercurial repository where some files are ignored, do not
        yield those files.

        Be in a different CWD during the above.
        """
        os.chdir(hg_repository / "LICENSES")
        assert Path("build/hello.py").absolute() not in iter_files(
            hg_repository, vcs_strategy=VCSStrategyHg(hg_repository)
        )

    def test_ignored_contains_space(self, hg_repository):
        """File names that contain spaces are also ignored."""
        (hg_repository / "I contain spaces.pyc").touch()
        assert Path("I contain spaces.pyc").absolute() not in iter_files(
            hg_repository, vcs_strategy=VCSStrategyHg(hg_repository)
        )

    @posix
    def test_ignored_contains_newline(self, hg_repository):
        """File names that contain newlines are also ignored."""
        (hg_repository / "hello\nworld.pyc").touch()
        assert Path("hello\nworld.pyc").absolute() not in iter_files(
            hg_repository, vcs_strategy=VCSStrategyHg(hg_repository)
        )


@pijul
class TestAllFilesPijul:
    """Test the iter_files function with Pijul."""

    def test_simple(self, pijul_repository):
        """Given a pijul repository where some files are ignored, do not yield
        those files.
        """
        assert Path("build/hello.py").absolute() not in iter_files(
            pijul_repository, vcs_strategy=VCSStrategyPijul(pijul_repository)
        )

    def test_iter_files_pijul_ignored_different_cwd(self, pijul_repository):
        """Given a pijul repository where some files are ignored, do not yield
        those files.

        Be in a different CWD during the above.
        """
        os.chdir(pijul_repository / "LICENSES")
        assert Path("build/hello.py").absolute() not in iter_files(
            pijul_repository, vcs_strategy=VCSStrategyPijul(pijul_repository)
        )

    def test_ignored_contains_space(self, pijul_repository):
        """File names that contain spaces are also ignored."""
        (pijul_repository / "I contain spaces.pyc").touch()
        assert Path("I contain spaces.pyc").absolute() not in iter_files(
            pijul_repository, vcs_strategy=VCSStrategyPijul(pijul_repository)
        )

    @posix
    def test_ignored_contains_newline(self, pijul_repository):
        """File names that contain newlines are also ignored."""
        (pijul_repository / "hello\nworld.pyc").touch()
        assert Path("hello\nworld.pyc").absolute() not in iter_files(
            pijul_repository, vcs_strategy=VCSStrategyPijul(pijul_repository)
        )
