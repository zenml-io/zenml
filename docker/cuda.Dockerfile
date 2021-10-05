ARG TENSORFLOW_VERSION=2.3.0
FROM tensorflow/tensorflow:${TENSORFLOW_VERSION}-gpu
ARG TENSORFLOW_VERSION

WORKDIR /zenml

# python
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    POETRY_VERSION=1.0.3 \
    POETRY_HOME=/root/.local

# prepend poetry and venv to path
ENV PATH="$POETRY_HOME/bin:$PATH"

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
    "tensorflow-gpu==${TENSORFLOW_VERSION}" && \
  wget https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py && python install-poetry.py


# copy project requirement files here to ensure they will be cached.
COPY pyproject.toml /zenml

# install runtime deps - uses $POETRY_VIRTUALENVS_IN_PROJECT internally
RUN poetry config virtualenvs.create false && poetry install

# create an alias for zenml
RUN echo 'alias zenml="poetry run zenml"' >> ~/.bashrc

ADD . /zenml
