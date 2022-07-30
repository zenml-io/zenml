ARG PYTHON_VERSION=3.9
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

ARG ZENML_VERSION

# install the given zenml version (default to latest)
RUN pip install zenml${ZENML_VERSION:+==$ZENML_VERSION}

FROM base AS server
RUN pip install zenml${ZENML_VERSION:+==$ZENML_VERSION}[server]
