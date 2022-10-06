# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2022 Carmen Bianca Bakker <carmenbianca@fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

# Create a base image that has dependencies installed.
FROM alpine:3.13 AS base

RUN apk --no-cache add git mercurial python3 py3-pip

# Build reuse into a virtualenv
FROM base AS build

WORKDIR /reuse-tool

COPY . /reuse-tool/

RUN pip3 install "poetry>=1.2"
RUN poetry config virtualenvs.create false \
  && poetry install --without dev --no-interaction --no-ansi

WORKDIR /data

ENTRYPOINT ["reuse"]
CMD ["lint"]
