# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
# SPDX-FileCopyrightText: 2020 John Mulligan <jmulligan@redhat.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""This module deals with version control systems."""

import logging
import os
from abc import ABC, abstractmethod
from os import PathLike
from pathlib import Path
from typing import Optional, Set

from ._util import GIT_EXE, HG_EXE, execute_command

_LOGGER = logging.getLogger(__name__)


class VCSStrategy(ABC):
    """Strategy pattern for version control systems."""

    @abstractmethod
    def __init__(self, project: "Project"):
        self.project = project

    @abstractmethod
    def is_ignored(self, path: PathLike) -> bool:
        """Is *path* ignored by the VCS?"""

    @classmethod
    @abstractmethod
    def in_repo(cls, directory: PathLike) -> bool:
        """Is *directory* inside of the VCS repository?

        :raises NotADirectoryError: if directory is not a directory.
        """

    @classmethod
    @abstractmethod
    def find_root(cls, cwd: PathLike = None) -> Optional[Path]:
        """Try to find the root of the project from *cwd*. If none is found,
        return None.

        :raises NotADirectoryError: if directory is not a directory.
        """


class VCSStrategyNone(VCSStrategy):
    """Strategy that is used when there is no VCS."""

    def __init__(self, project: "Project"):
        # pylint: disable=useless-super-delegation
        super().__init__(project)

    def is_ignored(self, path: PathLike) -> bool:
        return False

    @classmethod
    def in_repo(cls, directory: PathLike) -> bool:
        return False

    @classmethod
    def find_root(cls, cwd: PathLike = None) -> Optional[Path]:
        return None


class VCSStrategyGit(VCSStrategy):
    """Strategy that is used for Git."""

    def __init__(self, project):
        super().__init__(project)
        if not GIT_EXE:
            raise FileNotFoundError("Could not find binary for Git")
        self._all_ignored_files = self._find_all_ignored_files()

    def _find_all_ignored_files(self) -> Set[Path]:
        """Return a set of all files ignored by git. If a whole directory is
        ignored, don't return all files inside of it.
        """
        command = [
            GIT_EXE,
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

    def is_ignored(self, path: PathLike) -> bool:
        path = self.project.relative_from_root(path)
        return path in self._all_ignored_files

    @classmethod
    def in_repo(cls, directory: PathLike) -> bool:
        if directory is None:
            directory = Path.cwd()

        if not Path(directory).is_dir():
            raise NotADirectoryError()

        command = [GIT_EXE, "status"]
        result = execute_command(command, _LOGGER, cwd=directory)

        return not result.returncode

    @classmethod
    def find_root(cls, cwd: PathLike = None) -> Optional[Path]:
        if cwd is None:
            cwd = Path.cwd()

        if not Path(cwd).is_dir():
            raise NotADirectoryError()

        command = [GIT_EXE, "rev-parse", "--show-toplevel"]
        result = execute_command(command, _LOGGER, cwd=cwd)

        if not result.returncode:
            path = result.stdout.decode("utf-8")[:-1]
            return Path(os.path.relpath(path, cwd))

        return None


class VCSStrategyHg(VCSStrategy):
    """Strategy that is used for Mercurial."""

    def __init__(self, project: "Project"):
        super().__init__(project)
        if not HG_EXE:
            raise FileNotFoundError("Could not find binary for Mercurial")
        self._all_ignored_files = self._find_all_ignored_files()

    def _find_all_ignored_files(self) -> Set[Path]:
        """Return a set of all files ignored by mercurial. If a whole directory
        is ignored, don't return all files inside of it.
        """
        command = [
            HG_EXE,
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

    def is_ignored(self, path: PathLike) -> bool:
        path = self.project.relative_from_root(path)
        return path in self._all_ignored_files

    @classmethod
    def in_repo(cls, directory: PathLike) -> bool:
        if directory is None:
            directory = Path.cwd()

        if not Path(directory).is_dir():
            raise NotADirectoryError()

        command = [HG_EXE, "root"]
        result = execute_command(command, _LOGGER, cwd=directory)

        return not result.returncode

    @classmethod
    def find_root(cls, cwd: PathLike = None) -> Optional[Path]:
        if cwd is None:
            cwd = Path.cwd()

        if not Path(cwd).is_dir():
            raise NotADirectoryError()

        command = [HG_EXE, "root"]
        result = execute_command(command, _LOGGER, cwd=cwd)

        if not result.returncode:
            path = result.stdout.decode("utf-8")[:-1]
            return Path(os.path.relpath(path, cwd))

        return None


def find_root(cwd: PathLike = None) -> Optional[Path]:
    """Try to find the root of the project from *cwd*. If none is found,
    return None.

    :raises NotADirectoryError: if directory is not a directory.
    """
    if GIT_EXE:
        root = VCSStrategyGit.find_root(cwd=cwd)
        if root:
            return root
    if HG_EXE:
        root = VCSStrategyHg.find_root(cwd=cwd)
        if root:
            return root
    return None
