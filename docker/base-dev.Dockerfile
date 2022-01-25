FROM ubuntu:20.04

WORKDIR /zenml

# python
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

# copy project requirement files here to ensure they will be cached.
COPY pyproject.toml /zenml

ENV ZENML_DEBUG=true
ENV ZENML_ANALYTICS_OPT_IN=false
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$POETRY_HOME/bin:$PATH"
RUN python -m venv $VIRTUAL_ENV

RUN pip install --no-cache-dir --upgrade --pre pip

# install dependencies but don't install zenml yet
# this improves caching as the dependencies don't have to be reinstalled everytime a src file changes
RUN poetry install --no-root

COPY . /zenml

# install zenml
RUN poetry update && poetry install
