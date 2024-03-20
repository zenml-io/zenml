ARG PYTHON_VERSION=3.9
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ZENML_DEBUG=1 \
    ZENML_LOGGING_VERBOSITY=INFO \
    ZENML_CONTAINER=1 

WORKDIR /zenml

COPY README.md pyproject.toml ./
# The existence of this __init__.py file allows the pip install before actually 
# copying our source files which would invalidate caching
COPY src/zenml/__init__.py ./src/zenml/

ENV ZENML_DEBUG=true \
    ZENML_ANALYTICS_OPT_IN=false

# Upgrade pip to the latest version
RUN pip install --upgrade pip

RUN pip install -e .
COPY src src