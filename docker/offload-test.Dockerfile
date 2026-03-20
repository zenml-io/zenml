FROM python:3.12-slim-bookworm

RUN set -ex \
  && apt-get update \
  && apt-get install -y --no-install-recommends \
    git curl build-essential graphviz \
  && apt-get clean -y \
  && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip uv setuptools wheel

WORKDIR /app
