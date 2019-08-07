<!--
SPDX-FileCopyrightText: 2017-2019 Free Software Foundation Europe e.V.

SPDX-License-Identifier: CC-BY-SA-4.0
-->

# reuse

[![](https://img.shields.io/pypi/l/fsfe-reuse.svg)](https://www.gnu.org/licenses/gpl-3.0.html)
[![](https://img.shields.io/pypi/v/fsfe-reuse.svg)](https://pypi.python.org/pypi/fsfe-reuse)
[![](https://img.shields.io/pypi/pyversions/fsfe-reuse.svg)](https://pypi.python.org/pypi/fsfe-reuse)
[![](https://reuse.software/badge/reuse-compliant.svg)](https://reuse.software/)
[![](https://img.shields.io/badge/readme_style-standard-brightgreen.svg)](https://github.com/RichardLitt/standard-readme)
[![](https://img.shields.io/pypi/status/fsfe-reuse.svg)](https://pypi.python.org/pypi/fsfe-reuse)

> reuse is a tool for compliance with the [REUSE](https://reuse.software/)
> recommendations.

-   Free Software: GPL-3.0-or-later
-   Documentation: <https://reuse.readthedocs.io> and <https://reuse.software>
-   Source code: <https://github.com/fsfe/reuse-tool>
-   PyPI: <https://pypi.python.org/pypi/fsfe-reuse>
-   REUSE: 3.0
-   Python: 3.6+

## Background

Copyright and licensing is difficult, especially when reusing software from
different projects that are released under various different licenses.
[REUSE](https://reuse.software/) was started by the [Free Software Foundation
Europe](https://fsfe.org) (FSFE) to provide a set of recommendations to make
licensing your free software projects easier. Not only do these recommendations
make it easier for you to declare the licenses under which your works are
released, but they also make it easier for a computer to understand how your
project is licensed.

As a short summary, the recommendations are threefold:

1.  Choose and provide licenses
2.  Add copyright and licensing information to each file
3.  Confirm REUSE compliance

You are recommended to read the
[recommendations](https://reuse.software/practices/) in full for more
details. (IMPORTANT FIXME: These recommendations are currently out-of-date!
See <https://github.com/fsfe/reuse-docs>.)

This tool exists to facilitate the developer in complying with the above
recommendations.

There are other tools, such as [FOSSology](https://www.fossology.org/),
that have a lot more features and functionality surrounding the analysis
and inspection of copyright and licenses in software projects. reuse, on
the other hand, is solely designed to be a simple tool to assist in
compliance with the REUSE recommendations.

## Install

To install reuse, you need to have the following pieces of software on
your computer:

-   Python 3.6+
-   Pip

To install reuse, you only need to run the following command:

    pip3 install --user fsfe-reuse

After this, make sure that `~/.local/bin` is in your `$PATH`.

## Usage

First, read the [REUSE
recommendations](https://reuse.software/practices/). In a nutshell:

-   Include the texts of all used licenses in your project.
-   Add a comment header to each file that says
    `SPDX-License-Identifier:
     GPL-3.0-or-later`.
-   Add a comment header to each file that says
    `SPDX-FileCopyrightText: $YEAR $NAME`. You can be flexible with the format,
    just make sure that the line starts with `SPDX-FileCopyrightText:`.

Once you have taken those steps (again, read the actual recommendations
for better instructions), you can use this tool to verify whether your
project is fully compliant with the REUSE recommendations. To check
against the recommendations, use `reuse lint`:

    ~/Projects/reuse-tool $ reuse lint
    [...]

    Congratulations! Your project is compliant with version 3.0 of the REUSE Specification :-)

### Run in Docker

REUSE is simple to include in CI/CD processes. This way, you can check
for REUSE compliance for each build. In our [resources for
developers](https://reuse.software/dev/) you can learn how to integrate
the REUSE tool in Drone, Travis, or GitLab CI.

Within the `fsfe/reuse` Docker image available on [Docker
Hub](https://hub.docker.com/r/fsfe/reuse), you can run the helper tool
simply by executing `reuse lint`. To use the tool on your computer, you can
mount your project directory and run `reuse lint <path/to/directory>`.

## Maintainers

-   Carmen Bianca Bakker - <carmenbianca@fsfe.org>

## Contribute

Any pull requests or suggestions are welcome at
<https://github.com/fsfe/reuse-tool> or via e-mail to one of the maintainers.
General inquiries can be sent to <contact@fsfe.org>.

Starting local development is very simple, just execute the following
commands:

    git clone git@github.com:fsfe/reuse-tool.git
    cd reuse-tool/
    python3 -mvenv venv
    source venv/bin/activate
    make develop

You need to run `make develop` at least once to set up the virtualenv.

Next, run `make help` to see the available interactions.

## License

Copyright (C) 2017-2019 Free Software Foundation Europe e.V.

This work is licensed under multiple licences. Because keeping this section
up-to-date is challenging, here is a brief summary as of July 2019:

- All original source code is licensed under GPL-3.0-or-later.
- All documentation is licensed under CC-BY-SA-4.0.
- Some configuration and data files are licensed under CC0-1.0.
- Some code borrowed from
  [spdx/tool-python](https://github.com/spdx/tools-python) is licensed under
  Apache-2.0.

For more accurate information, check the individual files.
