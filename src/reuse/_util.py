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
# SPDX-License-Identifier: GPL-3.0-or-later

"""Misc. utilities for reuse."""

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import BinaryIO, List, Optional, Union

import chardet


GIT_EXE = shutil.which('git')


try:
    from pygit2 import Repository, GitError
    GIT_METHOD = 'pygit2'
except ImportError:  # pragma: no cover
    if GIT_EXE:
        GIT_METHOD = 'git'
    else:
        GIT_METHOD = None


_logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


PathLike = Union[Path, str]  # pylint: disable=invalid-name


def setup_logging(level: int = logging.WARNING) -> None:
    """Configure logging for reuse."""
    # library_logger is the root logger for reuse.  We configure logging solely
    # for reuse, not for any other libraries.
    library_logger = logging.getLogger('reuse')
    library_logger.setLevel(level)

    if not library_logger.hasHandlers():
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        library_logger.addHandler(handler)


def execute_command(
        command: List[str],
        logger: logging.Logger,
        **kwargs) -> subprocess.CompletedProcess:
    """Run the given command with subprocess.run.  Forward kwargs.  Silence
    output into a pipe unless kwargs override it.
    """
    logger.debug('running %s', ' '.join(command))

    stdout = kwargs.get('stdout', subprocess.PIPE)
    stderr = kwargs.get('stderr', None)

    return subprocess.run(
        command,
        stdout=stdout,
        stderr=stderr,
        **kwargs)


def find_root() -> Optional[Path]:
    """Try to find the root of the project from $PWD.  If none is found, return
    None.
    """
    cwd = Path.cwd()
    if in_git_repo(cwd):
        if GIT_METHOD == 'pygit2':
            repo = Repository(str(cwd))
            return Path(repo.path).parent
        elif GIT_METHOD == 'git':
            command = [GIT_EXE, 'rev-parse', '--show-toplevel']
            result = execute_command(command, _logger, cwd=str(cwd))

            if not result.returncode:
                path = result.stdout.decode('utf-8')[:-1]
                return Path(os.path.relpath(path, str(cwd)))
    return None


def in_git_repo(cwd: PathLike = None) -> bool:
    """Is *cwd* inside of a git repository?

    Always return False if git is not installed.
    """
    if cwd is None:
        cwd = Path.cwd()

    if GIT_METHOD == 'pygit2':
        try:
            Repository(str(cwd))
            return True
        except GitError:
            return False
    elif GIT_METHOD == 'git':
        command = [GIT_EXE, 'status']
        result = execute_command(command, _logger, cwd=str(cwd))

        return not result.returncode

    return False


def _is_binary_string(bytes_string: bytes) -> bool:
    """Given a bytes object, does it look like a binary string or a text
    string?

    Behaviour is based on file(1).
    """
    textchars = bytearray(
        {7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7f})
    return bool(bytes_string.translate(None, textchars))


def decoded_text_from_binary(binary_file: BinaryIO, size: int = None) -> str:
    """Given a binary file object, detect its encoding and return its contents
    as a decoded string.  Do not throw any errors if the encoding contains
    errors:  Just replace the false characters.

    If *size* is specified, only read so many bytes.
    """
    rawdata = binary_file.read(size)
    if _is_binary_string(rawdata):
        raise UnicodeError('cannot decode binary data')
    result = chardet.detect(rawdata)
    encoding = result.get('encoding')
    if encoding is None:
        encoding = 'utf-8'
    try:
        return rawdata.decode(encoding, errors='replace')
    # Handle unknown encodings.
    except LookupError as error:
        raise UnicodeError('could not decode {}'.format(encoding)) from error
