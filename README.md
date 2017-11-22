# reuse

[![PyPI](https://img.shields.io/pypi/l/fsfe-reuse.svg)](https://www.gnu.org/licenses/gpl-3.0.html)
[![PyPI](https://img.shields.io/pypi/v/fsfe-reuse.svg)](https://pypi.python.org/pypi/fsfe-reuse)
[![PyPI](https://img.shields.io/pypi/pyversions/fsfe-reuse.svg)](https://pypi.python.org/pypi/fsfe-reuse)
[![reuse compliant](https://reuse.software/badge/reuse-compliant.svg)](https://reuse.software/)
[![standard-readme compliant](https://img.shields.io/badge/readme_style-standard-brightgreen.svg)](https://github.com/RichardLitt/standard-readme)
[![PyPI](https://img.shields.io/pypi/status/fsfe-reuse.svg)](https://pypi.python.org/pypi/fsfe-reuse)

> reuse is a tool for compliance with the [REUSE
> Initiative](https://reuse.software/) recommendations.

- Free Software: GPL-3.0+

- Documentation: <https://reuse.gitlab.io>

- Source code: <https://git.fsfe.org/reuse/reuse>

- PyPI: <https://pypi.python.org/pypi/fsfe-reuse>

- Python: 3.5+

## Background

Copyright and licensing is difficult, especially when reusing software from
different projects that are released under various different licenses.  The
[REUSE Initiative](https://reuse.software/) was started by the
[FSFE](https://fsfe.org) to provide a set of recommendations to make licensing
your free software projects easier.  Not only do these recommendations make it
easier for you to declare the licenses under which your works are released, but
they also make it easier for a computer to understand how your project is
licensed.

As a short summary, the recommendations are threefold:

1. Provide the exact text of each license used, verbatim.

2. Include a copyright notice and license in (or about) each file.

3. Provide an inventory for included software.

You are recommended to read the
[recommendations](https://reuse.software/practices/) in full for more details.

This tool exists to facilitate the developer in complying to the above
recommendations.  It will serve as a linter for compliance, and as a compiler
for generating the bill of materials.

There are other tools, such as [FOSSology](https://www.fossology.org/), that
have a lot more features and functionality surrounding the analysis and
inspection of copyright and licenses in software projects.  reuse, on the other
hand, is solely designed to be a simple tool to assist in compliance with the
REUSE Initiative recommendations.

## Install

To install reuse, make sure that you have Python >=3.5 and Pip installed, then
run the following command::

    pip3 install --user fsfe-reuse

## Usage

To check your project for REUSE compliance, use `reuse lint`:

    ~/Projects/curl$ reuse lint
    .gitattributes
    README
    docs/libcurl/CMakeLists.txt
    lib/.gitattributes
    [...]

All the listed files have no licence information associated with them.

To generate a bill of materials, use `reuse compile`:

    ~/Projects/curll$ reuse compile
    SPDXVersion: SPDX-2.1
    DataLicense: CC0-1.0
    SPDXID: SPDXRef-DOCUMENT
    DocumentName: curl
    DocumentNamespace: http://spdx.org/spdxdocs/spdx-v2.1-c8c7047c-855c-45a6-bed0-c23900498a79
    Creator: Person: Anonymous ()
    Creator: Organization: Anonymous ()
    Creator: Tool: reuse-0.0.4
    Created: 2017-11-15T11:42:28Z
    CreatorComment: <text>This document was created automatically using available reuse information consistent with the REUSE Initiative.</text>
    [...]

Ideally, you would distribute this bill of materials together with the tarfile
distribution of your project.

Make sure that, when outputting to a file, that this file ends in the `.spdx`
extension.  If you do not do this, the tool will attempt to include the file
itself into the bill of materials, which obviously will not work.

## Maintainers

- Carmen Bianca Bakker - carmenbianca at fsfe dot org

- Jonas Öberg - jonas at fsfe dot org

## Contribute

Any pull requests or suggestions are welcome at
<https://git.fsfe.org/reuse/reuse> or via e-mail to one of the maintainers.
General inquiries can be sent to <contact@fsfe.org>.

Starting local development is very simple, just execute the following commands:

    git clone git@git.fsfe.org:reuse/reuse.git
    cd reuse/
    python3 -mvenv venv
    source venv/bin/activate
    make develop

You need to run `make develop` at least once to set up the virtualenv.

Next, run `make help` to see the available interactions.

## License

Copyright (C) 2017 Free Software Foundation Europe e.V.

Licensed under the GNU General Public License version 3 or later.
