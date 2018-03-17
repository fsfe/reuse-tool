# reuse

[![license](https://img.shields.io/pypi/l/fsfe-reuse.svg)](https://www.gnu.org/licenses/gpl-3.0.html)
[![version](https://img.shields.io/pypi/v/fsfe-reuse.svg)](https://pypi.python.org/pypi/fsfe-reuse)
[![python](https://img.shields.io/pypi/pyversions/fsfe-reuse.svg)](https://pypi.python.org/pypi/fsfe-reuse)
[![reuse](https://reuse.software/badge/reuse-compliant.svg)](https://reuse.software/)
[![standard-readme](https://img.shields.io/badge/readme_style-standard-brightgreen.svg)](https://github.com/RichardLitt/standard-readme)
[![status](https://img.shields.io/pypi/status/fsfe-reuse.svg)](https://pypi.python.org/pypi/fsfe-reuse)

> reuse is a tool for compliance with the [REUSE
> Initiative](https://reuse.software/) recommendations.

- Free Software: GPL-3.0-or-later

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

To install reuse, you need to have the following pieces of software on your
computer:

- Python 3.5+

- Pip

- `python3-pygit2`

You can install `python3-pygit2` via your operating system's package
manager. For Debian-like GNU/Linux distributions this would be:

    apt-get install python3-pygit2

Note that simply installing `pygit2` via `pip` does not work as this omits
the `libgit2` dependency.

You can also use reuse without `python3-pygit2` at the cost of significantly
degraded performance as the amount of files to process increases.

To install reuse, you only need to run the following command:

    pip3 install --user fsfe-reuse

After this, make sure that `~/.local/bin` is in your `$PATH`.

## Usage

First, read the [REUSE recommendations](https://reuse.software/practices/).  In
a nutshell:

- Include the texts of all used licenses in your project.

  - A special note on the GPL: If you use `Valid-License-Identifier: GPL-3.0` or
    name the file `LICENSES/GPL-3.0.txt`, this will catch all the following
    licenses: `GPL-3.0`, `GPL-3.0+`, `GPL-3.0-only` and `GPL-3.0-or-later`.
    This applies to the entire GPL family of licenses.

- Add a comment header to each file that says `SPDX-License-Identifier:
  GPL-3.0-or-later`.  Replace `GPL-3.0-or-later` with the license that applies
  to the file.  If you cannot edit the comment header, include a
  [debian/copyright](https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/)
  file.

- Add a comment header to each file that says `Copyright (C) YEAR  NAME`.  You
  can be flexible with the format, just make sure that the line starts with
  `Copyright`.  You can add multiple lines.

Once you have taken those steps (again, read the actual recommendations for
better instructions), you can use this tool to verify whether your project is
fully compliant with the REUSE recommendations.  To check against the
recommendations, use `reuse lint`:

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

Make sure that, when outputting to a file, this file ends in the `.spdx`
extension.  If you do not do this, the tool will attempt to include the file
itself into the bill of materials, which obviously will not work.

## Maintainers

- Carmen Bianca Bakker - <carmenbianca@fsfe.org>

- Jonas Öberg - <jonas@fsfe.org>

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
