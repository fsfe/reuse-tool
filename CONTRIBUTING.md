<!--
SPDX-FileCopyrightText: 2021 Free Software Foundation Europe e.V. <https://fsfe.org>

SPDX-License-Identifier: CC-BY-SA-4.0
-->

# Contribution Guidelines

## Table of Contents

- [Release a new version](#release-a-new-version)

## Release a new version

- Verify changelog
- Create branch release-1.XX.Y
- `bumpversion --new-version 1.XX.Y minor`
- Alter changelog
- Do some final tweaks/bugfixes (and alter changelog)
- `make update-resources` (and alter changelog again)
- Once everything is good, `git tag -s v1.XX.Y`. Minimal tag message.
- `make test-release`
- Test here possibly
- `git push --tags origin`
- `make release` (use one of the documented keys of maintainers)
- `git checkout master`
- `git merge release-1.XX.Y`
- `git push origin master`
- Update readthedocs (if not happened automatically)
- Update API worker: https://git.fsfe.org/reuse/api-worker#user-content-server
- Make sure package is updated in distros (contact maintainers)
