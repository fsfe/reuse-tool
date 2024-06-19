<!--
SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>

SPDX-License-Identifier: CC-BY-SA-4.0
-->

# reuse

[![The latest version of reuse can be found on PyPI.](https://img.shields.io/pypi/v/reuse.svg)](https://pypi.python.org/pypi/reuse)
[![Information on what versions of Python reuse supports can be found on PyPI.](https://img.shields.io/pypi/pyversions/reuse.svg)](https://pypi.python.org/pypi/reuse)
[![REUSE status](https://api.reuse.software/badge/github.com/fsfe/reuse-tool)](https://api.reuse.software/info/github.com/fsfe/reuse-tool)
[![standard-readme compliant](https://img.shields.io/badge/readme%20style-standard-brightgreen.svg)](https://github.com/RichardLitt/standard-readme)
[![Packaging status](https://repology.org/badge/tiny-repos/reuse.svg?header=in%20distro%20repos)](https://repology.org/project/reuse/versions)
[![Translation status](https://hosted.weblate.org/widgets/fsfe/-/reuse-tool/svg-badge.svg)](https://hosted.weblate.org/projects/fsfe/reuse-tool/)

reuse is a tool for compliance with the [REUSE](https://reuse.software/)
recommendations.

- Documentation: <https://reuse.readthedocs.io> and <https://reuse.software>
- Source code: <https://github.com/fsfe/reuse-tool>
- PyPI: <https://pypi.python.org/pypi/reuse>
- REUSE: 3.2
- Python: 3.8+

## Table of contents

- [Background](#background)
- [Install](#install)
- [Usage](#usage)
- [Maintainers](#maintainers)
- [Contributing](#contributing)
- [Licensing](#licensing)

## Background

<!-- REUSE-IgnoreStart -->

Copyright and licensing is difficult, especially when reusing software from
different projects that are released under various different licenses.
[REUSE](https://reuse.software) was started by the
[Free Software Foundation Europe](https://fsfe.org) (FSFE) to provide a set of
recommendations to make licensing your Free Software projects easier. Not only
do these recommendations make it easier for you to declare the licenses under
which your works are released, but they also make it easier for a computer to
understand how your project is licensed.

<!-- REUSE-IgnoreEnd -->

As a short summary, the recommendations are threefold:

1. Choose and provide licenses
2. Add copyright and licensing information to each file
3. Confirm REUSE compliance

You are recommended to read [our tutorial](https://reuse.software/tutorial) for
a step-by-step guide through these three steps. The
[FAQ](https://reuse.software/faq) covers basic questions about licensing,
copyright, and more complex use cases. Advanced users and integrators will find
the [full specification](https://reuse.software/spec) helpful.

This tool exists to facilitate the developer in complying with the above
recommendations.

There are [other tools](https://reuse.software/comparison) that have a lot more
features and functionality surrounding the analysis and inspection of copyright
and licenses in software projects. The REUSE helper tool, on the other hand, is
solely designed to be a simple tool to assist in compliance with the REUSE
recommendations.

## Install

### Installation via package manager (Recommended)

There are packages available for easy install on many operating systems. You are
welcome to help us package this tool for more distributions!

An automatically generated list can be found at
[repology.org](https://repology.org/project/reuse/versions), without any
guarantee for completeness.

### Install and run via pipx (Recommended)

The following one-liner both installs and runs this tool from
[PyPI](https://pypi.org/project/reuse/) via
[pipx](https://pypa.github.io/pipx/):

```bash
pipx run reuse lint
```

pipx automatically isolates reuse into its own Python virtualenv, which means
that it won't interfere with other Python packages, and other Python packages
won't interfere with it.

If you want to be able to use reuse without prepending it with `pipx run` every
time, install it globally like so:

```bash
pipx install reuse
```

reuse will then be available in `~/.local/bin`, which must be added to your
`$PATH`.

After this, make sure that `~/.local/bin` is in your `$PATH`. On Windows, the
required path for your environment may look like
`%USERPROFILE%\AppData\Roaming\Python\Python39\Scripts`, depending on the Python
version you have installed.

To upgrade reuse, run this command:

```bash
pipx upgrade reuse
```

For full functionality, the following pieces of software are recommended:

- Git
- Mercurial 4.3+
- Pijul

### Installation via pip

To install reuse into `~/.local/bin`, run:

```bash
pip3 install --user reuse
```

Subsequently, make sure that `~/.local/bin` is in your `$PATH` like described in
the previous section.

To upgrade reuse, run this command:

```bash
pip3 install --user --upgrade reuse
```

### Installation from source

You can also install this tool from the source code, but we recommend the
methods above for easier and more stable updates. Please make sure the
requirements for the installation via pip are present on your machine.

```bash
pip install .
```

## Usage

First, read the [REUSE tutorial](https://reuse.software/tutorial/). In a
nutshell:

<!-- REUSE-IgnoreStart -->

1. Put your licenses in the `LICENSES/` directory.
2. Add a comment header to each file that says
   `SPDX-License-Identifier: GPL-3.0-or-later`, and
   `SPDX-FileCopyrightText: $YEAR $NAME`. You can be flexible with the format,
   just make sure that the line starts with `SPDX-FileCopyrightText:`.
3. Verify your work using this tool.

Example of header:

```
# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: CC-BY-SA-4.0
```

<!-- REUSE-IgnoreEnd -->

### CLI

To check against the recommendations, use `reuse lint`:

```
~/Projects/reuse-tool $ reuse lint
[...]

Congratulations! Your project is compliant with version 3.2 of the REUSE Specification :-)
```

This tool can do various more things, detailed in the documentation. Here a
short summary:

- `annotate` --- Add copyright and/or licensing information to the header of a
  file.
- `download` --- Download the specified license into the `LICENSES/` directory.
- `init` --- Set up the project for REUSE compliance.
- `lint` --- Verify the project for REUSE compliance.
- `spdx` --- Generate an SPDX Document of all files in the project.
- `supported-licenses` --- Prints all licenses supported by REUSE.

### Example demo

In this screencast, we are going to follow the
[tutorial](https://reuse.software/tutorial), making the
[REUSE example repository](https://github.com/fsfe/reuse-example/) compliant.

![Demo of some basic REUSE tool commands](https://download.fsfe.org/videos/reuse/screencasts/reuse-tool.gif)

### Run in Docker

The `fsfe/reuse` Docker image is available on
[Docker Hub](https://hub.docker.com/r/fsfe/reuse). With it, you can easily
include REUSE in CI/CD processes. This way, you can check for REUSE compliance
for each build. In our [resources for developers](https://reuse.software/dev/)
you can learn how to integrate the REUSE tool in Drone, Travis, GitHub, or
GitLab CI.

You can run the helper tool simply by providing the command you want to run
(e.g., `lint`, `spdx`). The image's working directory is `/data` by default. So
if you want to lint a project that is in your current working directory, you can
mount it on the container's `/data` directory, and tell the tool to lint. That
looks a little like this:

```bash
docker run --rm --volume $(pwd):/data fsfe/reuse lint
```

You can also provide additional arguments, like so:

```bash
docker run --rm --volume $(pwd):/data fsfe/reuse --include-submodules spdx -o out.spdx
```

The available tags are:

- `latest` --- the most recent release of reuse.
- `{major}` --- the latest major release.
- `{major}.{minor}` --- the latest minor release.
- `{major}.{minor}.{patch}` --- a precise release.

You can add `-debian` to any of the tags to get a Debian-based instead of an
Alpine-based image, which is larger, but may be better suited for license
compliance.

### Run as pre-commit hook

You can automatically run `reuse lint` on every commit as a pre-commit hook for
Git. This uses [pre-commit](https://pre-commit.com/). Once you
[have it installed](https://pre-commit.com/#install), add this to the
`.pre-commit-config.yaml` in your repository:

```yaml
repos:
  - repo: https://github.com/fsfe/reuse-tool
    rev: v3.0.2
    hooks:
      - id: reuse
```

Then run `pre-commit install`. Now, every time you commit, `reuse lint` is run
in the background, and will prevent your commit from going through if there was
an error.

## Maintainers

- Carmen Bianca Bakker <carmenbianca@fsfe.org>

### Former maintainers

- Max Mehl <max.mehl@fsfe.org>
- Linus Sehn <linus@fsfe.org>

## Contributing

If you're interested in contributing to the reuse project, there are several
ways to get involved. Development of the project takes place on GitHub at
<https://github.com/fsfe/reuse-tool>. There, you can submit bug reports, feature
requests, and pull requests. Even and especially when in doubt, feel free to
open an issue with a question. Contributions of all types are welcome, and the
development team is happy to provide guidance and support for new contributors.

You should exercise some caution when opening a pull request to make changes
which were not (yet) acknowledged by the team as pertinent. Such pull requests
may be closed, leading to disappointment. To avoid this, please open an issue
first.

Additionally, the <reuse@lists.fsfe.org> mailing list is available for
discussion and support related to the project.

You can find the full contribution guidelines at
<https://reuse.readthedocs.io/en/latest/contribute.html>.

## Licensing

This work is licensed under multiple licences. Because keeping this section
up-to-date is challenging, here is a brief summary as of April 2024:

- All original source code is licensed under GPL-3.0-or-later.
- All documentation is licensed under CC-BY-SA-4.0.
- Some configuration and data files are licensed under CC0-1.0.
- Some code borrowed from
  [spdx/tools-python](https://github.com/spdx/tools-python) is licensed under
  Apache-2.0.

For more accurate information, check the individual files.
