ARG PYTHON_VERSION=3.11
ARG ZENML_VERSION=latest
ARG CLOUD_PROVIDER

FROM zenmldocker/zenml:${ZENML_VERSION}-py${PYTHON_VERSION} as base

# Install the Python requirements
RUN pip install zenml${ZENML_VERSION:+==$ZENML_VERSION} notebook pyarrow datasets transformers transformers[torch] torch sentencepiece

# Install cloud-specific ZenML integrations
RUN if [ "$CLOUD_PROVIDER" = "aws" ]; then \
        zenml integration install aws s3 -y; \
    elif [ "$CLOUD_PROVIDER" = "azure" ]; then \
        zenml integration install azure -y; \
    elif [ "$CLOUD_PROVIDER" = "gcp" ]; then \
        zenml integration install gcp -y; \
    else \
        echo "No specific cloud integration installed"; \
    fi