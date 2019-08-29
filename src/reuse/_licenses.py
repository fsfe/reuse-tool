# SPDX-FileCopyrightText: 2014 Ahmed H. Ismail
# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: Apache-2.0
# SPDX-License-Identifier: GPL-3.0-or-later
#
# load_license_list was copied and altered from its original location
# at <https://github.com/spdx/tools-python/blob/master/spdx/config.py>.

"""A list with all SPDX licenses.

Last updated 2019-08-29.
"""

import json
import os

_BASE_DIR = os.path.dirname(__file__)
_RESOURCES_DIR = os.path.join(_BASE_DIR, "resources")
_LICENSES = os.path.join(_RESOURCES_DIR, "licenses.json")
_EXCEPTIONS = os.path.join(_RESOURCES_DIR, "exceptions.json")


def _load_license_list(file_name):
    """Return the licenses list version tuple and a mapping of licenses
    id->name loaded from a JSON file
    from https://github.com/spdx/license-list-data
    """
    licenses_map = {}
    with open(file_name, "r") as lics:
        licenses = json.load(lics)
        version = licenses["licenseListVersion"].split(".")
        for lic in licenses["licenses"]:
            if lic.get("isDeprecatedLicenseId"):
                continue
            name = lic["name"]
            identifier = lic["licenseId"]
            licenses_map[identifier] = name
    return version, licenses_map


def _load_exception_list(file_name):
    """Return the exceptions list version tuple and a mapping of
    exceptions id->name loaded from a JSON file
    from https://github.com/spdx/license-list-data
    """
    exceptions_map = {}
    with open(file_name, "r") as excs:
        exceptions = json.load(excs)
        version = exceptions["licenseListVersion"].split(".")
        for exc in exceptions["exceptions"]:
            if exc.get("isDeprecatedLicenseId"):
                continue
            name = exc["name"]
            identifier = exc["licenseExceptionId"]
            exceptions_map[identifier] = name
    return version, exceptions_map


_, LICENSE_MAP = _load_license_list(_LICENSES)
_, EXCEPTION_MAP = _load_exception_list(_EXCEPTIONS)
