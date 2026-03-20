FROM python:3.12-slim-bookworm

RUN set -ex \
  && apt-get update \
  && apt-get install -y --no-install-recommends \
    git curl build-essential graphviz \
  && apt-get clean -y \
  && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip uv setuptools wheel

WORKDIR /app

# Copy project files needed for installation
COPY pyproject.toml README.md /app/
COPY src/ /app/src/
COPY scripts/install-zenml-dev.sh /app/scripts/

# Install ZenML (editable) + all integration dependencies.
# Integration packages land in system site-packages and persist
# across runs. The editable install points to /app/src/zenml/,
# which gets overlaid by the fresh CWD mount at runtime.
RUN scripts/install-zenml-dev.sh --system --integrations yes

# Clean up source files that will be replaced by the CWD mount
RUN rm -rf /app/src /app/scripts /app/pyproject.toml /app/README.md
