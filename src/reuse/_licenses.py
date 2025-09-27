# SPDX-FileCopyrightText: 2014 Ahmed H. Ismail
# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: Apache-2.0
# SPDX-License-Identifier: GPL-3.0-or-later
#
# load_license_list was copied and altered from its original location
# at <https://github.com/spdx/tools-python/blob/462e986/spdx/config.py>.

"""A list with all SPDX licenses."""
import importlib.resources
import json
from importlib.abc import Traversable

_ROOT: Traversable = importlib.resources.files("reuse")
_LICENSES: Traversable = _ROOT / "resources" / "licenses.json"
_EXCEPTIONS: Traversable = _ROOT / "resources" / "exceptions.json"


def _load_license_list(fp: Traversable) -> tuple[list[int], dict[str, dict]]:
    """Return the licenses list version tuple and a mapping of licenses
    id->name loaded from a JSON file
    from https://github.com/spdx/license-list-data
    """
    licenses_map = {}
    with fp.open("r", encoding="utf8") as lics:
        licenses = json.load(lics)
        version = licenses["licenseListVersion"].split(".")
        for lic in licenses["licenses"]:
            identifier = lic["licenseId"]
            licenses_map[identifier] = lic
    return version, licenses_map


def _load_exception_list(fp: Traversable) -> tuple[list[int], dict[str, dict]]:
    """Return the exceptions list version tuple and a mapping of
    exceptions id->name loaded from a JSON file
    from https://github.com/spdx/license-list-data
    """
    exceptions_map = {}
    with fp.open("r", encoding="utf8") as excs:
        exceptions = json.load(excs)
        version = exceptions["licenseListVersion"].split(".")
        for exc in exceptions["exceptions"]:
            identifier = exc["licenseExceptionId"]
            exceptions_map[identifier] = exc
    return version, exceptions_map


_, LICENSE_MAP = _load_license_list(_LICENSES)
_, EXCEPTION_MAP = _load_exception_list(_EXCEPTIONS)
ALL_MAP = {**LICENSE_MAP, **EXCEPTION_MAP}
ALL_NON_DEPRECATED_MAP = {
    identifier: contents.copy()
    for identifier, contents in ALL_MAP.items()
    if not contents["isDeprecatedLicenseId"]
}
