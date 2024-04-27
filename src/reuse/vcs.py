# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
# SPDX-FileCopyrightText: 2020 John Mulligan <jmulligan@redhat.com>
# SPDX-FileCopyrightText: 2023 Markus Haug <korrat@proton.me>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""This module deals with version control systems."""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from inspect import isclass
from pathlib import Path
from typing import TYPE_CHECKING, Generator, Optional, Set, Type

from ._util import GIT_EXE, HG_EXE, PIJUL_EXE, StrPath, execute_command

if TYPE_CHECKING:
    from .project import Project

_LOGGER = logging.getLogger(__name__)


class VCSStrategy(ABC):
    """Strategy pattern for version control systems."""

    EXE: str | None = None

    @abstractmethod
    def __init__(self, project: Project):
        self.project = project

    @abstractmethod
    def is_ignored(self, path: StrPath) -> bool:
        """Is *path* ignored by the VCS?"""

    @abstractmethod
    def is_submodule(self, path: StrPath) -> bool:
        """Is *path* a VCS submodule?"""

    @classmethod
    @abstractmethod
    def in_repo(cls, directory: StrPath) -> bool:
        """Is *directory* inside of the VCS repository?

        Raises:
            NotADirectoryError: if directory is not a directory.
        """

    @classmethod
    @abstractmethod
    def find_root(cls, cwd: Optional[StrPath] = None) -> Optional[Path]:
        """Try to find the root of the project from *cwd*. If none is found,
        return None.

        Raises:
            NotADirectoryError: if directory is not a directory.
        """


class VCSStrategyNone(VCSStrategy):
    """Strategy that is used when there is no VCS."""

    def __init__(self, project: Project):
        # pylint: disable=useless-super-delegation
        super().__init__(project)

    def is_ignored(self, path: StrPath) -> bool:
        return False

    def is_submodule(self, path: StrPath) -> bool:
        return False

    @classmethod
    def in_repo(cls, directory: StrPath) -> bool:
        return False

    @classmethod
    def find_root(cls, cwd: Optional[StrPath] = None) -> Optional[Path]:
        return None


class VCSStrategyGit(VCSStrategy):
    """Strategy that is used for Git."""

    EXE = GIT_EXE

    def __init__(self, project: Project):
        super().__init__(project)
        if not self.EXE:
            raise FileNotFoundError("Could not find binary for Git")
        self._all_ignored_files = self._find_all_ignored_files()
        self._submodules = self._find_submodules()

    def _find_all_ignored_files(self) -> Set[Path]:
        """Return a set of all files ignored by git. If a whole directory is
        ignored, don't return all files inside of it.
        """
        command = [
            str(self.EXE),
            "ls-files",
            "--exclude-standard",
            "--ignored",
            "--others",
            "--directory",
            # TODO: This flag is unexpected.  I reported it as a bug in Git.
            # This flag---counter-intuitively---lists untracked directories
            # that contain ignored files.
            "--no-empty-directory",
            # Separate output with \0 instead of \n.
            "-z",
        ]
        result = execute_command(command, _LOGGER, cwd=self.project.root)
        all_files = result.stdout.decode("utf-8").split("\0")
        return {Path(file_) for file_ in all_files}

    def _find_submodules(self) -> Set[Path]:
        command = [
            str(self.EXE),
            "config",
            "-z",
            "--file",
            ".gitmodules",
            "--get-regexp",
            r"\.path$",
        ]
        result = execute_command(command, _LOGGER, cwd=self.project.root)
        # The final element may be an empty string. Filter it.
        submodule_entries = [
            entry
            for entry in result.stdout.decode("utf-8").split("\0")
            if entry
        ]
        # Each entry looks a little like 'submodule.submodule.path\nmy_path'.
        return {Path(entry.splitlines()[1]) for entry in submodule_entries}

    def is_ignored(self, path: StrPath) -> bool:
        path = self.project.relative_from_root(path)
        return path in self._all_ignored_files

    def is_submodule(self, path: StrPath) -> bool:
        return any(
            self.project.relative_from_root(path).resolve()
            == submodule_path.resolve()
            for submodule_path in self._submodules
        )

    @classmethod
    def in_repo(cls, directory: StrPath) -> bool:
        if not Path(directory).is_dir():
            raise NotADirectoryError()

        command = [str(cls.EXE), "status"]
        result = execute_command(command, _LOGGER, cwd=directory)

        return not result.returncode

    @classmethod
    def find_root(cls, cwd: Optional[StrPath] = None) -> Optional[Path]:
        if cwd is None:
            cwd = Path.cwd()

        if not Path(cwd).is_dir():
            raise NotADirectoryError()

        command = [str(cls.EXE), "rev-parse", "--show-toplevel"]
        result = execute_command(command, _LOGGER, cwd=cwd)

        if not result.returncode:
            path = result.stdout.decode("utf-8")[:-1]
            return Path(os.path.relpath(path, cwd))

        return None


class VCSStrategyHg(VCSStrategy):
    """Strategy that is used for Mercurial."""

    EXE = HG_EXE

    def __init__(self, project: Project):
        super().__init__(project)
        if not self.EXE:
            raise FileNotFoundError("Could not find binary for Mercurial")
        self._all_ignored_files = self._find_all_ignored_files()

    def _find_all_ignored_files(self) -> Set[Path]:
        """Return a set of all files ignored by mercurial. If a whole directory
        is ignored, don't return all files inside of it.
        """
        command = [
            str(self.EXE),
            "status",
            "--ignored",
            # terse is marked 'experimental' in the hg help but is documented
            # in the man page. It collapses the output of a dir containing only
            # ignored files to the ignored name like the git command does.
            # TODO: Re-enable this flag in the future.
            # "--terse=i",
            "--no-status",
            "--print0",
        ]
        result = execute_command(command, _LOGGER, cwd=self.project.root)
        all_files = result.stdout.decode("utf-8").split("\0")
        return {Path(file_) for file_ in all_files}

    def is_ignored(self, path: StrPath) -> bool:
        path = self.project.relative_from_root(path)
        return path in self._all_ignored_files

    def is_submodule(self, path: StrPath) -> bool:
        # TODO: Implement me.
        return False

    @classmethod
    def in_repo(cls, directory: StrPath) -> bool:
        if not Path(directory).is_dir():
            raise NotADirectoryError()

        command = [str(cls.EXE), "root"]
        result = execute_command(command, _LOGGER, cwd=directory)

        return not result.returncode

    @classmethod
    def find_root(cls, cwd: Optional[StrPath] = None) -> Optional[Path]:
        if cwd is None:
            cwd = Path.cwd()

        if not Path(cwd).is_dir():
            raise NotADirectoryError()

        command = [str(cls.EXE), "root"]
        result = execute_command(command, _LOGGER, cwd=cwd)

        if not result.returncode:
            path = result.stdout.decode("utf-8")[:-1]
            return Path(os.path.relpath(path, cwd))

        return None


class VCSStrategyPijul(VCSStrategy):
    """Strategy that is used for Pijul."""

    EXE = PIJUL_EXE

    def __init__(self, project: Project):
        super().__init__(project)
        if not self.EXE:
            raise FileNotFoundError("Could not find binary for Pijul")
        self._all_tracked_files = self._find_all_tracked_files()

    def _find_all_tracked_files(self) -> Set[Path]:
        """Return a set of all files tracked by pijul."""
        command = [str(self.EXE), "list"]
        result = execute_command(command, _LOGGER, cwd=self.project.root)
        all_files = result.stdout.decode("utf-8").splitlines()
        return {Path(file_) for file_ in all_files}

    def is_ignored(self, path: StrPath) -> bool:
        path = self.project.relative_from_root(path)
        return path not in self._all_tracked_files

    def is_submodule(self, path: StrPath) -> bool:
        # not supported in pijul yet
        return False

    @classmethod
    def in_repo(cls, directory: StrPath) -> bool:
        if not Path(directory).is_dir():
            raise NotADirectoryError()

        command = [str(cls.EXE), "diff", "--short"]
        result = execute_command(command, _LOGGER, cwd=directory)

        return not result.returncode

    @classmethod
    def find_root(cls, cwd: Optional[StrPath] = None) -> Optional[Path]:
        if cwd is None:
            cwd = Path.cwd()

        # TODO this duplicates pijul's logic.
        # Maybe it should be replaced by calling pijul,
        # but there is no matching subcommand yet.
        path = Path(cwd).resolve()

        if not path.is_dir():
            raise NotADirectoryError()

        while True:
            if (path / ".pijul").is_dir():
                return path

            parent = path.parent
            if parent == path:
                # We reached the filesystem root
                return None

            path = parent


def all_vcs_strategies() -> Generator[Type[VCSStrategy], None, None]:
    """Yield all VCSStrategy classes that aren't the abstract base class."""
    for value in globals().values():
        if (
            isclass(value)
            and issubclass(value, VCSStrategy)
            and value is not VCSStrategy
        ):
            yield value


def find_root(cwd: Optional[StrPath] = None) -> Optional[Path]:
    """Try to find the root of the project from *cwd*. If none is found,
    return None.

    Raises:
        NotADirectoryError: if directory is not a directory.
    """
    for strategy in all_vcs_strategies():
        if strategy.EXE:
            root = strategy.find_root(cwd=cwd)
            if root:
                return root
    return None
