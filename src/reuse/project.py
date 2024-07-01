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
from collections import defaultdict
from gettext import gettext as _
from pathlib import Path
from typing import DefaultDict, Dict, Iterator, List, NamedTuple, Optional, Type

from binaryornot.check import is_binary

from . import (
    _IGNORE_DIR_PATTERNS,
    _IGNORE_FILE_PATTERNS,
    _IGNORE_MESON_PARENT_DIR_PATTERNS,
    IdentifierNotFound,
    ReuseInfo,
)
from ._licenses import EXCEPTION_MAP, LICENSE_MAP
from ._util import (
    _LICENSEREF_PATTERN,
    StrPath,
    _determine_license_path,
    relative_from_root,
    reuse_info_of_file,
)
from .global_licensing import (
    GlobalLicensing,
    NestedReuseTOML,
    PrecedenceType,
    ReuseDep5,
)
from .vcs import VCSStrategy, VCSStrategyNone, all_vcs_strategies

_LOGGER = logging.getLogger(__name__)


class GlobalLicensingConflict(Exception):
    """There are two global licensing files in the project that are not
    compatible.
    """


class GlobalLicensingFound(NamedTuple):
    path: Path
    cls: Type[GlobalLicensing]


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
        global_licensing: Optional[GlobalLicensing] = None,
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

        self.global_licensing = global_licensing

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
            UnicodeDecodeError: if the global licensing config file could not be
                decoded.
            GlobalLicensingParseError: if the global licensing config file could
                not be parsed.
            GlobalLicensingConflict: if more than one global licensing config
                file is present.
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

        global_licensing: Optional[GlobalLicensing] = None
        found = cls.find_global_licensing(root)
        if found:
            global_licensing = found.cls.from_file(found.path)

        project = cls(
            root,
            vcs_strategy=vcs_strategy,
            global_licensing=global_licensing,
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
        within the file, the .license file, from REUSE.toml, and/or from the
        .reuse/dep5 file.

        The presence of a .license file always means that the file itself will
        not be parsed for REUSE information.

        When information is found from multiple sources, and if the precedence
        for that file in REUSE.toml is 'aggregate' (or if .reuse/dep5 is used),
        then two (or more) :class:`ReuseInfo` objects are returned in list set,
        each with respective discovered REUSE information and information about
        the source.

        Alternatively, if the precedence is set to 'closest' or 'toml', or if
        information was found in only one source, then a list of one item is
        returned.

        The exact precedence handling is detailed in the specification.

        An empty list is returned if no information was found whatsoever.
        """
        # pylint: disable=too-many-branches
        original_path = path
        path = _determine_license_path(path)

        _LOGGER.debug(f"searching '{path}' for REUSE information")

        # This means that only one 'source' of licensing/copyright information
        # is captured in ReuseInfo
        global_results: "DefaultDict[PrecedenceType, List[ReuseInfo]]" = (
            defaultdict(list)
        )
        file_result = ReuseInfo()
        result: List[ReuseInfo] = []

        # Search the global licensing file for REUSE information.
        if self.global_licensing:
            relpath = self.relative_from_root(path)
            global_results = defaultdict(
                list, self.global_licensing.reuse_info_of(relpath)
            )
            for info_list in global_results.values():
                for global_result in info_list:
                    if global_result.contains_copyright_or_licensing():
                        _LOGGER.info(
                            _("'{path}' covered by {global_path}").format(
                                path=path, global_path=global_result.source_path
                            )
                        )

        if PrecedenceType.OVERRIDE in global_results:
            _LOGGER.info(
                _(
                    "'{path}' is covered exclusively by REUSE.toml. Not reading"
                    " the file contents."
                ).format(path=path)
            )
        elif is_binary(str(path)):
            _LOGGER.info(
                _(
                    "'{path}' was detected as a binary file; not searching its"
                    " contents for REUSE information."
                ).format(path=path)
            )
        else:
            file_result = reuse_info_of_file(path, original_path, self.root)

        result.extend(global_results[PrecedenceType.OVERRIDE])
        result.extend(global_results[PrecedenceType.AGGREGATE])
        if file_result.contains_info():
            result.append(file_result)
        if not file_result.contains_copyright_or_licensing():
            result.extend(global_results[PrecedenceType.CLOSEST])
        # Special case: If a file contains only copyright, apply the
        # REUSE.toml's licensing if it exists, and vice versa.
        elif file_result.contains_copyright_xor_licensing():
            if global_results[PrecedenceType.CLOSEST]:
                # There should only by a single CLOSEST result in the list.
                closest = global_results[PrecedenceType.CLOSEST][0]
                if file_result.copyright_lines:
                    result.append(
                        closest.copy(
                            copyright_lines=set(),
                        )
                    )
                elif file_result.spdx_expressions:
                    result.append(
                        closest.copy(
                            spdx_expressions=set(),
                        )
                    )
        return result

    def relative_from_root(self, path: StrPath) -> Path:
        """If the project root is /tmp/project, and *path* is
        /tmp/project/src/file, then return src/file.
        """
        return relative_from_root(path, self.root)

    @classmethod
    def find_global_licensing(
        cls, root: Path
    ) -> Optional[GlobalLicensingFound]:
        """Find the path and corresponding class of a project directory's
        :class:`GlobalLicensing`.

        Raises:
            GlobalLicensingConflict: if more than one global licensing config
                file is present.
        """
        candidate: Optional[GlobalLicensingFound] = None
        dep5_path = root / ".reuse/dep5"
        if (dep5_path).exists():
            # Sneaky workaround to not print this warning.
            if not os.environ.get("_SUPPRESS_DEP5_WARNING"):
                warnings.warn(
                    _(
                        "'.reuse/dep5' is deprecated. You are recommended to"
                        " instead use REUSE.toml. Use `reuse convert-dep5` to"
                        " convert."
                    ),
                    PendingDeprecationWarning,
                )
            candidate = GlobalLicensingFound(dep5_path, ReuseDep5)
        toml_path = None
        with contextlib.suppress(StopIteration):
            toml_path = next(root.rglob("**/REUSE.toml"))
        if toml_path is not None:
            if candidate is not None:
                raise GlobalLicensingConflict(
                    _(
                        "Found both '{new_path}' and '{old_path}'. You"
                        " cannot keep both files simultaneously; they are"
                        " not intercompatible."
                    ).format(new_path=toml_path, old_path=dep5_path)
                )
            candidate = GlobalLicensingFound(root, NestedReuseTOML)
        return candidate

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
