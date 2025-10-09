# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2020 John Mulligan <jmulligan@redhat.com>
# SPDX-FileCopyrightText: 2023 Markus Haug <korrat@proton.me>
# SPDX-FileCopyrightText: 2024 Skyler Grey <sky@a.starrysky.fyi>
# SPDX-FileCopyrightText: 2025 Jonas Fierlings <fnoegip@gmail.com>
# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""This module deals with version control systems."""

from __future__ import annotations

import logging
import os
import shutil
from abc import ABC, abstractmethod
from collections.abc import Generator
from inspect import isclass
from pathlib import Path
from typing import TYPE_CHECKING

from ._util import execute_command, relative_from_root
from .types import StrPath

if TYPE_CHECKING:
    from .project import Project

_LOGGER = logging.getLogger(__name__)

GIT_EXE = shutil.which("git")
HG_EXE = shutil.which("hg")
JUJUTSU_EXE = shutil.which("jj")
PIJUL_EXE = shutil.which("pijul")


def _find_ancestor(
    directory: StrPath, ancestor: str, is_directory: bool = True
) -> Path | None:
    path = Path(directory).resolve()
    for parent in [path] + list(path.parents):
        if (parent / ancestor).is_dir() or (
            (parent / ancestor).exists() and not is_directory
        ):
            return parent / ancestor
    return None


class VCSStrategy(ABC):
    """Strategy pattern for version control systems."""

    EXE: str | None = None

    def __init__(self, root: StrPath):
        self.root = Path(root)

    @abstractmethod
    def is_ignored(self, path: Path) -> bool:
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
    def find_root(cls, cwd: StrPath | None = None) -> Path | None:
        """Try to find the root of the project from *cwd*. If none is found,
        return None.

        Raises:
            NotADirectoryError: if directory is not a directory.
        """


class VCSStrategyNone(VCSStrategy):
    """Strategy that is used when there is no VCS."""

    def is_ignored(self, path: Path) -> bool:
        return False

    def is_submodule(self, path: StrPath) -> bool:
        return False

    @classmethod
    def in_repo(cls, directory: StrPath) -> bool:
        return False

    @classmethod
    def find_root(cls, cwd: StrPath | None = None) -> Path | None:
        return None


class VCSStrategyGit(VCSStrategy):
    """Strategy that is used for Git."""

    EXE = GIT_EXE

    def __init__(self, root: StrPath):
        super().__init__(root)
        if not self.EXE:
            raise FileNotFoundError("Could not find binary for Git")
        self._all_ignored_files = self._find_all_ignored_files()
        self._submodules = self._find_submodules()

    def _find_all_ignored_files(self) -> set[Path]:
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
        result = execute_command(command, _LOGGER, cwd=self.root)
        all_files = result.stdout.decode("utf-8").split("\0")
        return {Path(file_) for file_ in all_files}

    def _find_submodules(self) -> set[Path]:
        command = [
            str(self.EXE),
            "config",
            "-z",
            "--file",
            ".gitmodules",
            "--get-regexp",
            r"\.path$",
        ]
        result = execute_command(command, _LOGGER, cwd=self.root)
        # The final element may be an empty string. Filter it.
        submodule_entries = [
            entry
            for entry in result.stdout.decode("utf-8").split("\0")
            if entry
        ]
        # Each entry looks a little like 'submodule.submodule.path\nmy_path'.
        return {Path(entry.splitlines()[1]) for entry in submodule_entries}

    def is_ignored(self, path: Path) -> bool:
        path = relative_from_root(path, self.root)
        return path in self._all_ignored_files

    def is_submodule(self, path: StrPath) -> bool:
        return any(
            relative_from_root(Path(path), self.root).resolve()
            == submodule_path.resolve()
            for submodule_path in self._submodules
        )

    @classmethod
    def in_repo(cls, directory: StrPath) -> bool:
        if not Path(directory).is_dir():
            raise NotADirectoryError()

        if _find_ancestor(directory, ".git", is_directory=False):
            command = [str(cls.EXE), "rev-parse", "--is-inside-work-tree"]
            result = execute_command(command, _LOGGER, cwd=directory)

            return not result.returncode
        return False

    @classmethod
    def find_root(cls, cwd: StrPath | None = None) -> Path | None:
        if cwd is None:
            cwd = Path.cwd()

        if not Path(cwd).is_dir():
            raise NotADirectoryError()
        if not _find_ancestor(cwd, ".git", is_directory=False):
            return None

        command = [str(cls.EXE), "rev-parse", "--show-toplevel"]
        result = execute_command(command, _LOGGER, cwd=cwd)

        if not result.returncode:
            path = result.stdout.decode("utf-8")[:-1]
            return Path(os.path.relpath(path, cwd))

        return None


class VCSStrategyHg(VCSStrategy):
    """Strategy that is used for Mercurial."""

    EXE = HG_EXE

    def __init__(self, root: StrPath):
        super().__init__(root)
        if not self.EXE:
            raise FileNotFoundError("Could not find binary for Mercurial")
        self._all_ignored_files = self._find_all_ignored_files()

    def _find_all_ignored_files(self) -> set[Path]:
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
        result = execute_command(command, _LOGGER, cwd=self.root)
        all_files = result.stdout.decode("utf-8").split("\0")
        return {Path(file_) for file_ in all_files}

    def is_ignored(self, path: Path) -> bool:
        path = relative_from_root(path, self.root)
        return path in self._all_ignored_files

    def is_submodule(self, path: StrPath) -> bool:
        # TODO: Implement me.
        return False

    @classmethod
    def in_repo(cls, directory: StrPath) -> bool:
        if not Path(directory).is_dir():
            raise NotADirectoryError()

        if _find_ancestor(directory, ".hg"):
            command = [str(cls.EXE), "root"]
            result = execute_command(command, _LOGGER, cwd=directory)

            return not result.returncode
        return False

    @classmethod
    def find_root(cls, cwd: StrPath | None = None) -> Path | None:
        if cwd is None:
            cwd = Path.cwd()

        if not Path(cwd).is_dir():
            raise NotADirectoryError()
        if not _find_ancestor(cwd, ".hg"):
            return None

        command = [str(cls.EXE), "root"]
        result = execute_command(command, _LOGGER, cwd=cwd)

        if not result.returncode:
            path = result.stdout.decode("utf-8")[:-1]
            return Path(os.path.relpath(path, cwd))

        return None


class VCSStrategyJujutsu(VCSStrategy):
    """Strategy that is used for Jujutsu."""

    EXE = JUJUTSU_EXE

    def __init__(self, root: StrPath):
        super().__init__(root)
        if not self.EXE:
            raise FileNotFoundError("Could not find binary for Jujutsu")
        self._all_tracked_files = self._find_all_tracked_files()

    def _find_all_tracked_files(self) -> set[Path]:
        """
        Return a set of all files tracked in the current jj revision
        """
        version = self._version()
        # TODO: Remove the version check once most distributions ship jj 0.19.0
        # or higher.
        if version is None or version >= (0, 19, 0):
            command = [str(self.EXE), "file", "list"]
        else:
            command = [str(self.EXE), "files"]
        result = execute_command(command, _LOGGER, cwd=self.root)
        all_files = result.stdout.decode("utf-8").split("\n")
        return {Path(file_) for file_ in all_files if file_}

    def _version(self) -> tuple[int, int, int] | None:
        """
        Returns the (major, minor, patch) version of the jujutsu executable,
        or None if the version components cannot be determined.
        """
        result = execute_command(
            [str(self.EXE), "--version"], _LOGGER, cwd=self.root
        )
        lines = result.stdout.decode("utf-8").split("\n")
        # Output has the form `jj major.minor.patch[-hash]\n`.
        try:
            line = lines[0]
            version = line.split(" ")[-1]
            without_hash = version.split("-")[0]
            components = without_hash.split(".")
            return (int(components[0]), int(components[1]), int(components[2]))
        except (IndexError, ValueError) as e:
            _LOGGER.debug("unable to parse jj version: %s", e)
            return None

    def is_ignored(self, path: Path) -> bool:
        path = relative_from_root(path, self.root)

        for tracked in self._all_tracked_files:
            if tracked.parts[: len(path.parts)] == path.parts:
                # We can't check only if the path is in our tracked files as we
                # must support directories as well as files
                #
                # We'll consider a directory "tracked" if there are any tracked
                # files inside it
                return False

        return True

    def is_submodule(self, path: StrPath) -> bool:
        return False

    @classmethod
    def in_repo(cls, directory: StrPath) -> bool:
        if not Path(directory).is_dir():
            raise NotADirectoryError()

        if _find_ancestor(directory, ".jj"):
            command = [str(cls.EXE), "root"]
            result = execute_command(command, _LOGGER, cwd=directory)

            return not result.returncode
        return False

    @classmethod
    def find_root(cls, cwd: StrPath | None = None) -> Path | None:
        if cwd is None:
            cwd = Path.cwd()

        if not Path(cwd).is_dir():
            raise NotADirectoryError()
        if not _find_ancestor(cwd, ".jj"):
            return None

        command = [str(cls.EXE), "root"]
        result = execute_command(command, _LOGGER, cwd=cwd)

        if not result.returncode:
            path = result.stdout.decode("utf-8")[:-1]
            return Path(os.path.relpath(path, cwd))

        return None


class VCSStrategyPijul(VCSStrategy):
    """Strategy that is used for Pijul."""

    EXE = PIJUL_EXE

    def __init__(self, root: StrPath):
        super().__init__(root)
        if not self.EXE:
            raise FileNotFoundError("Could not find binary for Pijul")
        self._all_tracked_files = self._find_all_tracked_files()

    def _find_all_tracked_files(self) -> set[Path]:
        """Return a set of all files tracked by pijul."""
        command = [str(self.EXE), "list"]
        result = execute_command(command, _LOGGER, cwd=self.root)
        all_files = result.stdout.decode("utf-8").splitlines()
        return {Path(file_) for file_ in all_files}

    def is_ignored(self, path: Path) -> bool:
        path = relative_from_root(path, self.root)
        return path not in self._all_tracked_files

    def is_submodule(self, path: StrPath) -> bool:
        # not supported in pijul yet
        return False

    @classmethod
    def in_repo(cls, directory: StrPath) -> bool:
        if not Path(directory).is_dir():
            raise NotADirectoryError()

        if _find_ancestor(directory, ".pijul"):
            command = [str(cls.EXE), "diff", "--short"]
            result = execute_command(command, _LOGGER, cwd=directory)

            return not result.returncode
        return False

    @classmethod
    def find_root(cls, cwd: StrPath | None = None) -> Path | None:
        if cwd is None:
            cwd = Path.cwd()

        # TODO this duplicates pijul's logic.
        # Maybe it should be replaced by calling pijul,
        # but there is no matching subcommand yet.
        path = Path(cwd).resolve()

        if not path.is_dir():
            raise NotADirectoryError()

        dot_pijul = _find_ancestor(path, ".pijul")
        if dot_pijul is not None:
            return dot_pijul.parent
        return None


def all_vcs_strategies() -> Generator[type[VCSStrategy]]:
    """Yield all VCSStrategy classes that aren't the abstract base class."""
    for value in globals().values():
        if (
            isclass(value)
            and issubclass(value, VCSStrategy)
            and value is not VCSStrategy
        ):
            yield value


def find_root(cwd: StrPath | None = None) -> Path | None:
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
