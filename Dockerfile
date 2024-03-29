# SPDX-FileCopyrightText: 2019 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2022 Carmen Bianca Bakker <carmenbianca@fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

# Create a base image that has dependencies installed.
FROM alpine:3.18 AS base

RUN apk --no-cache add git mercurial python3 openssh-client

# Build reuse into a virtualenv
FROM base AS build

RUN apk --no-cache add poetry gettext

WORKDIR /reuse-tool
COPY . /reuse-tool/

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN poetry install --no-interaction --no-root --only main
RUN poetry build --no-interaction
RUN pip install dist/*.whl

# Copy over the virtualenv and use it
FROM base
COPY --from=build /opt/venv /opt/venv

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN git config --global --add safe.directory /data
WORKDIR /data

ENTRYPOINT ["reuse"]
CMD ["lint"]
