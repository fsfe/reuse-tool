<!--
SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>

SPDX-License-Identifier: CC-BY-SA-4.0
-->

# reuse

[![The latest version of reuse can be found on PyPI.](https://img.shields.io/pypi/v/reuse.svg)](https://pypi.python.org/pypi/reuse)
[![Information on what versions of Python reuse supports can be found on PyPI.](https://img.shields.io/pypi/pyversions/reuse.svg)](https://pypi.python.org/pypi/reuse)
[![REUSE status](https://api.reuse.software/badge/github.com/fsfe/reuse-tool)](https://api.reuse.software/info/github.com/fsfe/reuse-tool)
[![readme style standard](https://img.shields.io/badge/readme_style-standard-brightgreen.svg)](https://github.com/RichardLitt/standard-readme)
[![Packaging status](https://repology.org/badge/tiny-repos/reuse.svg?header=in%20distro%20repos)](https://repology.org/project/reuse/versions)

> reuse is a tool for compliance with the [REUSE](https://reuse.software/)
> recommendations.

- Documentation: <https://reuse.readthedocs.io> and <https://reuse.software>
- Source code: <https://github.com/fsfe/reuse-tool>
- PyPI: <https://pypi.python.org/pypi/reuse>
- REUSE: 3.0
- Python: 3.6+

## Background

Copyright and licensing is difficult, especially when reusing software from
different projects that are released under various different licenses.
[REUSE](https://reuse.software) was started by the
[Free Software Foundation Europe](https://fsfe.org) (FSFE) to provide a set of
recommendations to make licensing your Free Software projects easier. Not only
do these recommendations make it easier for you to declare the licenses under
which your works are released, but they also make it easier for a computer to
understand how your project is licensed.

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

## Example demo

In this screencast, we are going to follow the
[tutorial](https://reuse.software/tutorial), making the
[REUSE example repository](https://github.com/fsfe/reuse-example/) compliant.

![Demo of some basic REUSE tool commands](https://download.fsfe.org/videos/reuse/screencasts/reuse-tool.gif)

## Install

### Installation via package managers (Recommended)

There are packages available for easy install on some operating systems. You are
welcome to help us package this tool for more distributions!

- Alpine Linux: [reuse](https://pkgs.alpinelinux.org/packages?name=reuse)
- Arch Linux: [reuse](https://archlinux.org/packages/community/any/reuse/)
- Debian: [reuse](https://packages.debian.org/search?keywords=reuse&exact=1)
- GNU Guix: [reuse](https://guix.gnu.org/en/packages/reuse-1.0.0/)
- Fedora: [reuse](https://packages.fedoraproject.org/pkgs/reuse/reuse/)
- MacPorts: [reuse](https://ports.macports.org/port/reuse/)
- NixOS: [reuse](https://search.nixos.org/packages?show=reuse)
- openSUSE: [reuse](https://software.opensuse.org/package/reuse)
- VoidLinux: [reuse](https://voidlinux.org/packages/?arch=x86_64&q=reuse)

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

### Installation via pip

To install reuse, you need to have the following pieces of software on your
computer:

- Python 3.6+
- pip

You then only need to run the following command:

```bash
pip3 install --user reuse
```

After this, make sure that `~/.local/bin` is in your `$PATH`. On Windows, the
required path for your environment may look like
`%USERPROFILE%\AppData\Roaming\Python\Python39\Scripts`, depending on the Python
version you have installed.

To update reuse, run this command:

```bash
pip3 install --user --upgrade reuse
```

For full functionality, the following pieces of software are recommended:

- Git
- Mercurial 4.3+

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

To check against the recommendations, use `reuse lint`:

```
~/Projects/reuse-tool $ reuse lint
[...]

Congratulations! Your project is compliant with version 3.0 of the REUSE Specification :-)
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

There are a number of tags available:

- `latest` is the most recent stable release.
- `dev` follows the `main` branch of this repository. Up-to-date, but
  potentially unstable.
- `latest-extra` has a few extra packages installed, currently `openssh-client`.
- `latest-debian` is based on `python:slim`. It is larger, but may be better
  suited for license compliance.

### Run as pre-commit hook

You can automatically run `reuse lint` on every commit as a pre-commit hook for
Git. This uses [pre-commit](https://pre-commit.com/). Once you
[have it installed](https://pre-commit.com/#install), add this to the
`.pre-commit-config.yaml` in your repository:

```yaml
repos:
  - repo: https://github.com/fsfe/reuse-tool
    rev: v1.1.1
    hooks:
      - id: reuse
```

Then run `pre-commit install`. Now, every time you commit, `reuse lint` is run
in the background, and will prevent your commit from going through if there was
an error.

## Maintainers

- Carmen Bianca Bakker - <carmenbianca@fsfe.org>
- Max Mehl - <max.mehl@fsfe.org>

## Contribute

Any pull requests or suggestions are welcome at
<https://github.com/fsfe/reuse-tool> or via e-mail to one of the maintainers.
General inquiries can be sent to <reuse@lists.fsfe.org>.

Interaction within this project is covered by the
[FSFE's Code of Conduct](https://fsfe.org/about/codeofconduct).

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

## License

This work is licensed under multiple licences. Because keeping this section
up-to-date is challenging, here is a brief summary as of April 2020:

- All original source code is licensed under GPL-3.0-or-later.
- All documentation is licensed under CC-BY-SA-4.0.
- Some configuration and data files are licensed under CC0-1.0.
- Some code borrowed from
  [spdx/tool-python](https://github.com/spdx/tools-python) is licensed under
  Apache-2.0.

For more accurate information, check the individual files.
