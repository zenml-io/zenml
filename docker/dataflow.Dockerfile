FROM apache/beam_python3.7_sdk:2.26.0

# python
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

RUN apt-get update && \
  apt-get install --no-install-recommends -q -y software-properties-common && \
  apt-get update && \
  apt-get install --no-install-recommends -q -y \
  build-essential \
  ca-certificates \
  libsnappy-dev \
  protobuf-compiler \
  libprotobuf-dev \
  wget \
  unzip \
  git && \
  apt-get autoclean && \
  apt-get autoremove --purge && \
  wget https://bootstrap.pypa.io/get-pip.py && python3 get-pip.py && \
  pip install --no-cache-dir --upgrade --pre pip

ARG ZENML_VERSION
# install the given zenml version (default to latest)
RUN pip install --no-cache-dir zenml${ZENML_VERSION:+==$ZENML_VERSION}
