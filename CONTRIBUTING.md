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

## Scope and design goals of REUSE

REUSE has a finite scope. The goal is to make upstream licensing **easy,
comprehensive, unambiguous, and machine-readable**. Contributions which
contradict the goals are unlikely to be accepted. Comprehensiveness is
especially important; REUSE provides no real mechanism for excluding a file from
REUSE compliance testing, and it is unlikely that such a mechanism will be
added.

Behaviour changes to linting are also unlikely to be accepted, even if they are
good changes. The linting behaviour should always match the
[REUSE Specification](https://reuse.software/spec/). If you think that the
linting behaviour should change, you should open an issue on the
[reuse-website](https://github.com/fsfe/reuse-website) repository.

The linter does not accept any arguments or configurations which modify its
behaviour in determining compliance. This is intentional.

## Pull requests

Pull requests are generally welcome and encouraged, but please beware that they
may be closed for various reasons, such as:

- The change is out-of-scope for REUSE.
- The change does not align with the design goals of REUSE.
- The change is good, but the maintenance burden is too heavy.

To be safe, open an issue and engage in dialogue before beginning to implement a
feature that may not be accepted.

**Pull requests need not be perfect.** Not all the tests need to pass. A pull
request with 80% of the work done is a lot better than no pull request at all.
We can work together on making the pull request merge-ready, or the maintainers
can finalise the pull request for you.

Making a pull request generally necessitates the following steps:

### Set up local development

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
- `poetry run mypy`
- `make docs`

### Make changes

This is the tricky bit for which no development guide exists. You make changes
somewhere in the code. If you can, do the following things:

- Write docstrings.
- Add type hinting.
- Write tests.
- Update documentation.
- Add self as author to every touched file.
- Add self to `AUTHORS.rst`.

### Commit and submit a pull request

As part of committing, `pre-commit` should run some checks. If you can easily
fix them, fix them. If you get stuck here, **do not worry**. Just skip the
pre-commit step with `git commit -n`, and make a pull request. The maintainers
will be happy to fix those annoying things.

### Make a change log entry

Every pull request should add a change log entry. Change log entries go into
`changelog.d/<directory>/<name>.md`, where `<directory>` is the appropriate
category for the change set, and where `<name>` is a short or random name for
your change set.

The contents of the file should typically look like this:

```markdown
- Added a new feature. (#pr_number)
```

At release time, the contents of the `changelog.d/` directory are compiled into
`CHANGELOG.md` using `protokolo compile`.

Some PRs are excepted from adding change log entries, such as changes which are
too tiny to be significant, certain refactorings, or fixes to pull requests
which were already merged, but not yet released.

## Translation

Translations are welcome at
<https://hosted.weblate.org/projects/fsfe/reuse-tool/>. If you need additional
help to get started, don't hesitate to get in touch with the maintainers.

Broader instructions on how to help the FSFE translate things into local
languages can be found at <https://fsfe.org/contribute/translators/>. The
translators keep in touch with the <translators@lists.fsfe.org> mailing list.

## Development conventions

### Poetry

Because our downstreams may not have a very recent version of Poetry, we should
target `poetry-core>=1.4.0` and `poetry~=1.3.0` when interacting with Poetry,
especially when generating the `poetry.lock` file. You can
`pip install poetry~=1.3.0` to ascertain that you always get this right.

In order to update the `poetry.lock` file while changing as few lines as
possible, run `poetry lock --no-update`.

## Release checklist

- Create branch release-x.y.z
- `bumpver update --set-version vx.y.z`
- `make update-resources`
- `protokolo compile -f version vx.y.z`
- Alter changelog
- `poetry lock` (otherwise documentation won't generate;
  <https://github.com/readthedocs/readthedocs.org/issues/11624>). Update
  versions in `.pre-commit-config.yaml` as necessary.
- Do some final tweaks/bugfixes (and alter changelog)
- `make test-release`
- `pip install -i https://test.pypi.org/simple reuse` and test the package.
- Make a pull request of `release-x.y.z` against `main`.
- Once everything is good, `git tag -s vx.y.z`. Minimal tag message.
- `git push origin vx.y.z`
- `make release`
- Accept the PR.
- Create a release on GitHub.

### After release

- Update readthedocs (if not happened automatically)
- Update API worker: https://git.fsfe.org/reuse/api-worker#user-content-server
- Make sure package is updated in distros (contact maintainers)
- Update the revision in `dev.md` of
  [reuse-website](https://github.com/fsfe/reuse-website).
- If a major release, make sure
  [reuse-action](https://github.com/fsfe/reuse-action/) is updated.
