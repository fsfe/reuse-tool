=====
reuse
=====

reuse is a tool for compliance with the `REUSE Project
<https://reuse.software/>`_ recommendations.

- Free Software: GPL-3.0+

- Documentation: https://reuse.gitlab.io

- Source code: https://git.fsfe.org/reuse/reuse

- PyPI: https://pypi.python.org/pypi/fsfe-reuse

- Python: 3.5+

Install
-------

To install reuse, make sure that you have Python >=3.5 and Pip installed, then
run the following command::

    pip3 install --user fsfe-reuse

Usage
-----

To check your project for REUSE compliance, use ``reuse lint``::

    ~/Projects/curl$ reuse lint
    .gitattributes
    README
    docs/libcurl/CMakeLists.txt
    lib/.gitattributes
    [...]

All the listed files have no licence information associated with them.

Maintainers
-----------

- Carmen Bianca Bakker <carmenbianca at fsfe dot org>

- Jonas Öberg <jonas at fsfe dot org>

License
-------

Copyright (C) 2017 Free Software Foundation Europe e.V.

Licensed under the GNU General Public License version 3 or later.
