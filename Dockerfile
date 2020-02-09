# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

# Create a base image that has git installed.
FROM python:3.8-slim AS base

RUN apt-get update
RUN apt-get install -y --no-install-recommends git


# Build reuse into a virtualenv
FROM base AS build

WORKDIR /reuse-tool

ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY . /reuse-tool/

RUN pip install -r requirements.txt
RUN pip install .


# Copy over the virtualenv and use it
FROM base
COPY --from=build /opt/venv /opt/venv

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /data

CMD "$VIRTUAL_ENV/bin/reuse" lint
