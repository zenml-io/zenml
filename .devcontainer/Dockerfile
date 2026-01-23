# ZenML Dev Container Dockerfile
# Mirrors the Ubuntu CI environment for local debugging of CI failures
#
# This Dockerfile is used by all devcontainer configurations (Python 3.10-3.13).
# It installs system dependencies needed for CI parity but does NOT install
# ZenML Python packages - those are installed via postCreateCommand to match
# the CI workflow exactly.

ARG PYTHON_VERSION=3.11

FROM python:${PYTHON_VERSION}-slim-bookworm

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies that mirror what's available on GitHub Actions runners
# and what's needed to build Python packages with native extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Essential build tools (needed for many Python packages)
    build-essential \
    pkg-config \
    # Version control (required for ZenML and many integrations)
    git \
    # Network tools (useful for debugging and required by some integrations)
    curl \
    wget \
    ca-certificates \
    # Common native library headers for Python packages
    libffi-dev \
    libssl-dev \
    # MySQL/MariaDB client libraries (for database integration tests)
    default-libmysqlclient-dev \
    default-mysql-client \
    mariadb-client \
    # PostgreSQL client (for database integration tests)
    libpq-dev \
    postgresql-client \
    # Graphviz (installed in CI integration-test-fast.yml)
    graphviz \
    # Useful debugging tools
    procps \
    htop \
    less \
    vim-tiny \
    # Required for some ML libraries
    libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install uv (the package manager used by CI)
# This matches the pattern used in scripts/install-zenml-dev.sh
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Configure git (matches CI setup in .github/actions/setup_environment/action.yml)
RUN git config --global user.email "info@zenml.io" \
    && git config --global user.name "ZenML GmbH" \
    && git config --global --add safe.directory /workspaces/zenml

# Install Terraform (matches CI setup for Ubuntu)
RUN curl -fsSL https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com bookworm main" \
    | tee /etc/apt/sources.list.d/hashicorp.list \
    && apt-get update \
    && apt-get install -y terraform \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create cache directory for uv with proper permissions
RUN mkdir -p /root/.cache/uv

# Set the working directory
WORKDIR /workspaces/zenml

# Default command (overridden by devcontainer)
CMD ["bash"]
