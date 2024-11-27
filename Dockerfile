# Secret management
FROM segment/chamber:2 AS chamber

# Build the reqired dependecies
FROM python:3.11 AS builder

# Creates a standalone environment in /opt/venv
RUN pip install poetry==1.8.2

WORKDIR /opt/venv

COPY pyproject.toml poetry.lock ./
RUN touch README.md

# This installs the python dependencies into /opt/venv
RUN python -m venv /opt/venv && \
    poetry export --with dev,tests -f requirements.txt --output requirements.txt && \
    /opt/venv/bin/pip install -r requirements.txt

# Container for running the project
# This isn't a hyper optimised container but it's a good starting point
FROM python:3.11

# These will be overwritten in GHA due to https://github.com/docker/metadata-action/issues/295
# These must be duplicated in .github/workflows/build_docker.yaml
LABEL org.opencontainers.image.title="Open Methane Prior Emissions"
LABEL org.opencontainers.image.description="Method to calculate a gridded, prior emissions estimate for methane across Australia."
LABEL org.opencontainers.image.authors="Peter Rayner <peter.rayner@superpowerinstitute.com.au>, Jared Lewis <jared.lewis@climate-resource.com>"
LABEL org.opencontainers.image.vendor="The Superpower Institute"

# OPENMETHANE_PRIOR_VERSION will be overridden in release builds with semver vX.Y.Z
ARG OPENMETHANE_PRIOR_VERSION=development
# Make the $OPENMETHANE_PRIOR_VERSION available as an env var inside the container
ENV OPENMETHANE_PRIOR_VERSION=$OPENMETHANE_PRIOR_VERSION

LABEL org.opencontainers.image.version="${OPENMETHANE_PRIOR_VERSION}"

# Configure Python
ENV PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random

# This is deliberately outside of the work directory
# so that the local directory can be mounted as a volume of testing
ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    LD_LIBRARY_PATH="/opt/venv/lib:$LD_LIBRARY_PATH"

WORKDIR /opt/project

# Install additional apt dependencies
#RUN apt-get update && \
#    apt-get install -y csh bc file make wget && \
#    rm -rf /var/lib/apt/lists/*

# Secret management
COPY --from=chamber /chamber /bin/chamber

# Copy across the virtual environment
COPY --from=builder /opt/venv /opt/venv

# Copy in the rest of the project
# For testing it might be easier to mount $(PWD):/opt/project so that local changes are reflected in the container
COPY . /opt/project

# Install the local package in editable mode
RUN pip install -e .

CMD ["/bin/bash"]