ARG TENSORFLOW_VERSION=2.3.0
FROM tensorflow/tensorflow:${TENSORFLOW_VERSION}-gpu
ARG TENSORFLOW_VERSION

WORKDIR /zenml

RUN apt-get update -y && \
  apt-get install --no-install-recommends -y -q  \
  build-essential \
  libsnappy-dev \
  protobuf-compiler \
  libprotobuf-dev \
  python3-virtualenv \
  wget \
  git && \
  apt-get autoclean && \
  apt-get autoremove --purge && \
  CFLAGS=$(/usr/bin/python3.6-config --cflags) python3.6 -m pip install --no-cache-dir  \
    "tensorflow-gpu==${TENSORFLOW_VERSION}"

ADD . /zenml
RUN pip install -e .[all]