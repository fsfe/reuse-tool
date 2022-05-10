<!--
SPDX-FileCopyrightText: 2021 Free Software Foundation Europe e.V. <https://fsfe.org>

SPDX-License-Identifier: CC-BY-SA-4.0
-->

# Contribution Guidelines

## Table of Contents

- [Release a new version](#release-a-new-version)

## Release a new version

- Verify changelog
- Create branch release-0.XX
- `bumpversion --new-version 0.XX.0 minor`
- Alter changelog
- Do some final tweaks/bugfixes (and alter changelog)
- `make update-resources` (and alter changelog again)
- Once everything is good, `git tag -s v0.XX.0`
- `make test-release`
- Test here possibly
- `git tag -d latest`
- `git tag latest`
- `git push --force --tags origin`
- `git push --force --tags upstream`
- `make release` (use one of the documented keys of maintainers)
- `git checkout master`
- `git merge release-0.XX`
- `git push upstream master`
- Update readthedocs (if not happened automatically)
- Update API worker: https://git.fsfe.org/reuse/api-worker#user-content-server
- Make sure package is updated in distros (contact maintainers)
