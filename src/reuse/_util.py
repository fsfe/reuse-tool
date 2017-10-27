#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of reuse.  It is copyrighted by the contributors recorded
# in the version control history of the file, available from its original
# location: https://git.fsfe.org/reuse/reuse
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
# License-Filename: LICENSES/GPL-3.0.txt

"""Misc. utilities for reuse."""

import logging
import shutil
import subprocess
from os import PathLike
from pathlib import Path
from typing import Optional, List

GIT_EXE = shutil.which('git')

_logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


def execute_command(
        command: List[str],
        logger: logging.Logger,
        **kwargs) -> subprocess.CompletedProcess:
    """Run the given command with subprocess.run.  Forward kwargs.  Silence
    output into a pipe unless kwargs override it.
    """
    logger.debug('running %s', ' '.join(command))

    stdout = kwargs.get('stdout', subprocess.PIPE)
    stderr = kwargs.get('stderr', subprocess.PIPE)

    return subprocess.run(
        command,
        stdout=stdout,
        stderr=stderr,
        **kwargs)


def find_root() -> Optional[PathLike]:
    """Try to find the root of the project from $PWD.  If none is found, return
    None.
    """
    cwd = Path.cwd()
    if in_git_repo(cwd):
        command = [GIT_EXE, 'rev-parse', '--show-toplevel']
        result = execute_command(command, _logger, cwd=cwd)

        if not result.returncode:
            return Path(result.stdout.decode('utf-8')[:-1])
    return None


def in_git_repo(cwd: PathLike = None) -> bool:
    """Is *cwd* inside of a git repository?

    Always return False if git is not installed.
    """
    if GIT_EXE is None:
        return False

    if cwd is None:
        cwd = Path.cwd()

    command = [GIT_EXE, 'status']
    result = execute_command(command, _logger, cwd=cwd)

    return not result.returncode
