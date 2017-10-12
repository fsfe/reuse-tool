#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of reuse.  It is copyrighted by the contributors recorded
# in the version control history of the file, available from its original
# location: https://git.fsfe.org/carmenbianca/reuse
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

"""Tests for reuse."""

from reuse import _core


def test_extract_license_from_file(file_with_license_comments):
    """Test whether you can correctly extract license information from a code
    file's comments.
    """
    license_infos = _core.extract_license_from_file(file_with_license_comments)
    assert len(license_infos) == 1
    license = license_infos[0]
    assert license.name == file_with_license_comments.license
    assert license.filename == file_with_license_comments.license_file
