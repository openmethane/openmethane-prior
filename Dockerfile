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
    poetry export --with "dev tests" -f requirements.txt --output requirements.txt && \
    /opt/venv/bin/pip install -r requirements.txt

# Container for running the project
# This isn't a hyper optimised container but it's a good starting point
FROM python:3.11

LABEL org.opencontainers.image.authors="jared.lewis@climate-resource.com"

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