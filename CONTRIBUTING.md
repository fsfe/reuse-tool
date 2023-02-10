<!--
SPDX-FileCopyrightText: 2021 Free Software Foundation Europe e.V. <https://fsfe.org>

SPDX-License-Identifier: CC-BY-SA-4.0
-->

# Contribution Guidelines

## Release a new version

- Verify changelog
- Create branch release-x.y.z
- `bumpversion --new-version x.y.z minor`
- `make update-resources`
- Alter changelog
- Do some final tweaks/bugfixes (and alter changelog)
- `make test-release`
- `pip install -i https://test.pypi.org/simple reuse` and test the package.
- Once everything is good, `git tag -s vx.y.z`. Minimal tag message.
- `git push origin vx.y.z`
- `make release`
- `git checkout main`
- `git merge release-x.y.z`
- `git push origin main`
- Create a release on GitHub.
- Update readthedocs (if not happened automatically)
- Update API worker: https://git.fsfe.org/reuse/api-worker#user-content-server
- Make sure package is updated in distros (contact maintainers)
