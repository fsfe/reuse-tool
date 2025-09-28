#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT_PATH = Path(__file__).parent
APP_PATH = ROOT_PATH / "reuse.pyz"
SRC_PATH = ROOT_PATH / "src"
BUILD_PATH = ROOT_PATH / "build"


def main():
    APP_PATH.unlink(missing_ok=True)

    app = BytesIO()
    with ZipFile(app, "w") as bundle:
        bundle.compression = ZIP_DEFLATED
        bundle.compresslevel = 9
        for root, dirs, files in SRC_PATH.walk():
            root: Path
            base = root.relative_to(SRC_PATH)
            for file in files:
                bundle.write(root / file, base / file)
        for root, dirs, files in BUILD_PATH.walk():
            root: Path
            base = root.relative_to(BUILD_PATH)
            dirs[:] = [_ for _ in dirs if "__pycache__" not in _]
            for file in files:
                if str(base / file) in bundle.namelist():  # exists
                    continue
                bundle.write(root / file, base / file)
        bundle.writestr(
            "__main__.py", "from reuse.cli.main import main; main()"
        )

    with open(APP_PATH, "wb") as bundle:
        bundle.write(b"#!/usr/bin/env python3\n")
        bundle.write(app.getvalue())

    APP_PATH.chmod(0o755)


if __name__ == "__main__":
    main()
