ARG PYTHON_VERSION=3.11
ARG ZENML_VERSION=latest

# Use the official ZenML image as a base
FROM zenmldocker/zenml:latest as base

# Set user to root for installations
USER root

# Install prerequisites (curl already added) + extras from Modal example
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    dumb-init \
    git \
    git-lfs \
    && rm -rf /var/lib/apt/lists/*

# Define code-server versions/locations (same as Modal example)
ARG CODE_SERVER_INSTALLER="https://code-server.dev/install.sh"
ARG CODE_SERVER_ENTRYPOINT="https://raw.githubusercontent.com/coder/code-server/refs/tags/v4.96.1/ci/release-image/entrypoint.sh"
ARG FIXUD_INSTALLER="https://github.com/boxboat/fixuid/releases/download/v0.6.0/fixuid-0.6.0-linux-$(dpkg --print-architecture).tar.gz"

# Install code-server AND download the specific entrypoint script
RUN curl -fsSL ${CODE_SERVER_INSTALLER} | sh \
    && curl -fsSL ${CODE_SERVER_ENTRYPOINT} -o /code-server.sh \
    && chmod u+x /code-server.sh

# Install fixuid (mimicking Modal example's run_commands)
# Note: Using $(dpkg --print-architecture) directly in ARG might not work as expected during build-arg expansion.
# We embed it in the RUN command instead.
RUN ARCH="$(dpkg --print-architecture)" \
    && curl -fsSL "https://github.com/boxboat/fixuid/releases/download/v0.6.0/fixuid-0.6.0-linux-${ARCH}.tar.gz" | tar -C /usr/local/bin -xzf - \
    && chown root:root /usr/local/bin/fixuid \
    && chmod 4755 /usr/local/bin/fixuid \
    && mkdir -p /etc/fixuid \
    && echo "user: root" >> /etc/fixuid/config.yml \
    && echo "group: root" >> /etc/fixuid/config.yml

# Ensure /usr/local/bin (common install location) is in PATH
ENV PATH="/usr/local/bin:${PATH}"

# Create /home/coder directory (as in Modal example)
RUN mkdir -p /home/coder
# Optional: Set ownership if needed, depends on base image and desired execution user
# RUN chown someuser:somegroup /home/coder

# Set environment variables (as in Modal example)
ENV ENTRYPOINTD=""

# Default working directory from base image is likely /app
WORKDIR /app

# Expose the default code-server port (optional, for documentation)
EXPOSE 8080

# Default command - using dumb-init is often good practice with containers
CMD ["dumb-init", "--", "/bin/bash"] 