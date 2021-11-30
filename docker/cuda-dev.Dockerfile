ARG TENSORFLOW_VERSION=2.6.0
FROM tensorflow/tensorflow:${TENSORFLOW_VERSION}-gpu
ARG TENSORFLOW_VERSION

WORKDIR /zenml

# python
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

ENV ZENML_DEBUG=true
ENV ZENML_ANALYTICS_OPT_IN=false
ENV POETRY_HOME="/usr/local/poetry"
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
  python3.6-venv \
  wget \
  unzip \
  git && \
  add-apt-repository -r ppa:deadsnakes/ppa && \
  add-apt-repository -r ppa:maarten-fonville/protobuf && \
  apt-get autoclean && \
  apt-get autoremove --purge && \
  wget https://bootstrap.pypa.io/get-pip.py && python3 get-pip.py && \
  pip install --no-cache-dir --upgrade --pre pip && \
  wget https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py && \
  python3 install-poetry.py


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
