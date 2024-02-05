FROM nvidia/cuda:12.3.1-base-ubuntu22.04

# Install Python 3.10
RUN apt-get update && apt-get install -y python3.10 python3-pip python3.10-venv python3.10-dev python3.10-distutils

# Set envvars
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

RUN pip install -e .
COPY src src

RUN apt-get remove -y python3-blinker
RUN apt-get install python-is-python3