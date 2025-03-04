ARG PYTHON_VERSION=3.11
ARG VIRTUAL_ENV=/opt/venv
ARG USERNAME=zenml
ARG USER_UID=1000
ARG USER_GID=1000
ARG INSTALL_DEBUG_TOOLS=false

# Use a minimal base image to reduce the attack surface
FROM python:${PYTHON_VERSION}-slim-bookworm AS base

# Redeclaring ARGs because Docker is not smart enough to inherit them from the
# global scope
ARG VIRTUAL_ENV
ARG USERNAME
ARG USER_UID
ARG USER_GID
ARG INSTALL_DEBUG_TOOLS

# Update the system packages to latest versions to reduce vulnerabilities, then
# clean up to reduce the image size.
#
# Install some utilities for debugging and development only if
# INSTALL_DEBUG_TOOLS is true.
RUN set -ex && \
  apt-get update && \
  apt-get upgrade -y && \
  if [ "$INSTALL_DEBUG_TOOLS" = "true" ]; then \
    apt-get install -y curl net-tools nmap inetutils-ping default-mysql-client mariadb-client git ; \
  fi && \
  apt-get autoremove -y && \
  apt-get clean -y && \
  rm -rf /var/lib/apt/lists/*

# Create the user and group which will be used to run the ZenML server.
RUN groupadd --gid $USER_GID $USERNAME && \
  useradd --uid $USER_UID --gid $USER_GID -m $USERNAME && \
  mkdir -p $VIRTUAL_ENV && \
  chown -R $USER_UID:$USER_GID $VIRTUAL_ENV

WORKDIR /zenml

RUN chown -R $USER_UID:$USER_GID .

# Switch to non-privileged user
USER $USERNAME

ENV PATH="$VIRTUAL_ENV/bin:/home/$USERNAME/.local/bin:$PATH"

FROM base AS builder

# Redeclaring ARGs because Docker is not smart enough to inherit them from the
# global scope
ARG VIRTUAL_ENV
ARG USERNAME
ARG USER_UID
ARG USER_GID

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

# Install build dependencies
#
# NOTE: System packages required for the build stage should be installed here

RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY --chown=$USERNAME:$USER_GID  README.md pyproject.toml ./

# We first copy the __init__.py file to allow pip install-ing the Python
# dependencies as a separate cache layer. This way, we can avoid re-installing
# the dependencies when the source code changes but the dependencies don't.
COPY --chown=$USERNAME:$USER_GID src/zenml/__init__.py ./src/zenml/

# Run pip install before copying the source files to install dependencies in
# the virtual environment. Also create a requirements.txt file to keep track of
# dependencies for reproducibility and debugging.
# NOTE: we uninstall zenml at the end because we install it separately in the
# final stage
RUN pip install --upgrade pip \
    && pip install uv \
    && uv pip install .[server,secrets-aws,secrets-gcp,secrets-azure,secrets-hashicorp,s3fs,gcsfs,adlfs,connectors-aws,connectors-gcp,connectors-azure,azureml,sagemaker,vertex] \
    && uv pip uninstall zenml \
    && uv pip freeze > requirements.txt

# Inherit from the base image which has the minimal set of updated system
# software packages
FROM base AS common-runtime

# Redeclaring ARGs because Docker is not smart enough to inherit them from the
# global scope
ARG VIRTUAL_ENV
ARG USERNAME
ARG USER_UID
ARG USER_GID

ENV \
  # Allow statements and log messages to immediately appear
  PYTHONUNBUFFERED=1 \
  # Enable the fault handler for better stack traces in case of segfaults
  PYTHONFAULTHANDLER=1 \
  # Use a random seed for random number generators
  PYTHONHASHSEED=random \
  # Set environment variable to point to the active virtual env
  VIRTUAL_ENV=$VIRTUAL_ENV \
  # Set the ZenML global configuration path
  ZENML_CONFIG_PATH=/zenml/.zenconfig \
  # Signal to ZenML that it is running in a container
  ZENML_CONTAINER=1 \
  # Set ZenML debug mode to true
  ZENML_DEBUG=true \
  # Set ZenML logging verbosity to DEBUG
  ZENML_LOGGING_VERBOSITY=DEBUG \
  # Disable ZenML server-side analytics
  ZENML_ANALYTICS_OPT_IN=false \
  # Enable ZenML server rate limiting for the authentication endpoint
  ZENML_SERVER_RATE_LIMIT_ENABLED=1 \
  # Set the ZenML server login rate limit to 100 requests per minute
  ZENML_SERVER_LOGIN_RATE_LIMIT_MINUTE=100

# Install runtime dependencies
#
# NOTE: System packages required at runtime should be installed here

# Copy the virtual environment with all dependencies
COPY --chown=$USERNAME:$USER_GID --from=builder /opt/venv /opt/venv
# Copy the requirements.txt file from the builder stage
COPY --chown=$USERNAME:$USER_GID --from=builder /zenml/requirements.txt /zenml/requirements.txt

# Copy source code
COPY --chown=$USERNAME:$USER_GID README.md pyproject.toml ./
COPY --chown=$USERNAME:$USER_GID src src

FROM common-runtime AS local-runtime

# Run pip install again to install the source code in the virtual environment
# in editable mode
RUN pip install --no-deps --no-cache -e .[server,secrets-aws,secrets-gcp,secrets-azure,secrets-hashicorp,s3fs,gcsfs,adlfs,connectors-aws,connectors-gcp,connectors-azure,azureml,sagemaker,vertex]

EXPOSE 8080

ENTRYPOINT ["uvicorn", "zenml.zen_server.zen_server_api:app", "--log-level", "debug", "--no-server-header", "--proxy-headers", "--forwarded-allow-ips", "*", "--reload"]
CMD ["--port", "8080", "--host",  "0.0.0.0"]


FROM common-runtime AS runtime

# Run pip install again to install the source code in the virtual environment
# and then remove the sources
RUN pip install --no-deps --no-cache .[server,secrets-aws,secrets-gcp,secrets-azure,secrets-hashicorp,s3fs,gcsfs,adlfs,connectors-aws,connectors-gcp,connectors-azure,azureml,sagemaker,vertex] \
    && rm -rf src README.md pyproject.toml

EXPOSE 8080

ENTRYPOINT ["uvicorn", "zenml.zen_server.zen_server_api:app", "--log-level", "debug", "--no-server-header", "--proxy-headers", "--forwarded-allow-ips", "*"]
CMD ["--port", "8080", "--host",  "0.0.0.0"]
