#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2023 DB Systel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Lint 3rd party repositories"""

import argparse
import json
import os
import shutil
import subprocess
import sys

from git import Repo

CLONEDIR = "third-party"
REPOS = {
    "fsfe/reuse-example": {},
    "curl/curl": {},
    "spdx/license-list-XML": {"ignore-failure": True},
}


# Fetch arguments
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "-d",
    "--debug",
    action="store_true",
    help="print DEBUG messages",
)
parser.add_argument(
    "-f",
    "--force",
    action="store_true",
    help="force re-clone of third-party repositories",
)
args = parser.parse_args()


def main(args_):
    """Main function"""
    total_lint_fails = 0
    for repo, settings in REPOS.items():
        repo_dir = f"{CLONEDIR}/{repo}"
        ignore_failure = settings.get("ignore-failure", False)
        error = False

        # Delete local directory if it already exists
        if os.path.isdir(repo_dir) and args_.force:
            shutil.rmtree(repo_dir)

        # Clone repo
        if not os.path.isdir(repo_dir):
            print(f"[INFO] Cloning {repo} to {repo_dir}")
            Repo.clone_from(
                f"https://github.com/{repo}", f"{repo_dir}", filter=["tree:0"]
            )
        else:
            print(f"[INFO] Not cloning {repo} as it exists locally.")

        # Lint repo
        lint_ret = subprocess.run(
            ["reuse", "--root", repo_dir, "lint", "--json"],
            capture_output=True,
            check=False,
        )

        # Analyse output
        # Lint fails unexpectedly
        if lint_ret.returncode != 0 and not ignore_failure:
            error = True
            print(f"[ERROR] Linting {repo} failed unexpectedly")
        # Lint succeeds unexpectedly
        elif lint_ret.returncode == 0 and ignore_failure:
            error = True
            print(f"[ERROR] Linting {repo} succeeded unexpectedly")
        # Lint fails expectedly
        elif lint_ret.returncode != 0 and ignore_failure:
            print(f"[OK] Linting {repo} failed expectedly")
        # Lint succeeds expectedly
        elif lint_ret.returncode == 0 and not ignore_failure:
            print(f"[OK] Linting {repo} succeeded expectedly")

        # Print lint summary in case of error
        if args_.debug or error:
            summary = json.loads(lint_ret.stdout)["summary"]
            print(json.dumps(summary, indent=2))

        # Increment total error counter
        if error:
            total_lint_fails += 1

    return total_lint_fails


if __name__ == "__main__":
    args = parser.parse_args()
    sys.exit(main(args))
