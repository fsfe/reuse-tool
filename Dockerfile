# SPDX-Copyright: 2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

FROM alpine:latest

# Dependencies for reuse-tool
RUN apk --no-cache add python3 git

# Build dependencies
RUN apk --no-cache --virtual .build-deps add make gcc python3-dev musl-dev

COPY . /reuse-tool/

WORKDIR /reuse-tool/

# Install reuse-tool
RUN python3 -mvenv venv \
    && source venv/bin/activate \
    && make install

# Symlink reuse binary
RUN ln -s /reuse-tool/venv/bin/reuse /usr/local/bin

# Uninstall build dependencies
RUN apk del .build-deps

