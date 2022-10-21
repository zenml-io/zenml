ARG PYTHON_VERSION=3.9
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ZENML_CONTAINER=1


WORKDIR /zenml

COPY README.md pyproject.toml ./
# The existence of this __init__.py file allows the pip install before actually 
# copying our source files which would invalidate caching
COPY src/zenml/__init__.py ./src/zenml/

RUN pip install -e .[server]
COPY src src

RUN mkdir -p .zenconfig/local_stores/default_zen_store
COPY zenml.db .zenconfig/local_stores/default_zen_store

ENV ZENML_CONFIG_PATH=/zenml/.zenconfig \
    ZENML_DEBUG=true \
    ZENML_ANALYTICS_OPT_IN=false

ENTRYPOINT ["uvicorn", "zenml.zen_server.zen_server_api:app", "--log-level", "debug"]
CMD ["--port", "80", "--host",  "0.0.0.0"]