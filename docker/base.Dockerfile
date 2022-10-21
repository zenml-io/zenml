ARG PYTHON_VERSION=3.9
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ZENML_CONTAINER=1

ARG ZENML_VERSION

# install the given zenml version (default to latest)
RUN pip install zenml${ZENML_VERSION:+==$ZENML_VERSION}

FROM base AS server
RUN pip install zenml${ZENML_VERSION:+==$ZENML_VERSION}[server]

WORKDIR /zenml

RUN mkdir -p .zenconfig/local_stores/default_zen_store

ENV ZENML_CONFIG_PATH=/zenml/.zenconfig \
    ZENML_DEBUG=true \
    ZENML_ANALYTICS_OPT_IN=false

ENTRYPOINT ["uvicorn", "zenml.zen_server.zen_server_api:app",  "--log-level", "debug"]
CMD ["--proxy-headers", "--port", "80", "--host",  "0.0.0.0"]
