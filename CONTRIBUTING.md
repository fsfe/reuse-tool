<!--
SPDX-FileCopyrightText: 2021 Free Software Foundation Europe e.V. <https://fsfe.org>

SPDX-License-Identifier: CC-BY-SA-4.0
-->

# Contribution guidelines

Any issues or suggestions are welcome at <https://github.com/fsfe/reuse-tool> or
via e-mail to one of the maintainers. General inquiries can be sent to
<reuse@lists.fsfe.org>.

## Code of conduct

Interaction within this project is covered by the
[FSFE's Code of Conduct](https://fsfe.org/about/codeofconduct).

## Pull requests

Pull requests are generally welcome and encouraged, but please beware that they
may be closed as out-of-scope or otherwise not aligned with the design goals. To
be safe, open an issue and engage in dialogue before beginning to implement a
feature that may not be accepted.

When making a pull request, don't hesitate to add yourself to the AUTHORS.rst
file and the copyright headers of the files you touch.

## Translation

Translations are welcome at
<https://hosted.weblate.org/projects/fsfe/reuse-tool/>. If you need additional
help to get started, don't hesitate to get in touch with the maintainers.

Broader instructions on how to help the FSFE translate things into local
languages can be found at <https://fsfe.org/contribute/translators/>. The
translators keep in touch with the <translators@lists.fsfe.org> mailing list.

## Local development

Starting local development is very simple, just execute the following commands:

```bash
git clone git@github.com:fsfe/reuse-tool.git
cd reuse-tool/
poetry install  # You may need to install poetry using your package manager.
poetry run pre-commit install  # Using poetry is optional here if you already have pre-commit.
```

Next, you'll find the following commands handy:

- `poetry run reuse`
- `poetry run pytest`
- `poetry run pylint src`
- `make docs`

## Release checklist

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
