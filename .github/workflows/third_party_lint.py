#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2023 DB Systel GmbH
# SPDX-FileCopyrightText: 2023 Carmen Bianca BAKKER <carmenbianca@fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Lint 3rd party repositories"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from git import Repo

CLONE_DIR = Path(tempfile.gettempdir()) / "reuse-third-party"
DEFAULT_REPOS = {
    "https://github.com/fsfe/reuse-example": {},
    "https://github.com/curl/curl": {},
    "https://github.com/spdx/license-list-XML": {"expect-failure": True},
}


def rm_fr(path):
    """Force-remove directory."""
    path = Path(path)
    if path.exists():
        shutil.rmtree(path)


def lint_repo(repo, force_clone=False, expect_failure=False, json=False):
    """Meta function to clone and lint a repository, start to finish."""
    # The sanitation only works on Linux. If we want to do this 'properly', we
    # should use the pathvalidate dependency.
    repo_dir = Path(f"{CLONE_DIR}/{repo.replace('/', '_')}")

    if force_clone:
        rm_fr(repo_dir)

    # Clone repo
    if not repo_dir.exists():
        print(f"[INFO] Cloning {repo} to {repo_dir}")
        repo_git = Repo.clone_from(
            repo,
            repo_dir,
            # Shallow clone.
            depth=1,
        )
    else:
        print(f"[INFO] Not cloning {repo} as it exists locally.")
        repo_git = Repo(repo_dir)

    # Get last commit of repo
    repo_sha = repo_git.head.object.hexsha

    # Lint repo
    print(f"[INFO] Start linting of {repo} (commit {repo_sha})")
    lint_result = subprocess.run(
        ["reuse", "--root", repo_dir, "lint", "--json"],
        capture_output=True,
        check=False,
    )
    if json:
        print(lint_result.stdout.decode("utf-8"))
        print()
    if lint_result.returncode != 0 and not expect_failure:
        print(f"[ERROR] Linting {repo} failed unexpectedly")
    elif lint_result.returncode == 0 and expect_failure:
        print(f"[ERROR] Linting {repo} succeeded unexpectedly")
    elif lint_result.returncode != 0 and expect_failure:
        print(f"[OK] Linting {repo} failed expectedly")
    elif lint_result.returncode == 0 and not expect_failure:
        print(f"[OK] Linting {repo} succeeded expectedly")
    return lint_result


def main(args):
    """Main function"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="force re-clone of third-party repositories",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="show json output of lint",
    )
    parser.add_argument(
        "--expect-failure",
        action="store_true",
        help="expect the lint to fail",
    )
    mutex_group = parser.add_mutually_exclusive_group(required=True)
    mutex_group.add_argument(
        "repo",
        help="link to repository",
        nargs="?",
    )
    mutex_group.add_argument(
        "--defaults",
        action="store_true",
        help="run against some default repositories",
    )
    args = parser.parse_args()

    total_lint_fails = 0
    if args.defaults:
        for repo, settings in DEFAULT_REPOS.items():
            expect_failure = (
                settings.get("expect-failure") or args.expect_failure
            )
            result = lint_repo(
                repo,
                force_clone=args.force,
                expect_failure=expect_failure,
                json=args.json,
            )
            if result.returncode and not expect_failure:
                total_lint_fails += 1
    else:
        result = lint_repo(
            args.repo,
            force_clone=args.force,
            expect_failure=args.expect_failure,
            json=args.json,
        )
        if result.returncode and not args.expect_failure:
            total_lint_fails += 1
    return total_lint_fails


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
