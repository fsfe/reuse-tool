# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2023 Carmen Bianca BAKKER <carmenbianca@fsfe.org>
# SPDX-FileCopyrightText: 2023 Matthias Riße
# SPDX-FileCopyrightText: 2023 DB Systel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Module that contains the central Project class."""

import contextlib
import errno
import glob
import logging
import os
import warnings
from gettext import gettext as _
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Type

from binaryornot.check import is_binary
from boolean.boolean import ParseError
from debian.copyright import Copyright
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
    _LICENSEREF_PATTERN,
    StrPath,
    _contains_snippet,
    _copyright_from_dep5,
    _determine_license_path,
    _parse_dep5,
    decoded_text_from_binary,
    extract_reuse_info,
)
from .vcs import VCSStrategy, VCSStrategyNone, all_vcs_strategies

_LOGGER = logging.getLogger(__name__)


class Project:
    """Simple object that holds the project's root, which is necessary for many
    interactions.
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        root: StrPath,
        vcs_strategy: Optional[Type[VCSStrategy]] = None,
        license_map: Optional[Dict[str, Dict]] = None,
        licenses: Optional[Dict[str, Path]] = None,
        dep5_copyright: Optional[Copyright] = None,
        include_submodules: bool = False,
        include_meson_subprojects: bool = False,
    ):
        self.root = Path(root)

        if vcs_strategy is None:
            vcs_strategy = VCSStrategyNone
        self.vcs_strategy = vcs_strategy(self)

        if license_map is None:
            license_map = LICENSE_MAP
        self.license_map = license_map.copy()
        self.license_map.update(EXCEPTION_MAP)
        self.licenses_without_extension: Dict[str, Path] = {}

        if licenses is None:
            licenses = {}
        self.licenses = licenses

        self.dep5_copyright = dep5_copyright

        self.include_submodules = include_submodules
        self.include_meson_subprojects = include_meson_subprojects

    @classmethod
    def from_directory(
        cls,
        root: StrPath,
        include_submodules: bool = False,
        include_meson_subprojects: bool = False,
    ) -> "Project":
        """A factory method that reads various files in the *root* directory to
        correctly build the :class:`Project` object.

        Args:
            root: The root of the project.
            include_submodules: Whether to also lint VCS submodules.
            include_meson_subprojects: Whether to also lint Meson subprojects.

        Raises:
            FileNotFoundError: if root does not exist.
            NotADirectoryError: if root is not a directory.
            UnicodeDecodeError: if .reuse/dep5 could not be decoded.
            DebianError: if .reuse/dep5 could not be parsed.
        """
        root = Path(root)
        if not root.exists():
            raise FileNotFoundError(
                errno.ENOENT,
                os.strerror(errno.ENOENT),
                str(root),
            )
        if not root.is_dir():
            raise NotADirectoryError(
                errno.ENOTDIR,
                os.strerror(errno.ENOTDIR),
                str(root),
            )

        vcs_strategy = cls._detect_vcs_strategy(root)
        try:
            dep5_copyright: Optional[Copyright] = _parse_dep5(
                root / ".reuse/dep5"
            )
        except FileNotFoundError:
            dep5_copyright = None

        project = cls(
            root,
            vcs_strategy=vcs_strategy,
            dep5_copyright=dep5_copyright,
            include_submodules=include_submodules,
            include_meson_subprojects=include_meson_subprojects,
        )

        # TODO: Because the `_find_licenses()` method is so broad and depends on
        # some object attributes, we set the attribute after creating the
        # object. Ideally we do this before creating the object, but that would
        # require refactoring the method.
        project.licenses = project._find_licenses()

        return project

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
                    not self.include_submodules
                    and self.vcs_strategy.is_submodule(the_dir)
                ):
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
        if self.dep5_copyright:
            dep5_result = _copyright_from_dep5(
                self.relative_from_root(path), self.dep5_copyright
            )
            if dep5_result.contains_copyright_or_licensing():
                _LOGGER.info(
                    _("'{path}' covered by .reuse/dep5").format(path=path)
                )

        if is_binary(str(path)):
            _LOGGER.info(
                _(
                    "'{path}' was detected as a binary file; not searching its"
                    " contents for REUSE information."
                ).format(path=path)
            )
        else:
            # Search the file for REUSE information.
            with path.open("rb") as fp:
                try:
                    read_limit: Optional[int] = _HEADER_BYTES
                    # Completely read the file once
                    # to search for possible snippets
                    if _contains_snippet(fp):
                        _LOGGER.debug(
                            f"'{path}' seems to contain an SPDX Snippet"
                        )
                        read_limit = None
                    # Reset read position
                    fp.seek(0)
                    # Scan the file for REUSE info, possibly limiting the read
                    # length
                    file_result = extract_reuse_info(
                        decoded_text_from_binary(fp, size=read_limit)
                    )
                    if file_result.contains_copyright_or_licensing():
                        source_type = SourceType.FILE_HEADER
                        if path.suffix == ".license":
                            source_type = SourceType.DOT_LICENSE
                        file_result = file_result.copy(
                            path=self.relative_from_root(
                                original_path
                            ).as_posix(),
                            source_path=self.relative_from_root(
                                path
                            ).as_posix(),
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
                    " need do nothing yet. Run "
                    " `reuse --suppress-deprecation lint` to hide this warning."
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

    @staticmethod
    def _relative_from_root_static(path: StrPath, root: StrPath) -> Path:
        """A static method of :method:`Project.relative_fromt_root`."""
        path = Path(path)
        try:
            return path.relative_to(root)
        except ValueError:
            return Path(os.path.relpath(path, start=root))

    def relative_from_root(self, path: StrPath) -> Path:
        """If the project root is /tmp/project, and *path* is
        /tmp/project/src/file, then return src/file.
        """
        return self._relative_from_root_static(path, self.root)

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
        if _LICENSEREF_PATTERN.match(path.stem):
            return path.stem

        raise IdentifierNotFound(
            f"Could not find SPDX License Identifier for {path}"
        )

    def _find_licenses(self) -> Dict[str, Path]:
        """Return a dictionary of all licenses in the project, with their SPDX
        identifiers as names and paths as values.
        """
        # TODO: This method does more than one thing. We ought to simplify it.
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
                raise RuntimeError("Multiple licenses resolve to {identifier}")
            # Add the identifiers
            license_files[identifier] = path
            if (
                _LICENSEREF_PATTERN.match(identifier)
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

    @classmethod
    def _detect_vcs_strategy(cls, root: StrPath) -> Type[VCSStrategy]:
        """For each supported VCS, check if the software is available and if the
        directory is a repository. If not, return :class:`VCSStrategyNone`.
        """
        for strategy in all_vcs_strategies():
            if strategy.EXE and strategy.in_repo(root):
                return strategy

        _LOGGER.info(
            _(
                "project '{}' is not a VCS repository or required VCS"
                " software is not installed"
            ).format(root)
        )
        return VCSStrategyNone
