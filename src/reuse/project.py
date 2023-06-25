# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2023 DB Systel GmbH
# SPDX-FileCopyrightText: 2023 Carmen Bianca BAKKER <carmenbianca@fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Module that contains the central Project class."""

import contextlib
import glob
import logging
import os
import warnings
from gettext import gettext as _
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Union, cast

from boolean.boolean import ParseError
from debian.copyright import Copyright
from debian.copyright import Error as DebianError
from license_expression import ExpressionError

from . import (
    _IGNORE_DIR_PATTERNS,
    _IGNORE_FILE_PATTERNS,
    _IGNORE_MESON_PARENT_DIR_PATTERNS,
    IdentifierNotFound,
    ReuseInfo,
    SourceType,
)
from ._licenses import EXCEPTION_MAP, LICENSE_MAP
from ._util import (
    _HEADER_BYTES,
    GIT_EXE,
    HG_EXE,
    StrPath,
    _contains_snippet,
    _copyright_from_dep5,
    _determine_license_path,
    decoded_text_from_binary,
    extract_reuse_info,
)
from .vcs import (
    VCSStrategy,
    VCSStrategyGit,
    VCSStrategyHg,
    VCSStrategyNone,
    find_root,
)

_LOGGER = logging.getLogger(__name__)


class Project:
    """Simple object that holds the project's root, which is necessary for many
    interactions.
    """

    def __init__(
        self,
        root: StrPath,
        include_submodules: bool = False,
        include_meson_subprojects: bool = False,
    ):
        self._root = Path(root)
        if not self._root.is_dir():
            raise NotADirectoryError(f"{self._root} is no valid path")

        if GIT_EXE and VCSStrategyGit.in_repo(self._root):
            self.vcs_strategy: VCSStrategy = VCSStrategyGit(self)
        elif HG_EXE and VCSStrategyHg.in_repo(self._root):
            self.vcs_strategy = VCSStrategyHg(self)
        else:
            _LOGGER.info(
                _(
                    "project is not a VCS repository or required VCS software"
                    " is not installed"
                )
            )
            self.vcs_strategy = VCSStrategyNone(self)

        self.licenses_without_extension: Dict[str, Path] = {}

        self.license_map = LICENSE_MAP.copy()
        # TODO: Is this correct?
        self.license_map.update(EXCEPTION_MAP)
        self.licenses = self._licenses()
        # Use '0' as None, because None is a valid value...
        self._copyright_val: Optional[Union[int, Copyright]] = 0
        self.include_submodules = include_submodules

        meson_build_path = self._root / "meson.build"
        uses_meson = meson_build_path.is_file()
        self.include_meson_subprojects = (
            include_meson_subprojects and uses_meson
        )

    def all_files(self, directory: Optional[StrPath] = None) -> Iterator[Path]:
        """Yield all files in *directory* and its subdirectories.

        The files that are not yielded are:

        - Files ignored by VCS (e.g., see .gitignore)

        - Files/directories matching IGNORE_*_PATTERNS.
        """
        if directory is None:
            directory = self.root
        directory = Path(directory)

        for root_str, dirs, files in os.walk(directory):
            root = Path(root_str)
            _LOGGER.debug("currently walking in '%s'", root)

            # Don't walk ignored directories
            for dir_ in list(dirs):
                the_dir = root / dir_
                if self._is_path_ignored(the_dir):
                    _LOGGER.debug("ignoring '%s'", the_dir)
                    dirs.remove(dir_)
                elif the_dir.is_symlink():
                    _LOGGER.debug("skipping symlink '%s'", the_dir)
                    dirs.remove(dir_)
                elif (
                    the_dir / ".git"
                ).is_file() and not self.include_submodules:
                    _LOGGER.info(
                        "ignoring '%s' because it is a submodule", the_dir
                    )
                    dirs.remove(dir_)

            # Filter files.
            for file_ in files:
                the_file = root / file_
                if self._is_path_ignored(the_file):
                    _LOGGER.debug("ignoring '%s'", the_file)
                    continue
                if the_file.is_symlink():
                    _LOGGER.debug("skipping symlink '%s'", the_file)
                    continue
                # Suppressing this error because I simply don't want to deal
                # with that here.
                with contextlib.suppress(OSError):
                    if the_file.stat().st_size == 0:
                        _LOGGER.debug("skipping 0-sized file '%s'", the_file)
                        continue

                _LOGGER.debug("yielding '%s'", the_file)
                yield the_file

    def reuse_info_of(self, path: StrPath) -> List[ReuseInfo]:
        """Return REUSE info of *path*.

        This function will return any REUSE information that it can find: from
        within the file, the .license file and/or from the .reuse/dep5 file.

        The presence of a .license file always means that the file itself will
        not be parsed for REUSE information.

        When the .reuse/dep5 file covers a file and there is also REUSE
        information within that file (or within its .license file), then two
        :class:`ReuseInfo` objects are returned in the set, each with respective
        discovered REUSE information and information about the source.
        """
        original_path = path
        path = _determine_license_path(path)

        _LOGGER.debug(f"searching '{path}' for REUSE information")

        # This means that only one 'source' of licensing/copyright information
        # is captured in ReuseInfo
        dep5_result = ReuseInfo()
        file_result = ReuseInfo()
        result = []

        # Search the .reuse/dep5 file for REUSE information.
        if self._copyright:
            dep5_result = _copyright_from_dep5(
                self.relative_from_root(path), self._copyright
            )
            if dep5_result.contains_copyright_or_licensing():
                _LOGGER.info(
                    _("'{path}' covered by .reuse/dep5").format(path=path)
                )

        # Search the file for REUSE information.
        with path.open("rb") as fp:
            try:
                # Completely read the file once to search for possible snippets
                if _contains_snippet(fp):
                    _LOGGER.debug(f"'{path}' seems to contain a SPDX Snippet")
                    read_limit = None
                else:
                    read_limit = _HEADER_BYTES
                # Reset read position
                fp.seek(0)
                # Scan the file for REUSE info, possible limiting the read
                # length
                file_result = extract_reuse_info(
                    decoded_text_from_binary(fp, size=read_limit)
                )
                if file_result.contains_copyright_or_licensing():
                    if path.suffix == ".license":
                        source_type = SourceType.DOT_LICENSE
                    else:
                        source_type = SourceType.FILE_HEADER
                    file_result = file_result.copy(
                        path=self.relative_from_root(original_path).as_posix(),
                        source_path=self.relative_from_root(path).as_posix(),
                        source_type=source_type,
                    )

            except (ExpressionError, ParseError):
                _LOGGER.error(
                    _(
                        "'{path}' holds an SPDX expression that cannot be"
                        " parsed, skipping the file"
                    ).format(path=path)
                )

        # There is both information in a .dep5 file and in the file header
        if dep5_result.contains_info() and file_result.contains_info():
            warnings.warn(
                _(
                    "Copyright and licensing information for"
                    " '{original_path}' has been found in both '{path}' and"
                    " in the DEP5 file located at '{dep5_path}'. The"
                    " information for these two sources has been"
                    " aggregated. In the future this behaviour will change,"
                    " and you will need to explicitly enable aggregation."
                    " See"
                    " <https://github.com/fsfe/reuse-tool/issues/779>. You"
                    " need do nothing yet. Run with"
                    " `--suppress-deprecation` to hide this warning."
                ).format(
                    original_path=original_path,
                    path=path,
                    dep5_path=dep5_result.source_path,
                ),
                PendingDeprecationWarning,
            )
        if dep5_result.contains_info():
            result.append(dep5_result)
        if file_result.contains_info():
            result.append(file_result)
        return result

    def relative_from_root(self, path: StrPath) -> Path:
        """If the project root is /tmp/project, and *path* is
        /tmp/project/src/file, then return src/file.
        """
        path = Path(path)
        try:
            return path.relative_to(self.root)
        except ValueError:
            return Path(os.path.relpath(path, start=self.root))

    def _is_path_ignored(self, path: Path) -> bool:
        """Is *path* ignored by some mechanism?"""
        name = path.name
        parent_parts = path.parent.parts
        parent_dir = parent_parts[-1] if len(parent_parts) > 0 else ""
        if path.is_file():
            for pattern in _IGNORE_FILE_PATTERNS:
                if pattern.match(name):
                    return True
        elif path.is_dir():
            for pattern in _IGNORE_DIR_PATTERNS:
                if pattern.match(name):
                    return True
            if not self.include_meson_subprojects:
                for pattern in _IGNORE_MESON_PARENT_DIR_PATTERNS:
                    if pattern.match(parent_dir):
                        return True

        if self.vcs_strategy.is_ignored(path):
            return True

        return False

    def _identifier_of_license(self, path: Path) -> str:
        """Figure out the SPDX License identifier of a license given its path.
        The name of the path (minus its extension) should be a valid SPDX
        License Identifier.
        """
        if not path.suffix:
            raise IdentifierNotFound(f"{path} has no file extension")
        if path.stem in self.license_map:
            return path.stem
        if path.stem.startswith("LicenseRef-"):
            return path.stem

        raise IdentifierNotFound(
            f"Could not find SPDX License Identifier for {path}"
        )

    @property
    def root(self) -> Path:
        """Path to the root of the project."""
        return self._root

    @property
    def _copyright(self) -> Optional[Copyright]:
        if self._copyright_val == 0:
            copyright_path = self.root / ".reuse/dep5"
            try:
                with copyright_path.open(encoding="utf-8") as fp:
                    self._copyright_val = Copyright(fp)
            except OSError:
                _LOGGER.debug("no .reuse/dep5 file, or could not read it")
            except DebianError:
                _LOGGER.exception(_(".reuse/dep5 has syntax errors"))
            except UnicodeError:
                _LOGGER.exception(_(".reuse/dep5 could not be parsed as utf-8"))

            # This check is a bit redundant, but otherwise I'd have to repeat
            # this line under each exception.
            if not self._copyright_val:
                self._copyright_val = None
        return cast(Optional[Copyright], self._copyright_val)

    def _licenses(self) -> Dict[str, Path]:
        """Return a dictionary of all licenses in the project, with their SPDX
        identifiers as names and paths as values.
        """
        license_files: Dict[str, Path] = {}

        directory = str(self.root / "LICENSES/**")
        for path_str in glob.iglob(directory, recursive=True):
            path = Path(path_str)
            # For some reason, LICENSES/** is resolved even though it
            # doesn't exist. I have no idea why. Deal with that here.
            if not Path(path).exists() or Path(path).is_dir():
                continue
            if Path(path).suffix == ".license":
                continue

            path = self.relative_from_root(path)
            _LOGGER.debug(
                _("determining identifier of '{path}'").format(path=path)
            )

            try:
                identifier = self._identifier_of_license(path)
            except IdentifierNotFound:
                if path.name in self.license_map:
                    _LOGGER.info(
                        _("{path} does not have a file extension").format(
                            path=path
                        )
                    )
                    identifier = path.name
                    self.licenses_without_extension[identifier] = path
                else:
                    identifier = path.stem
                    _LOGGER.warning(
                        _(
                            "Could not resolve SPDX License Identifier of"
                            " {path}, resolving to {identifier}. Make sure the"
                            " license is in the license list found at"
                            " <https://spdx.org/licenses/> or that it starts"
                            " with 'LicenseRef-', and that it has a file"
                            " extension."
                        ).format(path=path, identifier=identifier)
                    )

            if identifier in license_files:
                _LOGGER.critical(
                    _(
                        "{identifier} is the SPDX License Identifier of both"
                        " {path} and {other_path}"
                    ).format(
                        identifier=identifier,
                        path=path,
                        other_path=license_files[identifier],
                    )
                )
                raise RuntimeError(f"Multiple licenses resolve to {identifier}")
            # Add the identifiers
            license_files[identifier] = path
            if (
                identifier.startswith("LicenseRef-")
                and "Unknown" not in identifier
            ):
                self.license_map[identifier] = {
                    "reference": str(path),
                    "isDeprecatedLicenseId": False,
                    "detailsUrl": None,
                    "referenceNumber": None,
                    "name": identifier,
                    "licenseId": identifier,
                    "seeAlso": [],
                    "isOsiApproved": None,
                }

        return license_files


def create_project() -> Project:
    """Create a project object. Try to find the project root from CWD,
    otherwise treat CWD as root.
    """
    root = find_root()
    if root is None:
        root = Path.cwd()
    return Project(root)
