FROM ubuntu:18.04

WORKDIR /zenml

# python
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    POETRY_HOME=/root/.local

ENV ZENML_DEBUG=true
ENV ZENML_ANALYTICS_OPT_IN=false
ENV PATH="$POETRY_HOME/bin:$PATH"

RUN apt-get update && \
  apt-get install --no-install-recommends -q -y software-properties-common && \
  add-apt-repository ppa:deadsnakes/ppa && \
  add-apt-repository ppa:maarten-fonville/protobuf && \
  apt-get update && \
  apt-get install --no-install-recommends -q -y \
  build-essential \
  ca-certificates \
  libsnappy-dev \
  protobuf-compiler \
  libprotobuf-dev \
  python3.7-dev \
  python3.7-venv \
  wget \
  unzip \
  git && \
  add-apt-repository -r ppa:deadsnakes/ppa && \
  add-apt-repository -r ppa:maarten-fonville/protobuf && \
  update-alternatives --install /usr/bin/python python /usr/bin/python3.7 1 && \
  update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.7 1 && \
  update-alternatives --install /usr/bin/python-config python-config /usr/bin/python3.7-config 1 && \
  apt-get autoclean && \
  apt-get autoremove --purge && \
  wget https://bootstrap.pypa.io/get-pip.py && python3 get-pip.py && \
  pip install --no-cache-dir --upgrade --pre pip && \
  wget https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py && \
  python install-poetry.py

# copy project requirement files here to ensure they will be cached.
COPY pyproject.toml /zenml

# don't create a virtualenv for dependencies
RUN poetry config virtualenvs.create false

# install dependencies but don't install zenml yet
# this improves caching as the dependencies don't have to be reinstalled everytime a src file changes
RUN poetry install --no-root

# create an alias for zenml
RUN echo 'alias zenml="poetry run zenml"' >> ~/.bashrc

COPY . /zenml

# install zenml
RUN poetry update && poetry install
