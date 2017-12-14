#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2017  Free Software Foundation Europe e.V.
#
# This file is part of reuse, available from its original location:
# <https://git.fsfe.org/reuse/reuse/>.
#
# reuse is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# reuse is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# reuse.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0+

"""reuse is a tool for compliance with the REUSE Initiative recommendations."""

# pylint: disable=ungrouped-imports,too-many-arguments

import contextlib
import datetime
import glob
import hashlib
import logging
import os
import re
import sys
from pathlib import Path
from typing import (BinaryIO, Dict, Iterable, Iterator, List, NamedTuple,
                    Optional, Union)
from uuid import uuid4

from debian.copyright import Copyright, NotMachineReadableError

from ._util import (GIT_EXE, PathLike, decoded_text_from_binary,
                    execute_command, in_git_repo)
from .licenses import LICENSES

try:
    from pygit2 import Repository, GitError
    PYGIT2 = True
except ImportError:  # pragma: no cover
    PYGIT2 = False


__author__ = 'Carmen Bianca Bakker'
__email__ = 'carmenbianca@fsfe.org'
__license__ = 'GPLv3+'
__version__ = '0.1.1'

_logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

# Amount of bytes that we assume will be big enough to contain the entire
# comment header (including SPDX tags), so that we don't need to read the
# entire file.
_HEADER_BYTES = 4096

_END_PATTERN = r'(?:\*/)*(?:-->)*$'
_LICENSE_PATTERN = re.compile(
    r'SPDX-Licen[cs]e-Identifier: (.*?)' + _END_PATTERN,
    re.MULTILINE)
_COPYRIGHT_PATTERN = re.compile(
    r'(Copyright .*?)' + _END_PATTERN,
    re.MULTILINE)
_VALID_LICENSE_PATTERN = re.compile(
    r'Valid-Licen[cs]e-Identifier: (.*?)' + _END_PATTERN,
    re.MULTILINE)

_IGNORE_DIR_PATTERNS = [
    re.compile(r'^\.git$'),
    re.compile(r'^\.svn$'),
    re.compile(r'^LICEN[CS]ES$'),
]

_IGNORE_FILE_PATTERNS = [
    re.compile(r'^LICEN[CS]E'),
    re.compile(r'^COPYING'),
    re.compile(r'^copyright$'),
    re.compile(r'.*\.license$'),
    re.compile(r'.*\.spdx$'),
    re.compile(r'^\.gitignore$'),
]

#: Simple structure for holding REUSE information.
ReuseInfo = NamedTuple(
    'ReuseInfo',
    [
        ('spdx_expressions', List[str]),
        ('copyright_lines', List[str])
    ])


class ReuseException(Exception):
    """Base exception."""


class IdentifierNotFound(ReuseException):
    """Could not find SPDX identifier for license file."""


def _checksum(file_object: BinaryIO, hash_function) -> str:
    """Return checksum of *file_object*."""
    result = hash_function()
    for chunk in iter(
            lambda: file_object.read(128 * result.block_size), b''):
        result.update(chunk)
    return result.hexdigest()


def _copyright_from_debian(
        path: PathLike,
        copyright: Copyright) -> ReuseInfo:
    """Find the reuse information of *path* in the Debian copyright object.
    """
    result = copyright.find_files_paragraph(str(path))

    if result is None:
        return ReuseInfo([], [])

    return ReuseInfo(
        [result.license.synopsis],
        list(map(str.strip, result.copyright.splitlines())))


def _identifiers_from_expression(expression: str) -> List[str]:
    """Given an SPDX expression, return a list of the identifiers within.

    >>> _identifiers_from_expression('MIT AND (GPL-3.0+ OR CC0-1.0)')
    ['MIT', 'GPL-3.0+', 'CC0-1.0']
    """
    # All substrings that need to be removed for just the identifiers to
    # remain.
    to_replace = ['OR', 'AND', '(', ')']

    for substring in to_replace:
        expression = expression.replace(substring, '')

    return expression.split()


def extract_reuse_info(text: str) -> ReuseInfo:
    """Extract reuse information from comments in a string."""
    license_matches = list(map(str.strip, _LICENSE_PATTERN.findall(text)))
    copyright_matches = list(map(str.strip, _COPYRIGHT_PATTERN.findall(text)))

    return ReuseInfo(
        license_matches,
        copyright_matches)


def extract_valid_license(text: str) -> str:
    """Extract SPDX identifier from a string."""
    return list(map(str.strip, _VALID_LICENSE_PATTERN.findall(text)))


class Project:
    """Simple object that holds the project's root, which is necessary for many
    interactions.
    """

    def __init__(self, root: PathLike):
        self._root = Path(root)
        if not self._root.is_dir():
            raise NotADirectoryError('%s is no valid path' % self._root)

        self._git_repo = None
        if PYGIT2:
            with contextlib.suppress(GitError):
                self._git_repo = Repository(str(self._root))
        elif GIT_EXE:
            self._git_repo = in_git_repo(self._root)
        else:
            _logger.warning('could not find Git')
        self._license_files = None
        # Use '0' as None, because None is a valid value...
        self._copyright_val = 0

    def all_files(self, directory: PathLike = None) -> Iterator[Path]:
        """Yield all files in *directory* and its subdirectories.

        The files that are not yielded are:

        - Files ignored by VCS (e.g., see .gitignore)

        - Files/directories matching IGNORE_*_PATTERNS.

        If *directory* is a file, yield it if it is not ignored.
        """
        if directory is None:
            directory = self.root
        directory = Path(directory)

        if directory.is_file() and not self._is_path_ignored(directory):
            _logger.debug('yielding %s', directory)
            yield directory

        for root, dirs, files in os.walk(str(directory)):
            root = Path(root)
            _logger.debug('currently walking in %s', root)

            # Don't walk ignored directories
            for dir_ in list(dirs):
                if self._is_path_ignored(root / dir_):
                    _logger.debug('ignoring %s', root / dir_)
                    dirs.remove(dir_)

            # Filter files.
            for file_ in files:
                if self._is_path_ignored(root / file_):
                    _logger.debug('ignoring %s', root / file_)
                    continue

                _logger.debug('yielding %s', file_)
                yield root / file_

    def reuse_info_of(
            self,
            path: PathLike,
            ignore_debian: bool = False) -> ReuseInfo:
        """Get the reuse information of *path*.

        This function will return any reuse information that it can find.  If
        none is found, an empty ReuseInfo object is returned.
        """
        path = Path(path)
        license_path = Path('{}.license'.format(path))

        # Find the correct path to search.  Prioritise 'path.license'.
        if not license_path.exists():
            license_path = path
        _logger.debug('searching %s for reuse information', path)

        # Try to extract reuse information from the file.
        file_result = None

        with license_path.open('rb') as fp:
            try:
                file_result = extract_reuse_info(
                    decoded_text_from_binary(fp, size=_HEADER_BYTES))
                # Only return if the result contains a SPDX-License-Identifier
                # tag.  If it does not, the file may have contained a copyright
                # line.  That means we first want to check debian/copyright.
                if any(file_result.spdx_expressions):
                    return file_result
            except UnicodeError:
                _logger.info('%s could not be decoded', path)

        # Search the debian/copyright file for copyright information.
        if not ignore_debian and self._copyright:
            reuse_info = _copyright_from_debian(
                self._relative_from_root(path),
                self._copyright)
            if any(reuse_info):
                _logger.info('%s covered by debian/copyright', path)
                return reuse_info

        # Return the result we found earlier if debian/copyright didn't contain
        # more information.
        if file_result is not None and any(file_result):
            return file_result

        return ReuseInfo([], [])

    def lint(
            self,
            path: PathLike = None,
            spdx_mandatory: bool = True,
            copyright_mandatory: bool = True,
            ignore_debian: bool = False,
            ignore_missing: bool = False) -> Iterator[Path]:
        """Yield all files under *path* that are not compliant with the REUSE
        recommendations.

        If *path* is not specified, it becomes root.

        The modifiers are explained in :meth:`~Project.lint_file`.
        """
        if path is None:
            path = self.root
        for file_ in self.all_files(path):
            try:
                if self.lint_file(
                        file_,
                        spdx_mandatory=spdx_mandatory,
                        copyright_mandatory=copyright_mandatory,
                        ignore_debian=ignore_debian,
                        ignore_missing=ignore_missing):
                    yield file_
            except OSError:
                _logger.error('Could not read %s', file_)
                yield file_

    def lint_file(
            self,
            path: PathLike,
            spdx_mandatory: bool = True,
            copyright_mandatory: bool = True,
            ignore_debian: bool = False,
            ignore_missing: bool = False) -> int:
        """
        :param path: A path to a file.  If it is not a file, raise an OSError.
        :param spdx_mandatory: The file must have an SPDX expression in its
            reuse information.
        :param copyright_mandatory: The file must have a copyright line in its
            reuse information.
        :param ignore_debian: copyright/debian will not be checked for reuse
            information.
        :param ignore_missing: Declared licences in SPDX expression that could
            not be found in :attr:`~Project.licenses` will not affect the
            linter.

        Check whether *path* complies with the REUSE recommendations.  If it
        does, return 0.  If it does not, return a non-zero integer.  In a
        future version, the non-zero integer may be a bit mask.

        If both *spdx_mandatory* and *copyright_mandatory* are false, this
        function more or less becomes useless.  Common sense is advised.
        """
        path = Path(path)
        if not path.is_file():
            raise OSError('{} is not a file'.format(path))

        reuse_info = self.reuse_info_of(
            path,
            ignore_debian=ignore_debian)

        if spdx_mandatory and not any(reuse_info.spdx_expressions):
            return 1
        if copyright_mandatory and not any(reuse_info.copyright_lines):
            return 1

        if not ignore_missing:
            # Test if all licenses in the expression have an associated
            # license file.  If not, warn the user and yield the file.
            wrong_identifier = self._contains_invalid_identifiers(
                reuse_info.spdx_expressions)
            if wrong_identifier:
                _logger.warning(
                    '%s is licensed under %s, but its license file '
                    'could not be found', path, wrong_identifier)
                return 1

        return 0

    def bill_of_materials(
            self,
            out=sys.stdout,
            ignore_debian: bool = False) -> None:
        """Generate a bill of materials from the project.  The bill of
        materials is written to *out*.

        See https://spdx.org/specifications.
        """
        # Write mandatory tags
        out.write('SPDXVersion: SPDX-2.1\n')
        out.write('DataLicense: CC0-1.0\n')
        out.write('SPDXID: SPDXRef-DOCUMENT\n')

        out.write('DocumentName: {}\n'.format(self.root.resolve().name))
        # TODO: Generate UUID from git revision maybe
        # TODO: Fix the URL
        out.write(
            'DocumentNamespace: '
            'http://spdx.org/spdxdocs/spdx-v2.1-{}\n'.format(uuid4()))

        # Author
        # TODO: Fix Person and Organization
        out.write('Creator: Person: Anonymous ()\n')
        out.write('Creator: Organization: Anonymous ()\n')
        out.write('Creator: Tool: reuse-{}\n'.format(__version__))

        now = datetime.datetime.utcnow()
        now = now.replace(microsecond=0)
        out.write('Created: {}Z\n'.format(now.isoformat()))
        out.write(
            'CreatorComment: <text>This document was created automatically '
            'using available reuse information consistent with the '
            'REUSE Initiative.</text>\n')

        all_files = list(self.all_files())

        # List all DESCRIBES relationships.  This involves some code
        # duplication in determining the relative path to the file and its
        # hash.
        for file_ in all_files:
            relative = self._relative_from_root(file_)
            ref = hashlib.sha1(str(relative).encode('utf-8')).hexdigest()
            out.write(
                'Relationship: SPDXRef-DOCUMENT describes '
                'SPDXRef-{}\n'.format(ref))

        # File information
        for file_ in all_files:
            out.write('\n')
            self._file_information(file_, out, ignore_debian=ignore_debian)

        # Licenses
        for license, path in self.licenses.items():
            if license.startswith('LicenseRef-'):
                out.write('\n')
                out.write('LicenseID: {}\n'.format(license))
                out.write('LicenseName: NOASSERTION\n')

                with (self.root / path).open() as fp:
                    out.write(
                        'ExtractedText: <text>{}</text>\n'.format(fp.read()))

    @property
    def licenses(self) -> Dict[str, Path]:
        """Return a dictionary of all licenses in the project, with their SPDX
        identifiers as names and paths as values.

        If no name could be found for a license file, name it
        "LicenseRef-Unknown0" and count upwards for every other unknown file.
        """
        if self._license_files is not None:
            return self._license_files

        unknown_counter = 0
        license_files = dict()

        patterns = [
            'LICENSE*', 'LICENCE*', 'COPYING*', 'COPYRIGHT*', 'LICENCES/**',
            'LICENSES/**']
        for pattern in patterns:
            pattern = str(self.root.resolve() / pattern)
            for path in glob.iglob(pattern, recursive=True):
                # For some reason, LICENSES/** is resolved even though it
                # doesn't exist.  I have no idea why.  Deal with that here.
                if not Path(path).exists() or Path(path).is_dir():
                    continue
                if Path(path).suffix == '.license':
                    continue

                path = self._relative_from_root(path)
                license_path = Path('{}.license'.format(path))
                if not license_path.exists():
                    license_path = path
                _logger.debug('searching %s for license tags', license_path)

                try:
                    identifiers = self._identifiers_of_license(license_path)
                except IdentifierNotFound:
                    identifier = 'LicenseRef-Unknown{}'.format(unknown_counter)
                    identifiers = [identifier]
                    unknown_counter += 1
                    _logger.warning(
                        'Could not resolve SPDX identifier of %s, '
                        'resolving to %s', path, identifier)

                for identifier in identifiers:
                    if identifier in license_files:
                        _logger.critical(
                            '%s is the SPDX identifier of both %s and %s',
                            identifier,
                            path,
                            license_files[identifier])
                        raise RuntimeError(
                            'Multiple licenses resolve to {}'.format(
                                identifier))
                    license_files[identifier] = path

        self._license_files = license_files
        return self._license_files

    @property
    def root(self) -> Path:
        """Path to the root of the project."""
        return self._root

    @property
    def _copyright(self) -> Optional[Copyright]:
        if self._copyright_val == 0:
            copyright_path = self.root / 'debian' / 'copyright'
            try:
                with copyright_path.open() as fp:
                    self._copyright_val = Copyright(fp)
            except (IOError, OSError):
                _logger.debug('no debian/copyright file, or could not read it')
            except NotMachineReadableError:
                _logger.exception('debian/copyright has syntax errors')

            # This check is a bit redundant, but otherwise I'd have to repeat
            # this line under each exception.
            if not self._copyright_val:
                self._copyright_val = None
        return self._copyright_val

    def _contains_invalid_identifiers(
            self,
            expressions: Iterable[str]) -> Union[bool, str]:
        """Does the list of expressions contain any invalid SPDX identifiers?
        i.e., does any identifier refer to a file that does not exist in
        Project.licenses?

        Return the faulty identifier.

        If the list contains no SPDX identifiers at all, return False.
        """
        for expression in expressions:
            identifiers = _identifiers_from_expression(expression)

            for identifier in identifiers:
                if identifier.rstrip('+') not in self.licenses:
                    return identifier
        return False

    def _identifiers_of_license(self, path: PathLike) -> List[str]:
        """Figure out the SPDX identifier(s) of a license given its path.

        The order of precedence is:

        - A .license file containing the `Valid-License-Identifier` tag.

        - A `Valid-License-Identifier` tag within the license file itself.

        - The name of the file (minus extension) if:

          - The name is an SPDX license.

          - The name starts with 'LicenseRef-'.
        """
        path = Path(path)
        license_path = '{}.license'.format(path)

        # Find the correct path to search.  Prioritise 'path.license'.
        if not (self.root / license_path).exists():
            license_path = path

        with (self.root / license_path).open('rb') as fp:
            result = extract_valid_license(
                decoded_text_from_binary(fp, size=_HEADER_BYTES))
            if any(result):
                return result

        if path.stem in LICENSES or path.stem.startswith('LicenseRef-'):
            return [path.stem]

        raise IdentifierNotFound(
            'Could not find SPDX identifier for {}'.format(path))

    def _ignored_by_git(self, path: PathLike) -> bool:
        """Is *path* covered by the ignore mechanism of git?

        Always return False if git is not installed.
        """
        path = self._relative_from_root(path)

        if PYGIT2:
            return self._git_repo.path_is_ignored(str(path))
        elif GIT_EXE:
            command = [GIT_EXE, 'check-ignore', str(path)]

            result = execute_command(command, _logger, cwd=str(self.root))
            return not result.returncode
        return False

    def _ignored_by_vcs(self, path: PathLike) -> bool:
        """Is *path* covered by the ignore mechanism of the VCS (e.g.,
        .gitignore)?
        """
        if self._git_repo:
            return self._ignored_by_git(path)
        return False

    def _is_path_ignored(self, path: PathLike) -> bool:
        """Is *path* ignored by some mechanism?"""
        path = Path(path)

        if path.is_file():
            for pattern in _IGNORE_FILE_PATTERNS:
                if pattern.match(path.name):
                    return True
        elif path.is_dir():
            for pattern in _IGNORE_DIR_PATTERNS:
                if pattern.match(path.name):
                    return True

        if self._ignored_by_vcs(path):
            return True

        return False

    def _relative_from_root(self, path: PathLike) -> Path:
        """If the project root is /tmp/project, and *path* is
        /tmp/project/src/file, then return src/file.
        """
        return Path(os.path.relpath(str(path), start=str(self.root)))

    def _file_information(
            self,
            path: PathLike,
            out=sys.stdout,
            ignore_debian: bool = False) -> None:
        """Create SPDX File Information for *path*."""
        relative = self._relative_from_root(path)
        encoded = str(relative).encode('utf-8')
        out.write('FileName: ./{}\n'.format(relative))
        out.write('SPDXID: SPDXRef-{}\n'.format(
            hashlib.sha1(encoded).hexdigest()))

        with path.open('rb') as fp:
            out.write(
                'FileChecksum: SHA1: {}\n'.format(
                    _checksum(fp, hashlib.sha1)))

        # IMPORTANT: Make no assertion about concluded license.  This tool
        # cannot, with full certainty, determine the license of a file.
        out.write('LicenseConcluded: NOASSERTION\n')

        reuse_info = self.reuse_info_of(path, ignore_debian=ignore_debian)

        for spdx in reuse_info.spdx_expressions:
            out.write('LicenseInfoInFile: {}\n'.format(spdx))

        if reuse_info.copyright_lines:
            for line in reuse_info.copyright_lines:
                out.write('FileCopyrightText: <text>{}</text>\n'.format(line))
        else:
            out.write('FileCopyrightText: NONE\n')
