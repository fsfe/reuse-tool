# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

FROM alpine:latest

# Dependencies for reuse-tool
RUN apk --no-cache add python3 git

COPY . /reuse-tool/

# Install reuse-tool
RUN cd /reuse-tool \
    && python3 setup.py install \
    && rm -rf /reuse-tool
