ARG PYTHON_VERSION=3.11
ARG ZENML_VERSION=""
ARG ZENML_NIGHTLY="false"

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
ARG ZENML_VERSION
ARG ZENML_NIGHTLY="false"

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

# Install common build dependencies
#
# NOTE: System packages required for the build stages should be installed here

FROM builder as client-builder

ARG VIRTUAL_ENV=/opt/venv
ARG ZENML_VERSION
ARG ZENML_NIGHTLY="false"

RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Determine the package name based on ZENML_NIGHTLY
RUN if [ "$ZENML_NIGHTLY" = "true" ]; then \
      PACKAGE_NAME="zenml-nightly"; \
    else \
      PACKAGE_NAME="zenml"; \
    fi \
    && pip install --upgrade pip \
    && pip install ${PACKAGE_NAME}${ZENML_VERSION:+==$ZENML_VERSION} \
    && pip freeze > requirements.txt

FROM builder as server-builder

ARG VIRTUAL_ENV=/opt/venv
ARG ZENML_VERSION
ARG ZENML_NIGHTLY="false"

RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Determine the package name based on ZENML_NIGHTLY
RUN if [ "$ZENML_NIGHTLY" = "true" ]; then \
      PACKAGE_NAME="zenml-nightly"; \
    else \
      PACKAGE_NAME="zenml"; \
    fi \
    && pip install --upgrade pip \
    && pip install "${PACKAGE_NAME}[server,secrets-aws,secrets-gcp,secrets-azure,secrets-hashicorp,s3fs,gcsfs,adlfs,connectors-aws,connectors-gcp,connectors-azure,azureml,sagemaker,vertex]${ZENML_VERSION:+==$ZENML_VERSION}" \
    && pip freeze > requirements.txt

FROM base as client

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
  ZENML_CONTAINER=1

WORKDIR /zenml

# Install client runtime dependencies
#
# NOTE: System packages required by the client at runtime should be installed
# here

# Copy the virtual environment from the builder stage
COPY --from=client-builder /opt/venv /opt/venv
# Copy the requirements.txt file from the builder stage
COPY --from=client-builder /zenml/requirements.txt /zenml/requirements.txt

ENV PATH="$VIRTUAL_ENV/bin:$PATH"

FROM base AS server

ARG VIRTUAL_ENV=/opt/venv
ARG USERNAME=zenml
ARG USER_UID=1000
ARG USER_GID=$USER_UID

ENV \
  # Allow statements and log messages to immediately appear
  PYTHONUNBUFFERED=1 \
  # Enable the fault handler for better stack traces in case of segfaults
  PYTHONFAULTHANDLER=1 \
  # Use a random seed for random number generators
  PYTHONHASHSEED=random \
  # Set environment variable to point to the active virtual env
  VIRTUAL_ENV=$VIRTUAL_ENV \
  # Signal to ZenML that it is running in a container
  ZENML_CONTAINER=1 \
  # Set the ZenML global configuration path
  ZENML_CONFIG_PATH=/zenml/.zenconfig \
  # Set ZenML debug mode to false
  ZENML_DEBUG=false \
  # Enable ZenML server-side analytics
  ZENML_ANALYTICS_OPT_IN=true

WORKDIR /zenml

# Install server runtime dependencies
#
# NOTE: System packages required by the server at runtime should be installed
# here

# Copy the virtual environment from the builder stage
COPY --from=server-builder /opt/venv /opt/venv
# Copy the requirements.txt file from the builder stage
COPY --from=server-builder /zenml/requirements.txt /zenml/requirements.txt

# Create the user and group which will be used to run the ZenML server
# and set the ownership of the workdir directory to the user.
# Create the local stores directory beforehand and ensure it is owned by the
# user.
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && mkdir -p /zenml/.zenconfig/local_stores/default_zen_store \
    && chown -R $USER_UID:$USER_GID /zenml

ENV PATH="$VIRTUAL_ENV/bin:/home/$USERNAME/.local/bin:$PATH"

# Switch to non-privileged user
USER $USERNAME

# Start the ZenML server
EXPOSE 8080
ENTRYPOINT ["uvicorn", "zenml.zen_server.zen_server_api:app", "--log-level", "debug", "--no-server-header", "--proxy-headers", "--forwarded-allow-ips", "*"]
CMD ["--port", "8080", "--host",  "0.0.0.0"]
