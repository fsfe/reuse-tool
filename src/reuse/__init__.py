# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2021 Alliander N.V.
# SPDX-FileCopyrightText: 2023 Carmen Bianca BAKKER <carmenbianca@fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""reuse is a tool for compliance with the REUSE recommendations.

Although the API is documented, it is **NOT** guaranteed stable between minor or
even patch releases. The semantic versioning of this program pertains
exclusively to the reuse CLI command. If you want to use reuse as a Python
library, you should pin reuse to an exact version.

Having given the above disclaimer, the API has been relatively stable
nevertheless, and we (the maintainers) do make some efforts to not needlessly
change the public API.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("reuse")
except PackageNotFoundError:
    # package is not installed
    __version__ = "6.2.0"

__author__ = "Carmen Bianca Bakker"
__email__ = "carmenbianca@fsfe.org"
__license__ = "Apache-2.0 AND CC0-1.0 AND CC-BY-SA-4.0 AND GPL-3.0-or-later"
__REUSE_version__ = "3.3"
