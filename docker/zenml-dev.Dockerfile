ARG PYTHON_VERSION=3.11

# Use a minimal base image to reduce the attack surface
FROM python:${PYTHON_VERSION}-slim-bookworm AS base

# Update the system packages to latest versions to reduce vulnerabilities, then
# clean up to reduce the image size
#
# NOTE: System packages required for the build stage should be installed in the
# build stage itself to avoid bloating the final image. Packages required for
# the final image should be installed in the final stage.
RUN set -ex \
  && apt-get update \
  && apt-get upgrade -y \
  && apt-get autoremove -y \
  && apt-get clean -y \
  && rm -rf /var/lib/apt/lists/*

FROM base AS builder

ARG VIRTUAL_ENV=/opt/venv

ENV \
  # Set up virtual environment
  VIRTUAL_ENV=$VIRTUAL_ENV \
  # Set the default timeout for pip to something more reasonable
  # (the default is 15 seconds)
  PIP_DEFAULT_TIMEOUT=100 \
  # Disable a pip version check to reduce run-time & log-spam
  PIP_DISABLE_PIP_VERSION_CHECK=1 \
  # Cache is useless in docker image, so disable to reduce image size
  PIP_NO_CACHE_DIR=1

WORKDIR /zenml

# Install build dependencies
#
# NOTE: System packages required for the build stage should be installed here

RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY README.md pyproject.toml ./

# We first copy the __init__.py file to allow pip install-ing the Python
# dependencies as a separate cache layer. This way, we can avoid re-installing
# the dependencies when the source code changes but the dependencies don't.
COPY src/zenml/__init__.py ./src/zenml/

# Run pip install before copying the source files to install dependencies in
# the virtual environment. Also create a requirements.txt file to keep track of
# dependencies for reproducibility and debugging.
RUN pip install --upgrade pip \
  && pip install . \
  && pip freeze > requirements.txt

# Copy the source code
COPY src src

# Run pip install again to install the source code in the virtual environment
RUN pip install --no-deps --no-cache .

# Inherit from the base image which has the minimal set of updated system
# software packages
FROM base AS final

ARG VIRTUAL_ENV=/opt/venv

ENV \
  # Set the default timeout for pip to something more reasonable
  # (the default is 15 seconds)
  PIP_DEFAULT_TIMEOUT=100 \
  # Disable a pip version check to reduce run-time & log-spam
  PIP_DISABLE_PIP_VERSION_CHECK=1 \
  # Cache is useless in docker image, so disable to reduce image size
  PIP_NO_CACHE_DIR=1 \
  # Allow statements and log messages to be cached.
  #
  # NOTE: this is important for performance reasons. ZenML steps dump their
  # logs into the configured Artifact Store, which can be an external object
  # store. If the logs are not buffered, accessing the external object store
  # for every log message can make the code very slow.
  PYTHONUNBUFFERED=0 \
  # Enable the fault handler for better stack traces in case of segfaults
  PYTHONFAULTHANDLER=1 \
  # Use a random seed for random number generators
  PYTHONHASHSEED=random \
  # Set environment variable to point to the active virtual env
  VIRTUAL_ENV=$VIRTUAL_ENV \
  # Signal to ZenML that it is running in a container
  ZENML_CONTAINER=1 \
  # Set ZenML debug mode to true
  ZENML_DEBUG=true \
  # Set ZenML logging verbosity to INFO
  #
  # NOTE: debug logs can be very verbose and make it in fact more difficult to
  # spot issues during development.
  ZENML_LOGGING_VERBOSITY=INFO \
  # Disable ZenML client-side analytics
  ZENML_ANALYTICS_OPT_IN=false

WORKDIR /zenml

# Install runtime dependencies
#
# NOTE: System packages required at runtime should be installed here

# Install some utilities for debugging and development
RUN set -ex \
  && apt-get update \
  && apt-get install -y curl net-tools nmap inetutils-ping default-mysql-client mariadb-client git \
  && apt-get clean -y \
  && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv
# Copy the requirements.txt file from the builder stage
COPY --from=builder /zenml/requirements.txt /zenml/requirements.txt

ENV PATH="$VIRTUAL_ENV/bin:$PATH"
