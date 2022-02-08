ARG TENSORFLOW_VERSION=2.6.1
FROM tensorflow/tensorflow:${TENSORFLOW_VERSION}-gpu

# python
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on


RUN apt-get update && \
  apt-get install --no-install-recommends -q -y \
  build-essential \
  ca-certificates \
  libsnappy-dev \
  protobuf-compiler \
  libprotobuf-dev \
  python3 \
  python3-dev \
  python3-venv \
  python3-pip \
  curl \
  unzip \
  git && \
  apt-get autoclean && \
  apt-get autoremove --purge

RUN curl -sSL https://bootstrap.pypa.io/get-pip.py | python && \
  pip install --no-cache-dir --upgrade --pre pip

ARG ZENML_VERSION
# install the given zenml version (default to latest)
RUN pip install --no-cache-dir zenml${ZENML_VERSION:+==$ZENML_VERSION}
