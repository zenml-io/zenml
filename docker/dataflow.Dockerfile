FROM apache/beam_python3.7_sdk:2.26.0

WORKDIR /zenml

RUN apt-get update -y && \
  apt-get install --no-install-recommends -y -q software-properties-common && \
  # add-apt-repository ppa:deadsnakes/ppa && \
  # add-apt-repository ppa:maarten-fonville/protobuf && \
  apt-get update -y && \
  apt-get install --no-install-recommends -y -q \
  build-essential \
  ca-certificates \
  libsnappy-dev \
  protobuf-compiler \
  libprotobuf-dev \
  python3.7 \
  python3.7-dev \
  python3-distutils \
  wget \
  unzip \
  git && \
  # add-apt-repository -r ppa:deadsnakes/ppa && \
  # add-apt-repository -r ppa:maarten-fonville/protobuf && \
  # apt-get autoremove --purge python2.7-dev python2.7 libpython2.7 python2.7-minimal \
  # python3.5-dev python3.5 libpython3.5 python3.5-minimal -y && \
  update-alternatives --install /usr/bin/python python /usr/bin/python3.7 1 && \
  update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.7 1 && \
  update-alternatives --install /usr/bin/python-config python-config /usr/bin/python3.7-config 1 && \
  apt-get autoclean && \
  apt-get autoremove --purge && \
  wget https://bootstrap.pypa.io/get-pip.py && python3 get-pip.py && \
  pip install --no-cache-dir --upgrade --pre pip

ADD . /zenml
RUN pip install -e .[all]
