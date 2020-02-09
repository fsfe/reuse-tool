# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

FROM alpine:latest

RUN apk --no-cache add python3 git

COPY . /reuse-tool/

WORKDIR /reuse-tool

RUN python3 setup.py install

RUN rm -fr /reuse-tool

WORKDIR /data

CMD ["/usr/bin/reuse", "lint"]
