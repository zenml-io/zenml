ARG BASE_IMAGE="zenmldocker/prepare-release:base"

FROM BASE_IMAGE AS base

# Set the working directory
WORKDIR /app

# Redeclare ARGs
ARG ZENML_BRANCH
ARG CLOUD_PROVIDER

# Install the Python requirements
RUN pip install uv

RUN uv pip install "git+https://github.com/zenml-io/zenml.git@$ZENML_BRANCH" notebook pyarrow datasets transformers transformers[torch] torch sentencepiece

RUN echo "Cloud Provider: $CLOUD_PROVIDER";
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

ENV ZENML_REQUIRES_CODE_DOWNLOAD=True