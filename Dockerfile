# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

# Create a base image that has dependencies installed.
FROM alpine:3.11 AS base

RUN apk --no-cache add git mercurial python3

# Build reuse into a virtualenv
FROM base AS build

WORKDIR /reuse-tool

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY . /reuse-tool/

RUN pip3 install -r requirements.txt
RUN pip3 install .


# Copy over the virtualenv and use it
FROM base
COPY --from=build /opt/venv /opt/venv

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /data

ENTRYPOINT ["reuse"]
CMD ["lint"]
