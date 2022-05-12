# SPDX-FileCopyrightText: 2018 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

# The `default.nix` in flake-compat reads `flake.nix` and `flake.lock` from `src` and
# returns an attribute set of the shape `{ defaultNix, shellNix }`

(import (fetchTarball
  "https://github.com/edolstra/flake-compat/archive/master.tar.gz") {
    src = ./.;
  }).shellNix
