FROM ubuntu:20.04

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    POETRY_HOME=/root/.local

RUN apt-get update && \
  apt-get install --no-install-recommends -q -y \
  build-essential \
  ca-certificates \
  libsnappy-dev \
  protobuf-compiler \
  libprotobuf-dev \
  python3 \
  python3-dev \
  python-is-python3 \
  python3-venv \
  python3-pip \
  curl \
  unzip \
  git && \
  apt-get autoclean && \
  apt-get autoremove --purge

RUN curl -sSL https://install.python-poetry.org | python
RUN pip install --no-cache-dir --upgrade --pre pip

ENV ZENML_DEBUG=true
ENV ZENML_ANALYTICS_OPT_IN=false
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$POETRY_HOME/bin:$PATH"
RUN python -m venv $VIRTUAL_ENV

WORKDIR /zenml

# Copy all necessary files for the installation
COPY README.md pyproject.toml poetry.lock* ./
# The existence of this __init__.py file allows the poetry install before actually 
# copying our source files which would invalidate caching
COPY src/zenml/__init__.py ./src/zenml/

RUN poetry install

COPY src src
